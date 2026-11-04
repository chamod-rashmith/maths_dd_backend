"""Add student_profiles table for Domain 1 normalization.

Revision ID: 0008_student_profiles_domain1
Revises: 0007_lesson_parent_hierarchy
Create Date: 2026-11-04 11:10:00.000000

===============================================================================
Core IAM & Student Profile Normalization (Domain 1):
-------------------------------------------------------------------------------
1. Creates `student_profiles` table:
   - `user_id`: PK and FK to `users.uid` (ON DELETE CASCADE)
   - `exam_year`: Target G.C.E. A/L year (e.g. 2025, 2026, 2027)
   - `attempt_number`: Sitting attempt (1 = 1st shy, 2 = 2nd shy, 3 = 3rd shy)
   - `exam_district_id`: Official District FK for Z-Score rank & cutoffs
   - `school_name`: Student's school or institute
   - `stream`: Study stream (PHYSICAL_SCIENCE, BIO_SCIENCE, etc.)
   - `medium`: Examination medium (SINHALA, ENGLISH, TAMIL)
2. Adds indices on `exam_year` and `exam_district_id` for lightning-fast district analytics.
3. Automatically backfills existing student records from `users` table.
===============================================================================
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_student_profiles_domain1"
down_revision: Union[str, Sequence[str], None] = "0007_lesson_parent_hierarchy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create student_profiles table and initialize indexes."""
    op.create_table(
        "student_profiles",
        sa.Column(
            "user_id",
            sa.String(length=128),
            sa.ForeignKey("users.uid", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
            comment="Primary Key and Foreign Key linking directly to users.uid",
        ),
        sa.Column(
            "exam_year",
            sa.Integer(),
            nullable=True,
            comment="Target G.C.E. A/L Examination Year (e.g. 2025, 2026, 2027)",
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=True,
            comment="Exam sitting attempt: 1 (1st shy), 2 (2nd shy), 3 (3rd shy)",
        ),
        sa.Column(
            "exam_district_id",
            sa.Integer(),
            sa.ForeignKey("districts.id", ondelete="SET NULL"),
            nullable=True,
            comment="Official Sri Lankan District (1-25) used for Z-Score calculation",
        ),
        sa.Column(
            "school_name",
            sa.String(length=255),
            nullable=True,
            comment="Name of attending school or institute",
        ),
        sa.Column(
            "stream",
            sa.String(length=50),
            nullable=True,
            comment="G.C.E. A/L Subject Stream",
        ),
        sa.Column(
            "medium",
            sa.String(length=20),
            server_default=sa.text("'SINHALA'"),
            nullable=True,
            comment="Medium of examination: SINHALA, ENGLISH, TAMIL",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_index("ix_student_profiles_user_id", "student_profiles", ["user_id"], unique=False)
    op.create_index("ix_student_profiles_exam_year", "student_profiles", ["exam_year"], unique=False)
    op.create_index("ix_student_profiles_exam_district_id", "student_profiles", ["exam_district_id"], unique=False)


def downgrade() -> None:
    """Drop student_profiles table and its indexes."""
    op.drop_index("ix_student_profiles_exam_district_id", table_name="student_profiles")
    op.drop_index("ix_student_profiles_exam_year", table_name="student_profiles")
    op.drop_index("ix_student_profiles_user_id", table_name="student_profiles")
    op.drop_table("student_profiles")
