"""Add daily_challenges and daily_challenge_questions tables.

Revision ID: 0003_daily_challenge_sets
Revises: 0002_add_day_number
Create Date: 2026-11-04 09:50:00.000000

This migration normalizes the Daily Challenge architecture:
1. `daily_challenges`: Represents the daily workout set (Day 1, Day 2... Day N).
2. `daily_challenge_questions`: Junction table mapping 1 to 10+ questions to a daily set with
   section types (SHORT, ESSAY) and canonical ordering.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_daily_challenge_sets"
down_revision: Union[str, Sequence[str], None] = "0002_add_day_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create daily_challenges and daily_challenge_questions tables with constraints and indexes."""
    
    # 1. Create daily_challenges table
    op.create_table(
        "daily_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_id", sa.String(length=100), nullable=True),
        sa.Column("target_duration_seconds", sa.Integer(), server_default=sa.text("3600"), nullable=False),
        sa.Column("total_marks", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("day_number", name="uq_daily_challenges_day_number"),
    )
    op.create_index(op.f("ix_daily_challenges_day_number"), "daily_challenges", ["day_number"], unique=True)
    op.create_index(op.f("ix_daily_challenges_scheduled_date"), "daily_challenges", ["scheduled_date"], unique=False)
    op.create_index("idx_daily_challenges_day_date", "daily_challenges", ["day_number", "scheduled_date"], unique=False)

    # 2. Create daily_challenge_questions junction table
    op.create_table(
        "daily_challenge_questions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("daily_challenge_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=100), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("section", sa.String(length=50), server_default=sa.text("'SHORT'"), nullable=False),
        sa.Column("allocated_marks", sa.Integer(), server_default=sa.text("25"), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["daily_challenge_id"], ["daily_challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("daily_challenge_id", "question_id", name="uq_challenge_question"),
        sa.UniqueConstraint("daily_challenge_id", "order_index", name="uq_challenge_order"),
    )
    op.create_index(op.f("ix_daily_challenge_questions_daily_challenge_id"), "daily_challenge_questions", ["daily_challenge_id"], unique=False)
    op.create_index(op.f("ix_daily_challenge_questions_question_id"), "daily_challenge_questions", ["question_id"], unique=False)
    op.create_index("idx_dc_question_lookup", "daily_challenge_questions", ["daily_challenge_id", "order_index"], unique=False)


def downgrade() -> None:
    """Drop daily_challenge_questions and daily_challenges tables."""
    op.drop_table("daily_challenge_questions")
    op.drop_table("daily_challenges")
