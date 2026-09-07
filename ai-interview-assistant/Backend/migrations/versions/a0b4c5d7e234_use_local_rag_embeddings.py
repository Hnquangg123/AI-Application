"""use 384-dimensional local RAG embeddings

Revision ID: a0b4c5d7e234
Revises: f9a3b4c6d123
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "a0b4c5d7e234"
down_revision: Union[str, Sequence[str], None] = "f9a3b4c6d123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_project_data_embedding_cosine", table_name="project_data")
    op.drop_column("project_data", "embedding")
    op.add_column("project_data", sa.Column("embedding", Vector(384), nullable=True))
    op.create_index(
        "ix_project_data_embedding_cosine",
        "project_data",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.execute("UPDATE project_data SET status = 'pending', error = NULL")
    op.execute("UPDATE project_sections SET indexing_status = 'pending', indexing_error = NULL")


def downgrade() -> None:
    op.drop_index("ix_project_data_embedding_cosine", table_name="project_data")
    op.drop_column("project_data", "embedding")
    op.add_column("project_data", sa.Column("embedding", Vector(1536), nullable=True))
    op.create_index(
        "ix_project_data_embedding_cosine",
        "project_data",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.execute("UPDATE project_data SET status = 'pending', error = NULL")
    op.execute("UPDATE project_sections SET indexing_status = 'pending', indexing_error = NULL")
