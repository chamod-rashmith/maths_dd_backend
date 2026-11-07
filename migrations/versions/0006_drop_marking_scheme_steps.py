"""Drop unused marking_scheme_steps table (solutions use single Markdown+LaTeX content_text or pdf_url).

Revision ID: 0006_drop_marking_scheme_steps
Revises: 0005_add_admin_audit_logs_and_leaderboard_index
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_drop_marking_scheme_steps"
down_revision: Union[str, Sequence[str], None] = "0005_add_admin_audit_logs_and_leaderboard_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the unused marking_scheme_steps table and its indexes."""
    op.drop_index("idx_marking_steps_scheme_order", table_name="marking_scheme_steps", if_exists=True)
    op.drop_index("ix_marking_scheme_steps_marking_scheme_id", table_name="marking_scheme_steps", if_exists=True)
    op.drop_table("marking_scheme_steps", if_exists=True)


def downgrade() -> None:
    """Recreate marking_scheme_steps table for rollback compatibility."""
    op.create_table(
        "marking_scheme_steps",
        sa.Column("id", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column(
            "marking_scheme_id",
            sa.Uuid(),
            sa.ForeignKey("marking_schemes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("step_type", sa.String(length=32), server_default=sa.text("'METHOD'"), nullable=False),
        sa.Column("description_si", sa.Text(), nullable=False),
        sa.Column("allocated_marks", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("annotation", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(
        "ix_marking_scheme_steps_marking_scheme_id",
        "marking_scheme_steps",
        ["marking_scheme_id"],
    )
    op.create_index(
        "idx_marking_steps_scheme_order",
        "marking_scheme_steps",
        ["marking_scheme_id", "order_index"],
    )
