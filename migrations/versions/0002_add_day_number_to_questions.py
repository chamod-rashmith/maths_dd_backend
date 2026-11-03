"""Add day_number and is_deleted to questions table for dynamic daily challenge series.

Revision ID: 0002_add_day_number
Revises: 0001_initial_schema_v1
Create Date: 2026-11-03 12:08:00.000000

This migration ensures the `is_deleted` soft-delete flag and `day_number` integer columns
are present on the `questions` table with performance indexes.
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
    """Add is_deleted and day_number columns and corresponding search indexes to questions table."""
    # Ensure is_deleted column exists with default false
    op.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false")

    # Add day_number column to questions
    op.execute("ALTER TABLE questions ADD COLUMN IF NOT EXISTS day_number INTEGER")

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_questions_day_number ON questions (day_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_questions_is_deleted ON questions (is_deleted)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_questions_day_scheduled ON questions (day_number, scheduled_date, is_published, is_deleted)")


def downgrade() -> None:
    """Revert day_number and is_deleted columns and their indexes."""
    op.execute("DROP INDEX IF EXISTS idx_questions_day_scheduled")
    op.execute("DROP INDEX IF EXISTS ix_questions_day_number")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS day_number")
