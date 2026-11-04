"""Add exam_papers and marking_scheme_steps tables.

Revision ID: 0006_exam_papers_and_marking_steps
Revises: 0005_xp_transactions_and_progress
Create Date: 2026-11-04 10:40:00.000000

This migration normalizes the Academic Catalog & Content Bank (Domain 3):
1. `exam_papers`: Catalog of official G.C.E. A/L past papers and model tests.
2. `questions.exam_paper_id`: Links questions directly to their source examination paper.
3. `marking_scheme_steps`: 3NF step-by-step rubrics (Method, Accuracy, Final marks).
4. `marking_schemes.description_si`: Localized overview notes for marking schemes.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_exam_papers_and_marking_steps"
down_revision: Union[str, Sequence[str], None] = "0005_xp_transactions_and_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create exam_papers, marking_scheme_steps tables and add question FK."""

    # 1. Create exam_papers table
    op.create_table(
        "exam_papers",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("subject_id", sa.String(length=100), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=32), server_default=sa.text("'AL_GOVT'"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("part", sa.String(length=32), server_default=sa.text("'PART_I'"), nullable=False),
        sa.Column("title_si", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=True),
        sa.Column("source_pdf_url", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_exam_papers_subject_id", "exam_papers", ["subject_id"], unique=False)
    op.create_index("ix_exam_papers_type", "exam_papers", ["type"], unique=False)
    op.create_index("ix_exam_papers_year", "exam_papers", ["year"], unique=False)
    op.create_index("idx_exam_papers_subject_year", "exam_papers", ["subject_id", "year", "type"], unique=False)

    # 2. Add exam_paper_id to questions
    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "exam_paper_id",
                sa.String(length=36),
                nullable=True,
                comment="FK linking to source examination paper if past/model paper",
            )
        )
        batch_op.create_foreign_key(
            "fk_questions_exam_paper_id",
            "exam_papers",
            ["exam_paper_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_questions_exam_paper_id", ["exam_paper_id"], unique=False)

    # 3. Add description_si to marking_schemes
    with op.batch_alter_table("marking_schemes") as batch_op:
        batch_op.add_column(sa.Column("description_si", sa.Text(), nullable=True))

    # 4. Create marking_scheme_steps table
    op.create_table(
        "marking_scheme_steps",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("marking_scheme_id", sa.Uuid(), sa.ForeignKey("marking_schemes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("step_type", sa.String(length=32), server_default=sa.text("'METHOD'"), nullable=False),
        sa.Column("description_si", sa.Text(), nullable=False),
        sa.Column("allocated_marks", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("annotation", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_marking_scheme_steps_scheme_id", "marking_scheme_steps", ["marking_scheme_id"], unique=False)
    op.create_index("idx_marking_steps_scheme_order", "marking_scheme_steps", ["marking_scheme_id", "order_index"], unique=False)


def downgrade() -> None:
    """Drop marking_scheme_steps, remove question exam_paper FK, drop exam_papers."""
    op.drop_table("marking_scheme_steps")
    with op.batch_alter_table("marking_schemes") as batch_op:
        batch_op.drop_column("description_si")
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_index("ix_questions_exam_paper_id")
        batch_op.drop_constraint("fk_questions_exam_paper_id", type_="foreignkey")
        batch_op.drop_column("exam_paper_id")
    op.drop_table("exam_papers")
