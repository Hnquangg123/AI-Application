"""add project sections and section chunk metadata

Revision ID: f9a3b4c6d123
Revises: e8f2a3b5c012
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f9a3b4c6d123"
down_revision: Union[str, Sequence[str], None] = "e8f2a3b5c012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("indexing_status", sa.String(length=20), nullable=False),
        sa.Column("indexing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "slug", name="uq_project_section_slug"),
    )
    op.create_index("ix_project_sections_project_id", "project_sections", ["project_id"])
    op.add_column("project_data", sa.Column("project_section_id", sa.Uuid(), nullable=True))
    op.add_column("project_data", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.add_column(
        "project_data",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_project_data_section",
        "project_data",
        "project_sections",
        ["project_section_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_project_data_project_section_id", "project_data", ["project_section_id"])
    op.create_unique_constraint(
        "uq_project_data_section_chunk",
        "project_data",
        ["project_section_id", "chunk_index"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_project_data_section_chunk", "project_data", type_="unique")
    op.drop_index("ix_project_data_project_section_id", table_name="project_data")
    op.drop_constraint("fk_project_data_section", "project_data", type_="foreignkey")
    op.drop_column("project_data", "metadata")
    op.drop_column("project_data", "chunk_index")
    op.drop_column("project_data", "project_section_id")
    op.drop_index("ix_project_sections_project_id", table_name="project_sections")
    op.drop_table("project_sections")
