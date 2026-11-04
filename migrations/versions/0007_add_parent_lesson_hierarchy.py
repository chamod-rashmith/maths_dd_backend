"""Add parent_lesson_id hierarchy to syllabus_lessons.

Revision ID: 0007_lesson_parent_hierarchy
Revises: 0006_exam_papers_and_marking_steps
Create Date: 2026-11-04 11:00:00.000000

===============================================================================
Curriculum & Syllabus Hierarchy Normalization (Domain 2):
-------------------------------------------------------------------------------
1. Adds `parent_lesson_id` foreign key column to `syllabus_lessons` referencing
   `syllabus_lessons.id` (self-referential hierarchy).
2. Enables Main Unit -> Sub-lessons (Chapters & Sub-topics) structure:
   - Root Units: `parent_lesson_id IS NULL` (උදා: 05. ත්‍රිකෝණමිතිය)
   - Sub-lessons: `parent_lesson_id = 'les_trig'` (උදා: 5.1 ත්‍රිකෝණමිතික අනුපාත)
3. Adds `ix_syllabus_lessons_parent_lesson_id` index for instant sub-lesson querying.
4. ON DELETE CASCADE ensures when a main unit is deleted, its subtopics are cleaned.
===============================================================================
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_lesson_parent_hierarchy"
down_revision: Union[str, Sequence[str], None] = "0006_exam_papers_and_marking_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add parent_lesson_id column, index, and self-referencing foreign key to syllabus_lessons."""
    with op.batch_alter_table("syllabus_lessons") as batch_op:
        batch_op.add_column(
            sa.Column(
                "parent_lesson_id",
                sa.String(length=100),
                nullable=True,
                comment="Self-referencing FK to parent SyllabusLesson.id (Null for root units)",
            )
        )
        batch_op.create_foreign_key(
            "fk_syllabus_lessons_parent_lesson_id",
            "syllabus_lessons",
            ["parent_lesson_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_syllabus_lessons_parent_lesson_id",
            ["parent_lesson_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove parent_lesson_id index, foreign key, and column from syllabus_lessons."""
    with op.batch_alter_table("syllabus_lessons") as batch_op:
        batch_op.drop_index("ix_syllabus_lessons_parent_lesson_id")
        batch_op.drop_constraint("fk_syllabus_lessons_parent_lesson_id", type_="foreignkey")
        batch_op.drop_column("parent_lesson_id")
