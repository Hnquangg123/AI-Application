"""add projects and project data

Revision ID: d7e1c2f4a901
Revises: c4a9d812f031
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e1c2f4a901"
down_revision: Union[str, Sequence[str], None] = "c4a9d812f031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project_data",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_content", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_data_project_id", "project_data", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_data_project_id", table_name="project_data")
    op.drop_table("project_data")
    op.drop_table("projects")
