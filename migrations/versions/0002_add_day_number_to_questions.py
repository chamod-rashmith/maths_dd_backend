"""Add day_number to questions table for dynamic daily challenge series.

Revision ID: 0002_add_day_number
Revises: 0001_initial_schema_v1
Create Date: 2026-11-03 12:08:00.000000

This migration adds an optional indexed integer column `day_number` to the `questions` table.
It enables organizing daily challenge questions into sequential series (e.g. Day 1, Day 2, Day 50)
regardless of calendar date skips, allowing students to browse and practice challenges chronologically.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_add_day_number"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add day_number column and corresponding search indexes to questions table."""
    # Add day_number column to questions
    op.add_column(
        "questions",
        sa.Column("day_number", sa.Integer(), nullable=True),
    )

    # Index for fast single-column lookup by day number
    op.create_index(
        op.f("ix_questions_day_number"),
        "questions",
        ["day_number"],
        unique=False,
    )

    # Composite index for filtering and sorting daily challenge series
    op.create_index(
        "idx_questions_day_scheduled",
        "questions",
        ["day_number", "scheduled_date", "is_published", "is_deleted"],
        unique=False,
    )


def downgrade() -> None:
    """Revert day_number column and its indexes."""
    op.drop_index("idx_questions_day_scheduled", table_name="questions")
    op.drop_index(op.f("ix_questions_day_number"), table_name="questions")
    op.drop_column("questions", "day_number")
