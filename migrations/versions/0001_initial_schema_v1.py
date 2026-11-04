"""Initial Clean Schema Baseline (v1 Production).

Revision ID: 0001_initial_schema_v1
Revises: None
Create Date: 2026-11-04 12:00:00.000000

Establishes the unified 3NF/BCNF relational database schema across all 7 architectural domains:
1. Core IAM & Student Profiles (districts, users, student_profiles, user_stats)
2. Curriculum & Syllabus Hierarchy (subjects, syllabus_lessons with self-referential sub-lessons)
3. Academic Catalog & Content Bank (exam_papers, questions, marking_schemes, marking_scheme_steps, study_notes)
4. Daily Challenge Engine (daily_challenges, daily_challenge_questions)
5. Student Progress & Gamification (user_question_attempts, user_daily_activities, xp_transactions)
6. Webhooks & Observability (processed_webhook_events)
7. Billing & Subscriptions (subscription_plans, plan_prices, user_subscriptions, payments, bank_transfer_slips)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "0001_initial_schema_v1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SRI_LANKAN_DISTRICTS = [
    {"id": 1, "code": "COLOMBO", "name_en": "Colombo", "name_si": "කොළඹ", "name_ta": "கொழும்பு", "province": "WESTERN", "display_order": 1},
    {"id": 2, "code": "GAMPAHA", "name_en": "Gampaha", "name_si": "ගම්පහ", "name_ta": "கம்பஹா", "province": "WESTERN", "display_order": 2},
    {"id": 3, "code": "KALUTARA", "name_en": "Kalutara", "name_si": "කළුතර", "name_ta": "களுத்துறை", "province": "WESTERN", "display_order": 3},
    {"id": 4, "code": "KANDY", "name_en": "Kandy", "name_si": "මහනුවර", "name_ta": "கண்டி", "province": "CENTRAL", "display_order": 4},
    {"id": 5, "code": "MATALE", "name_en": "Matale", "name_si": "මාතලේ", "name_ta": "மாத்தளை", "province": "CENTRAL", "display_order": 5},
    {"id": 6, "code": "NUWARA_ELIYA", "name_en": "Nuwara Eliya", "name_si": "නුවරඑළිය", "name_ta": "நுவரெலியா", "province": "CENTRAL", "display_order": 6},
    {"id": 7, "code": "GALLE", "name_en": "Galle", "name_si": "ගාල්ල", "name_ta": "காலி", "province": "SOUTHERN", "display_order": 7},
    {"id": 8, "code": "MATARA", "name_en": "Matara", "name_si": "මාතර", "name_ta": "மாத்தறை", "province": "SOUTHERN", "display_order": 8},
    {"id": 9, "code": "HAMBANTOTA", "name_en": "Hambantota", "name_si": "හම්බන්තොට", "name_ta": "அம்பாந்தோட்டை", "province": "SOUTHERN", "display_order": 9},
    {"id": 10, "code": "JAFFNA", "name_en": "Jaffna", "name_si": "යාපනය", "name_ta": "யாழ்ப்பாணம்", "province": "NORTHERN", "display_order": 10},
    {"id": 11, "code": "KILINOCHCHI", "name_en": "Kilinochchi", "name_si": "කිලිනොච්චිය", "name_ta": "கிளிநொச்சி", "province": "NORTHERN", "display_order": 11},
    {"id": 12, "code": "MANNAR", "name_en": "Mannar", "name_si": "මන්නාරම", "name_ta": "மன்னார்", "province": "NORTHERN", "display_order": 12},
    {"id": 13, "code": "VAVUNIYA", "name_en": "Vavuniya", "name_si": "වවුනියාව", "name_ta": "வவுனியா", "province": "NORTHERN", "display_order": 13},
    {"id": 14, "code": "MULLAITIVU", "name_en": "Mullaitivu", "name_si": "මුලතිව්", "name_ta": "முல்லைத்தீவு", "province": "NORTHERN", "display_order": 14},
    {"id": 15, "code": "BATTICALOA", "name_en": "Batticaloa", "name_si": "මඩකලපුව", "name_ta": "மட்டக்களப்பு", "province": "EASTERN", "display_order": 15},
    {"id": 16, "code": "AMPARA", "name_en": "Ampara", "name_si": "අම්පාර", "name_ta": "அம்பாறை", "province": "EASTERN", "display_order": 16},
    {"id": 17, "code": "TRINCOMALEE", "name_en": "Trincomalee", "name_si": "ත්‍රිකුණාමලය", "name_ta": "திருகோணமலை", "province": "EASTERN", "display_order": 17},
    {"id": 18, "code": "KURUNEGALA", "name_en": "Kurunegala", "name_si": "කුරුණෑගල", "name_ta": "குருணாகல்", "province": "NORTH_WESTERN", "display_order": 18},
    {"id": 19, "code": "PUTTALAM", "name_en": "Puttalam", "name_si": "පුත්තලම", "name_ta": "புத்தளம்", "province": "NORTH_WESTERN", "display_order": 19},
    {"id": 20, "code": "ANURADHAPURA", "name_en": "Anuradhapura", "name_si": "අනුරාධපුරය", "name_ta": "அனுராதபுரம்", "province": "NORTH_CENTRAL", "display_order": 20},
    {"id": 21, "code": "POLONNARUWA", "name_en": "Polonnaruwa", "name_si": "පොළොන්නරුව", "name_ta": "பொலன்னறுவை", "province": "NORTH_CENTRAL", "display_order": 21},
    {"id": 22, "code": "BADULLA", "name_en": "Badulla", "name_si": "බදුල්ල", "name_ta": "பதுளை", "province": "UVA", "display_order": 22},
    {"id": 23, "code": "MONARAGALA", "name_en": "Monaragala", "name_si": "මොනරාගල", "name_ta": "மொணරාகலை", "province": "UVA", "display_order": 23},
    {"id": 24, "code": "RATNAPURA", "name_en": "Ratnapura", "name_si": "රත්නපුර", "name_ta": "இரத்தினபுரி", "province": "SABARAGAMUWA", "display_order": 24},
    {"id": 25, "code": "KEGALLE", "name_en": "Kegalle", "name_si": "කෑගල්ල", "name_ta": "கேகாலை", "province": "SABARAGAMUWA", "display_order": 25},
]


def upgrade() -> None:
    """Create all 22 normalized production tables and pre-seed Sri Lankan districts."""

    # 1. districts
    districts_table = op.create_table(
        "districts",
        sa.Column("id", sa.Integer(), autoincrement=False, primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column("name_si", sa.String(length=100), nullable=False),
        sa.Column("name_ta", sa.String(length=100), nullable=False),
        sa.Column("province", sa.String(length=50), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_index(op.f("ix_districts_code"), "districts", ["code"], unique=True)
    op.create_index(op.f("ix_districts_province"), "districts", ["province"], unique=False)

    # Bulk insert standard Sri Lankan districts
    op.bulk_insert(districts_table, SRI_LANKAN_DISTRICTS)

    # 2. users (Firebase UID primary key matching User ORM model)
    op.create_table(
        "users",
        sa.Column("uid", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("telephone_no", sa.String(length=50), nullable=True),
        sa.Column("role", sa.String(length=50), server_default=sa.text("'USER'"), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("school_name", sa.String(length=255), nullable=True),
        sa.Column("district_id", sa.Integer(), sa.ForeignKey("districts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stream", sa.String(length=50), nullable=True),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("attempt", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_users_uid"), "users", ["uid"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_district_id"), "users", ["district_id"], unique=False)

    # 3. student_profiles (1-to-1 extension of users for academic metadata; PK is user_id)
    op.create_table(
        "student_profiles",
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("exam_year", sa.Integer(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("exam_district_id", sa.Integer(), sa.ForeignKey("districts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("school_name", sa.String(length=255), nullable=True),
        sa.Column("stream", sa.String(length=50), nullable=True),
        sa.Column("medium", sa.String(length=20), server_default=sa.text("'SINHALA'"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("attempt_number IS NULL OR (attempt_number >= 1 AND attempt_number <= 3)", name="chk_student_profiles_attempt_number"),
        sa.CheckConstraint("exam_year IS NULL OR (exam_year >= 2020 AND exam_year <= 2040)", name="chk_student_profiles_exam_year"),
    )
    op.create_index(op.f("ix_student_profiles_user_id"), "student_profiles", ["user_id"], unique=False)
    op.create_index(op.f("ix_student_profiles_exam_year"), "student_profiles", ["exam_year"], unique=False)
    op.create_index(op.f("ix_student_profiles_exam_district_id"), "student_profiles", ["exam_district_id"], unique=False)

    # 4. user_stats (Projection table for user stats, streaks, XP)
    op.create_table(
        "user_stats",
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("xp", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("current_streak_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("longest_streak_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_solved_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_study_time_seconds", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("accuracy_rate", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_user_stats_user_id"), "user_stats", ["user_id"], unique=False)

    # 5. subjects
    op.create_table(
        "subjects",
        sa.Column("id", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sinhala_name", sa.String(length=255), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_subjects_id"), "subjects", ["id"], unique=False)
    op.create_index(op.f("ix_subjects_code"), "subjects", ["code"], unique=True)

    # 6. syllabus_lessons (with hierarchical self-referential sub-lessons)
    op.create_table(
        "syllabus_lessons",
        sa.Column("id", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column("subject_id", sa.String(length=100), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_lesson_id", sa.String(length=100), sa.ForeignKey("syllabus_lessons.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("sinhala_title", sa.String(length=255), nullable=True),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("question_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("premium_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_syllabus_lessons_id"), "syllabus_lessons", ["id"], unique=False)
    op.create_index(op.f("ix_syllabus_lessons_subject_id"), "syllabus_lessons", ["subject_id"], unique=False)
    op.create_index(op.f("ix_syllabus_lessons_parent_lesson_id"), "syllabus_lessons", ["parent_lesson_id"], unique=False)
    op.create_index("idx_lessons_parent_order", "syllabus_lessons", ["parent_lesson_id", "order_index"], unique=False)

    # 7. exam_papers (Academic catalog of G.C.E. A/L past papers and model tests)
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
    op.create_index(op.f("ix_exam_papers_subject_id"), "exam_papers", ["subject_id"], unique=False)
    op.create_index(op.f("ix_exam_papers_type"), "exam_papers", ["type"], unique=False)
    op.create_index(op.f("ix_exam_papers_year"), "exam_papers", ["year"], unique=False)
    op.create_index("idx_exam_papers_subject_year", "exam_papers", ["subject_id", "year", "type"], unique=False)

    # 8. questions
    op.create_table(
        "questions",
        sa.Column("id", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default=sa.text("''"), nullable=True),
        sa.Column("subject_id", sa.String(length=100), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.String(length=100), sa.ForeignKey("syllabus_lessons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exam_paper_id", sa.String(length=36), sa.ForeignKey("exam_papers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_text", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("content_url", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=50), server_default=sa.text("'SHORT'"), nullable=False),
        sa.Column("difficulty", sa.String(length=50), server_default=sa.text("'MEDIUM'"), nullable=False),
        sa.Column("schedule", sa.String(length=50), server_default=sa.text("'REGULAR'"), nullable=False),
        sa.Column("source", sa.String(length=50), server_default=sa.text("'PAST_PAPER'"), nullable=False),
        sa.Column("source_details", sa.Text(), server_default=sa.text("''"), nullable=True),
        sa.Column("allocated_marks", sa.Integer(), server_default=sa.text("25"), nullable=False),
        sa.Column("is_premium", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("day_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_questions_id"), "questions", ["id"], unique=False)
    op.create_index(op.f("ix_questions_subject_id"), "questions", ["subject_id"], unique=False)
    op.create_index(op.f("ix_questions_lesson_id"), "questions", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_questions_exam_paper_id"), "questions", ["exam_paper_id"], unique=False)
    op.create_index(op.f("ix_questions_scheduled_date"), "questions", ["scheduled_date"], unique=False)
    op.create_index(op.f("ix_questions_day_number"), "questions", ["day_number"], unique=False)
    op.create_index(op.f("ix_questions_is_deleted"), "questions", ["is_deleted"], unique=False)
    op.create_index("idx_questions_subject_lesson", "questions", ["subject_id", "lesson_id", "is_published", "is_deleted"], unique=False)

    # 9. marking_schemes
    op.create_table(
        "marking_schemes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("question_id", sa.String(length=100), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), server_default=sa.text("'Official Marking Scheme'"), nullable=False),
        sa.Column("description_si", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("total_marks", sa.Integer(), server_default=sa.text("25"), nullable=False),
        sa.Column("is_official", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_premium_only", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_marking_schemes_question_id"), "marking_schemes", ["question_id"], unique=False)
    op.create_index("idx_marking_schemes_question_id", "marking_schemes", ["question_id", "order_index"], unique=False)

    # 10. marking_scheme_steps (Normalized Step-by-Step Marking Rubric: Method, Accuracy, Final)
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
    op.create_index(op.f("ix_marking_scheme_steps_scheme_id"), "marking_scheme_steps", ["marking_scheme_id"], unique=False)
    op.create_index("idx_marking_steps_scheme_order", "marking_scheme_steps", ["marking_scheme_id", "order_index"], unique=False)

    # 11. study_notes
    op.create_table(
        "study_notes",
        sa.Column("id", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_id", sa.String(length=100), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.String(length=100), sa.ForeignKey("syllabus_lessons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("is_premium", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_study_notes_id"), "study_notes", ["id"], unique=False)
    op.create_index(op.f("ix_study_notes_subject_id"), "study_notes", ["subject_id"], unique=False)
    op.create_index(op.f("ix_study_notes_lesson_id"), "study_notes", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_study_notes_is_deleted"), "study_notes", ["is_deleted"], unique=False)
    op.create_index("idx_study_notes_subject_order", "study_notes", ["subject_id", "order_index", "created_at"], unique=False)
    op.create_index("idx_study_notes_subject_lesson", "study_notes", ["subject_id", "lesson_id", "order_index", "is_deleted"], unique=False)

    # 12. subscription_plans (Domain 7: Educational Access Tiers)
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=64), unique=True, nullable=False),
        sa.Column("name_si", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("description_si", sa.Text(), nullable=True),
        sa.Column("interval", sa.String(length=32), server_default=sa.text("'MONTH'"), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("features_si", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_subscription_plans_code"), "subscription_plans", ["code"], unique=True)
    op.create_index(op.f("ix_subscription_plans_is_active"), "subscription_plans", ["is_active"], unique=False)

    # 13. plan_prices (Minor-unit cents precision for exact currency math)
    op.create_table(
        "plan_prices",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'LKR'"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_plan_prices_plan_id"), "plan_prices", ["plan_id"], unique=False)
    op.create_index(op.f("ix_plan_prices_is_active"), "plan_prices", ["is_active"], unique=False)

    # 14. user_subscriptions
    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.String(length=100), nullable=False),
        sa.Column("subscription_plan_id", sa.String(length=36), sa.ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("original_transaction_id", sa.String(length=255), nullable=True),
        sa.Column("latest_transaction_id", sa.String(length=255), nullable=True),
        sa.Column("store_entitlement_id", sa.String(length=100), server_default=sa.text("'pro_access'"), nullable=True),
        sa.Column("amount_lkr", sa.Float(), nullable=True),
        sa.Column("slip_image_url", sa.Text(), nullable=True),
        sa.Column("reference_note", sa.String(length=500), nullable=True),
        sa.Column("admin_notes", sa.String(length=500), nullable=True),
        sa.Column("approved_by", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_auto_renew", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_user_subscriptions_user_id"), "user_subscriptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_subscriptions_plan_id"), "user_subscriptions", ["plan_id"], unique=False)
    op.create_index(op.f("ix_user_subscriptions_subscription_plan_id"), "user_subscriptions", ["subscription_plan_id"], unique=False)
    op.create_index(op.f("ix_user_subscriptions_status"), "user_subscriptions", ["status"], unique=False)
    op.create_index(op.f("ix_user_subscriptions_provider"), "user_subscriptions", ["provider"], unique=False)

    # 15. payments
    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("subscription_id", sa.String(length=36), sa.ForeignKey("user_subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'LKR'"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("external_transaction_id", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_index(op.f("ix_payments_subscription_id"), "payments", ["subscription_id"], unique=False)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)

    # 16. bank_transfer_slips
    op.create_table(
        "bank_transfer_slips",
        sa.Column("payment_id", sa.String(length=36), sa.ForeignKey("payments.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("slip_image_url", sa.Text(), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=True),
        sa.Column("deposit_reference", sa.String(length=100), nullable=True),
        sa.Column("depositor_note", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=32), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("reviewed_by", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_bank_transfer_slips_review_status"), "bank_transfer_slips", ["review_status"], unique=False)

    # 17. processed_webhook_events
    op.create_table(
        "processed_webhook_events",
        sa.Column("event_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("app_user_id", sa.String(length=128), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_processed_webhook_events_app_user_id"), "processed_webhook_events", ["app_user_id"], unique=False)

    # 18. daily_challenges
    op.create_table(
        "daily_challenges",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_id", sa.String(length=100), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_duration_seconds", sa.Integer(), server_default=sa.text("3600"), nullable=False),
        sa.Column("total_marks", sa.Integer(), server_default=sa.text("50"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_daily_challenges_day_number"), "daily_challenges", ["day_number"], unique=True)
    op.create_index(op.f("ix_daily_challenges_scheduled_date"), "daily_challenges", ["scheduled_date"], unique=False)
    op.create_index(op.f("ix_daily_challenges_subject_id"), "daily_challenges", ["subject_id"], unique=False)

    # 19. daily_challenge_questions
    op.create_table(
        "daily_challenge_questions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("daily_challenge_id", sa.String(length=36), sa.ForeignKey("daily_challenges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.String(length=100), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("section", sa.String(length=50), server_default=sa.text("'SHORT'"), nullable=False),
        sa.Column("allocated_marks", sa.Integer(), server_default=sa.text("25"), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_daily_challenge_questions_challenge_id"), "daily_challenge_questions", ["daily_challenge_id"], unique=False)
    op.create_index(op.f("ix_daily_challenge_questions_question_id"), "daily_challenge_questions", ["question_id"], unique=False)

    # 20. user_question_attempts
    op.create_table(
        "user_question_attempts",
        sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.String(length=100), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("time_spent_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_attempt_duration_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("target_duration_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("was_overtime", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_daily_question", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_bookmarked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("confidence", sa.String(length=50), server_default=sa.text("'MEDIUM'"), nullable=False),
        sa.Column("student_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_user_question_attempts_user_id"), "user_question_attempts", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_question_attempts_question_id"), "user_question_attempts", ["question_id"], unique=False)
    op.create_index("idx_attempts_user_question", "user_question_attempts", ["user_id", "question_id"], unique=False)

    # 21. user_daily_activities
    op.create_table(
        "user_daily_activities",
        sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("date_key", sa.String(length=10), nullable=False),
        sa.Column("questions_solved_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_time_spent_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("daily_challenge_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_user_daily_activities_user_id"), "user_daily_activities", ["user_id"], unique=False)
    op.create_index("idx_activities_user_date", "user_daily_activities", ["user_id", "date_key"], unique=False)

    # 22. xp_transactions (Domain 5: Audit ledger for user XP gains and penalties)
    op.create_table(
        "xp_transactions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.uid", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), server_default=sa.text("'QUESTION_SOLVED'"), nullable=False),
        sa.Column("attempt_id", sa.String(length=255), nullable=True),
        sa.Column("question_id", sa.String(length=100), nullable=True),
        sa.Column("description_si", sa.String(length=255), nullable=True),
        sa.Column("description_en", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(op.f("ix_xp_transactions_user_id"), "xp_transactions", ["user_id"], unique=False)
    op.create_index(op.f("ix_xp_transactions_created_at"), "xp_transactions", ["created_at"], unique=False)
    op.create_index("idx_xp_trans_user_date", "xp_transactions", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    """Drop all 22 tables in reverse dependency order."""
    op.drop_table("xp_transactions")
    op.drop_table("user_daily_activities")
    op.drop_table("user_question_attempts")
    op.drop_table("daily_challenge_questions")
    op.drop_table("daily_challenges")
    op.drop_table("processed_webhook_events")
    op.drop_table("bank_transfer_slips")
    op.drop_table("payments")
    op.drop_table("user_subscriptions")
    op.drop_table("plan_prices")
    op.drop_table("subscription_plans")
    op.drop_table("study_notes")
    op.drop_table("marking_scheme_steps")
    op.drop_table("marking_schemes")
    op.drop_table("questions")
    op.drop_table("exam_papers")
    op.drop_table("syllabus_lessons")
    op.drop_table("subjects")
    op.drop_table("user_stats")
    op.drop_table("student_profiles")
    op.drop_table("users")
    op.drop_table("districts")
