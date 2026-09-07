import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    data: Mapped[list["ProjectData"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectData.created_at"
    )
    sections: Mapped[list["ProjectSection"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectSection.sort_order",
    )


class ProjectSection(Base):
    __tablename__ = "project_sections"
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_project_section_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=lambda: {"blocks": []}, nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    indexing_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    indexing_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="sections")
    data: Mapped[list["ProjectData"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="ProjectData.chunk_index"
    )


class ProjectData(Base):
    __tablename__ = "project_data"
    __table_args__ = (
        UniqueConstraint("project_section_id", "chunk_index", name="uq_project_data_section_chunk"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_sections.id", ondelete="CASCADE"), nullable=True, index=True
    )
    chunk_index: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # text | image
    source_content: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="data")
    section: Mapped[ProjectSection | None] = relationship(back_populates="data")
