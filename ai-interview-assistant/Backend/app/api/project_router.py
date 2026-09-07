from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.project import Project, ProjectData, ProjectSection
from app.models.schemas import (
    ProjectCreateRequest,
    ProjectDataCreateRequest,
    ProjectDataView,
    ProjectSectionCreateRequest,
    ProjectSectionUpdateRequest,
    ProjectSectionView,
    ProjectUpdateRequest,
    ProjectView,
)
from app.services.project_service import (
    get_project,
    get_project_section,
    list_projects,
    make_section_slug,
    process_project_data,
    process_project_section,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectView])
def projects(db: Session = Depends(get_db)) -> list[dict]:
    return list_projects(db)


@router.post("", response_model=ProjectView, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateRequest, db: Session = Depends(get_db)) -> Project:
    project = Project(name=payload.name.strip(), description=payload.description.strip())
    db.add(project)
    db.commit()
    return get_project(db, project.id)


@router.get("/{project_id}", response_model=ProjectView)
def read_project(project_id: UUID, db: Session = Depends(get_db)) -> Project:
    try:
        return get_project(db, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}", response_model=ProjectView)
def update_project(project_id: UUID, payload: ProjectUpdateRequest, db: Session = Depends(get_db)) -> Project:
    try:
        project = get_project(db, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    project.name = payload.name.strip()
    project.description = payload.description.strip()
    db.commit()
    return get_project(db, project.id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, db: Session = Depends(get_db)) -> None:
    try:
        project = get_project(db, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.delete(project)
    db.commit()


def _unique_section_slug(
    db: Session,
    project_id: UUID,
    requested_slug: str,
    section_id: UUID | None = None,
) -> str:
    base = make_section_slug(requested_slug)
    candidate = base
    suffix = 2
    while db.scalar(
        select(ProjectSection.id).where(
            ProjectSection.project_id == project_id,
            ProjectSection.slug == candidate,
            ProjectSection.id != section_id if section_id else ProjectSection.id.is_not(None),
        )
    ):
        candidate = f"{base[:190]}-{suffix}"
        suffix += 1
    return candidate


@router.get("/{project_id}/sections", response_model=list[ProjectSectionView])
def list_project_sections(project_id: UUID, db: Session = Depends(get_db)) -> list[ProjectSection]:
    try:
        project = get_project(db, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return project.sections


@router.post("/{project_id}/sections", response_model=ProjectSectionView, status_code=status.HTTP_201_CREATED)
def create_project_section(
    project_id: UUID,
    payload: ProjectSectionCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ProjectSection:
    try:
        get_project(db, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    section = ProjectSection(
        project_id=project_id,
        title=payload.title.strip(),
        slug=_unique_section_slug(db, project_id, payload.slug or payload.title),
        content=payload.content.model_dump(),
        sort_order=payload.sort_order,
        indexing_status="pending",
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    if section.content.get("blocks"):
        background_tasks.add_task(process_project_section, section.id)
    return section


@router.get("/{project_id}/sections/{section_id}", response_model=ProjectSectionView)
def read_project_section(project_id: UUID, section_id: UUID, db: Session = Depends(get_db)) -> ProjectSection:
    try:
        return get_project_section(db, project_id, section_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}/sections/{section_id}", response_model=ProjectSectionView)
def update_project_section(
    project_id: UUID,
    section_id: UUID,
    payload: ProjectSectionUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ProjectSection:
    try:
        section = get_project_section(db, project_id, section_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    section.title = payload.title.strip()
    section.slug = _unique_section_slug(db, project_id, payload.slug or payload.title, section.id)
    section.content = payload.content.model_dump()
    section.sort_order = payload.sort_order
    section.indexing_status = "pending"
    section.indexing_error = None
    db.commit()
    db.refresh(section)
    if section.content.get("blocks"):
        background_tasks.add_task(process_project_section, section.id)
    return section


@router.delete("/{project_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_section(project_id: UUID, section_id: UUID, db: Session = Depends(get_db)) -> None:
    try:
        section = get_project_section(db, project_id, section_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.delete(section)
    db.commit()


@router.post("/{project_id}/sections/{section_id}/index", status_code=status.HTTP_202_ACCEPTED)
def index_project_section(
    project_id: UUID,
    section_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    try:
        section = get_project_section(db, project_id, section_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    section.indexing_status = "pending"
    section.indexing_error = None
    db.commit()
    background_tasks.add_task(process_project_section, section.id)
    return {"status": "queued", "count": 1}


@router.post("/{project_id}/data", response_model=ProjectDataView, status_code=status.HTTP_202_ACCEPTED)
def add_project_data(
    project_id: UUID,
    payload: ProjectDataCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ProjectData:
    try:
        get_project(db, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    data = ProjectData(
        project_id=project_id,
        source_type=payload.source_type,
        source_content=payload.source_content,
        status="pending",
    )
    db.add(data)
    db.commit()
    db.refresh(data)
    background_tasks.add_task(process_project_data, data.id)
    return data


@router.post("/{project_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
def reindex_project(project_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    try:
        project = get_project(db, project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    legacy_data = [data for data in project.data if data.project_section_id is None]
    for data in legacy_data:
        data.status = "pending"
        background_tasks.add_task(process_project_data, data.id)
    for section in project.sections:
        section.indexing_status = "pending"
        section.indexing_error = None
        background_tasks.add_task(process_project_section, section.id)
    db.commit()
    return {"status": "queued", "count": len(legacy_data) + len(project.sections)}
