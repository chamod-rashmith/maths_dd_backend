"""Add xp_transactions table and last_attempt_duration_seconds column.

Revision ID: 0005_xp_transactions_and_progress
Revises: 0004_billing_and_bank_slips
Create Date: 2026-11-04 10:30:00.000000

This migration establishes the normalized Gamification & Study Time Audit architecture (Domain 5):
1. `xp_transactions`: An immutable audit ledger for every XP award, deduction, or bonus with verified proof.
2. `user_question_attempts`: Adds `last_attempt_duration_seconds` to distinguish between the most recent attempt
   session and cumulative total study time (`time_spent_seconds`).
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_xp_transactions_and_progress"
down_revision: Union[str, Sequence[str], None] = "0004_billing_and_bank_slips"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create xp_transactions table and add last_attempt_duration_seconds to user_question_attempts."""

    # 1. Add last_attempt_duration_seconds to user_question_attempts
    with op.batch_alter_table("user_question_attempts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "last_attempt_duration_seconds",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )

    # 2. Create xp_transactions table (Immutable Gamification Audit Ledger)
    op.create_table(
        "xp_transactions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("attempt_id", sa.String(length=255), nullable=True),
        sa.Column("question_id", sa.String(length=100), nullable=True),
        sa.Column("description_si", sa.String(length=255), nullable=True),
        sa.Column("description_en", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_xp_transactions_user_id", "xp_transactions", ["user_id"], unique=False)
    op.create_index("ix_xp_transactions_reason", "xp_transactions", ["reason"], unique=False)
    op.create_index("ix_xp_transactions_created_at", "xp_transactions", ["created_at"], unique=False)


def downgrade() -> None:
    """Drop xp_transactions table and remove last_attempt_duration_seconds."""
    op.drop_table("xp_transactions")
    with op.batch_alter_table("user_question_attempts") as batch_op:
        batch_op.drop_column("last_attempt_duration_seconds")
