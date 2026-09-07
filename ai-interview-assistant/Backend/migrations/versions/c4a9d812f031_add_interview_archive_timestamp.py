"""add interview archive timestamp

Revision ID: c4a9d812f031
Revises: bae8f7bfd05a
Create Date: 2026-08-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a9d812f031"
down_revision: Union[str, Sequence[str], None] = "bae8f7bfd05a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_interview_sessions_archived_at",
        "interview_sessions",
        ["archived_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_interview_sessions_archived_at", table_name="interview_sessions")
    op.drop_column("interview_sessions", "archived_at")
