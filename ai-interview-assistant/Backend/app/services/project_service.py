import logging
import re
import unicodedata
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project, ProjectData, ProjectSection
from app.services.local_rag_service import describe_image, embed_text, embed_texts

logger = logging.getLogger(__name__)


def _project_view(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "data": [
            {
                "id": item.id,
                "project_section_id": item.project_section_id,
                "chunk_index": item.chunk_index,
                "source_type": item.source_type,
                "status": item.status,
                "extracted_text": item.extracted_text,
                "error": item.error,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in project.data
        ],
        "sections": project.sections,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def list_projects(db: Session) -> list[dict]:
    projects = db.scalars(
        select(Project)
        .options(selectinload(Project.data), selectinload(Project.sections))
        .order_by(Project.updated_at.desc())
    ).unique()
    return [_project_view(project) for project in projects]


def get_project(db: Session, project_id: UUID) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.data), selectinload(Project.sections))
    )
    if project is None:
        raise KeyError("Project not found.")
    return project


def get_project_section(db: Session, project_id: UUID, section_id: UUID) -> ProjectSection:
    section = db.scalar(
        select(ProjectSection).where(
            ProjectSection.id == section_id,
            ProjectSection.project_id == project_id,
        )
    )
    if section is None:
        raise KeyError("Project section not found.")
    return section


def make_section_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.replace("đ", "d").replace("Đ", "D"))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:200] or "section"


def _chunk_text(text: str, max_chars: int = 1800, overlap: int = 200) -> list[str]:
    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        if end < len(clean):
            boundary = max(clean.rfind("\n", start, end), clean.rfind(". ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


def process_project_data(data_id: UUID) -> None:
    """Background indexing job: extract text, create an embedding, and persist it."""
    from app.database.session import get_session_factory

    db = get_session_factory()()
    try:
        data = db.get(ProjectData, data_id)
        if data is None:
            return
        data.status = "processing"
        data.error = None
        db.commit()

        if data.source_type == "image":
            extracted = describe_image(data.source_content)
        else:
            extracted = data.source_content.strip()

        if not extracted:
            raise ValueError("No text could be extracted from this project data.")
        embedding = embed_text(extracted)
        data.extracted_text = extracted
        data.embedding = embedding
        data.status = "ready"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Project data indexing failed", extra={"data_id": str(data_id)})
        db.rollback()
        data = db.get(ProjectData, data_id)
        if data is not None:
            data.status = "failed"
            data.error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


def process_project_section(section_id: UUID) -> None:
    """Build chunk embeddings for all text and image blocks in one documentation section."""
    from app.database.session import get_session_factory

    db = get_session_factory()()
    try:
        section = db.get(ProjectSection, section_id)
        if section is None:
            return
        section.indexing_status = "processing"
        section.indexing_error = None
        db.commit()

        chunk_specs: list[tuple[str, str, dict]] = []
        for block_index, block in enumerate(section.content.get("blocks", [])):
            source_type = block.get("type")
            value = str(block.get("value", "")).strip()
            caption = str(block.get("caption") or "").strip() or None
            if source_type == "image":
                extracted = describe_image(value, caption)
            elif source_type == "text":
                extracted = value
            else:
                continue
            for block_chunk_index, chunk in enumerate(_chunk_text(extracted)):
                chunk_specs.append(
                    (
                        source_type,
                        chunk,
                        {
                            "section_title": section.title,
                            "section_slug": section.slug,
                            "block_index": block_index,
                            "block_chunk_index": block_chunk_index,
                            "caption": caption,
                        },
                    )
                )

        if not chunk_specs:
            raise ValueError("The section has no text or image content to index.")
        vectors = embed_texts([item[1] for item in chunk_specs])

        db.execute(delete(ProjectData).where(ProjectData.project_section_id == section.id))
        for chunk_index, ((source_type, chunk, metadata), embedding) in enumerate(zip(chunk_specs, vectors)):
            db.add(
                ProjectData(
                    project_id=section.project_id,
                    project_section_id=section.id,
                    chunk_index=chunk_index,
                    source_type=source_type,
                    source_content=chunk,
                    extracted_text=chunk,
                    embedding=embedding,
                    chunk_metadata=metadata,
                    status="ready",
                )
            )
        section.indexing_status = "ready"
        section.indexing_error = None
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Project section indexing failed", extra={"section_id": str(section_id)})
        db.rollback()
        section = db.get(ProjectSection, section_id)
        if section is not None:
            section.indexing_status = "failed"
            section.indexing_error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


def retrieve_project_context(db: Session, project_id: UUID, query: str, limit: int = 5) -> list[str]:
    """Retrieve the closest indexed project data using PostgreSQL cosine distance."""
    indexed_data_id = db.scalar(
        select(ProjectData.id)
        .where(
            ProjectData.project_id == project_id,
            ProjectData.status == "ready",
            ProjectData.embedding.is_not(None),
        )
        .limit(1)
    )
    if indexed_data_id is None:
        return []

    query_embedding = embed_text(query)
    distance = ProjectData.embedding.cosine_distance(query_embedding)
    rows = db.execute(
        select(ProjectData.extracted_text)
        .where(
            ProjectData.project_id == project_id,
            ProjectData.status == "ready",
            ProjectData.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(limit)
    ).scalars()
    return [text for text in rows if text]
