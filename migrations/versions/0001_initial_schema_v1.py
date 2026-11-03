"""initial_schema_v1

Revision ID: 0001_initial_schema_v1
Revises: 
Create Date: 2026-11-03 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema_v1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SRI_LANKAN_DISTRICTS = [
    # Western Province
    {"id": 1, "code": "COLOMBO", "name_en": "Colombo", "name_si": "කොළඹ", "name_ta": "கொழும்பு", "province": "WESTERN", "display_order": 1},
    {"id": 2, "code": "GAMPAHA", "name_en": "Gampaha", "name_si": "ගම්පහ", "name_ta": "கம்பஹா", "province": "WESTERN", "display_order": 2},
    {"id": 3, "code": "KALUTARA", "name_en": "Kalutara", "name_si": "කළුතර", "name_ta": "களுத்துறை", "province": "WESTERN", "display_order": 3},
    # Central Province
    {"id": 4, "code": "KANDY", "name_en": "Kandy", "name_si": "මහනුවර", "name_ta": "கண்டி", "province": "CENTRAL", "display_order": 4},
    {"id": 5, "code": "MATALE", "name_en": "Matale", "name_si": "මාතලේ", "name_ta": "மாத்தளை", "province": "CENTRAL", "display_order": 5},
    {"id": 6, "code": "NUWARA_ELIYA", "name_en": "Nuwara Eliya", "name_si": "නුවරඑළිය", "name_ta": "நுவரெலியா", "province": "CENTRAL", "display_order": 6},
    # Southern Province
    {"id": 7, "code": "GALLE", "name_en": "Galle", "name_si": "ගාල්ල", "name_ta": "காலி", "province": "SOUTHERN", "display_order": 7},
    {"id": 8, "code": "MATARA", "name_en": "Matara", "name_si": "මාතර", "name_ta": "மாத்தறை", "province": "SOUTHERN", "display_order": 8},
    {"id": 9, "code": "HAMBANTOTA", "name_en": "Hambantota", "name_si": "හම්බන්තොට", "name_ta": "அம்பாந்தோட்டை", "province": "SOUTHERN", "display_order": 9},
    # Northern Province
    {"id": 10, "code": "JAFFNA", "name_en": "Jaffna", "name_si": "යාපනය", "name_ta": "யாழ்ப்பாணம்", "province": "NORTHERN", "display_order": 10},
    {"id": 11, "code": "KILINOCHCHI", "name_en": "Kilinochchi", "name_si": "කිලිනොච්චිය", "name_ta": "கிளிநொச்சி", "province": "NORTHERN", "display_order": 11},
    {"id": 12, "code": "MANNAR", "name_en": "Mannar", "name_si": "මන්නාරම", "name_ta": "மன்னார்", "province": "NORTHERN", "display_order": 12},
    {"id": 13, "code": "VAVUNIYA", "name_en": "Vavuniya", "name_si": "වවුනියාව", "name_ta": "வவுனியா", "province": "NORTHERN", "display_order": 13},
    {"id": 14, "code": "MULLAITIVU", "name_en": "Mullaitivu", "name_si": "මුලතිව්", "name_ta": "முல்லைத்தீவு", "province": "NORTHERN", "display_order": 14},
    # Eastern Province
    {"id": 15, "code": "BATTICALOA", "name_en": "Batticaloa", "name_si": "මඩකලපුව", "name_ta": "மட்டக்களப்பு", "province": "EASTERN", "display_order": 15},
    {"id": 16, "code": "AMPARA", "name_en": "Ampara", "name_si": "අම්පාර", "name_ta": "அம்பாறை", "province": "EASTERN", "display_order": 16},
    {"id": 17, "code": "TRINCOMALEE", "name_en": "Trincomalee", "name_si": "ත්‍රිකුණාමලය", "name_ta": "திருகோணமலை", "province": "EASTERN", "display_order": 17},
    # North Western Province
    {"id": 18, "code": "KURUNEGALA", "name_en": "Kurunegala", "name_si": "කුරුණෑගල", "name_ta": "குருணாகல்", "province": "NORTH_WESTERN", "display_order": 18},
    {"id": 19, "code": "PUTTALAM", "name_en": "Puttalam", "name_si": "පුත්තලම", "name_ta": "புத்தளம்", "province": "NORTH_WESTERN", "display_order": 19},
    # North Central Province
    {"id": 20, "code": "ANURADHAPURA", "name_en": "Anuradhapura", "name_si": "අනුරාධපුරය", "name_ta": "அனுராதபுரம்", "province": "NORTH_CENTRAL", "display_order": 20},
    {"id": 21, "code": "POLONNARUWA", "name_en": "Polonnaruwa", "name_si": "පොළොන්නරුව", "name_ta": "பொலன்னறுவை", "province": "NORTH_CENTRAL", "display_order": 21},
    # Uva Province
    {"id": 22, "code": "BADULLA", "name_en": "Badulla", "name_si": "බදුල්ල", "name_ta": "பதுளை", "province": "UVA", "display_order": 22},
    {"id": 23, "code": "MONARAGALA", "name_en": "Monaragala", "name_si": "මොනරාගල", "name_ta": "மொணරාகலை", "province": "UVA", "display_order": 23},
    # Sabaragamuwa Province
    {"id": 24, "code": "RATNAPURA", "name_en": "Ratnapura", "name_si": "රත්නපුර", "name_ta": "இரத்தினபுரி", "province": "SABARAGAMUWA", "display_order": 24},
    {"id": 25, "code": "KEGALLE", "name_en": "Kegalle", "name_si": "කෑගල්ල", "name_ta": "கேகாலை", "province": "SABARAGAMUWA", "display_order": 25},
]


def upgrade() -> None:
    """Create clean v1 baseline schema with all 12 production tables and seed districts."""

    # 1. districts
    districts_table = op.create_table(
        'districts',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('name_si', sa.String(length=100), nullable=False),
        sa.Column('name_ta', sa.String(length=100), nullable=False),
        sa.Column('province', sa.String(length=50), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_districts_code'), 'districts', ['code'], unique=True)
    op.create_index(op.f('ix_districts_province'), 'districts', ['province'], unique=False)

    # Pre-seed 25 Sri Lankan Districts
    op.bulk_insert(districts_table, SRI_LANKAN_DISTRICTS)

    # 2. subjects
    op.create_table(
        'subjects',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sinhala_name', sa.String(length=255), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subjects_id'), 'subjects', ['id'], unique=False)
    op.create_index(op.f('ix_subjects_code'), 'subjects', ['code'], unique=True)

    # 3. syllabus_lessons
    op.create_table(
        'syllabus_lessons',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('subject_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('sinhala_title', sa.String(length=255), nullable=True),
        sa.Column('order_index', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('question_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('premium_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_syllabus_lessons_id'), 'syllabus_lessons', ['id'], unique=False)
    op.create_index(op.f('ix_syllabus_lessons_subject_id'), 'syllabus_lessons', ['subject_id'], unique=False)

    # 4. questions
    op.create_table(
        'questions',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), server_default=sa.text("''"), nullable=True),
        sa.Column('subject_id', sa.String(length=100), nullable=False),
        sa.Column('lesson_id', sa.String(length=100), nullable=True),
        sa.Column('content_text', sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column('content_url', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=50), server_default=sa.text("'SHORT'"), nullable=False),
        sa.Column('difficulty', sa.String(length=50), server_default=sa.text("'MEDIUM'"), nullable=False),
        sa.Column('schedule', sa.String(length=50), server_default=sa.text("'REGULAR'"), nullable=False),
        sa.Column('source', sa.String(length=50), server_default=sa.text("'PAST_PAPER'"), nullable=False),
        sa.Column('source_details', sa.Text(), server_default=sa.text("''"), nullable=True),
        sa.Column('allocated_marks', sa.Integer(), server_default=sa.text('25'), nullable=False),
        sa.Column('is_premium', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_published', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['lesson_id'], ['syllabus_lessons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)
    op.create_index(op.f('ix_questions_subject_id'), 'questions', ['subject_id'], unique=False)
    op.create_index(op.f('ix_questions_lesson_id'), 'questions', ['lesson_id'], unique=False)
    op.create_index(op.f('ix_questions_scheduled_date'), 'questions', ['scheduled_date'], unique=False)
    op.create_index(op.f('ix_questions_is_deleted'), 'questions', ['is_deleted'], unique=False)
    op.create_index('idx_questions_subject_lesson', 'questions', ['subject_id', 'lesson_id', 'is_published', 'is_deleted'], unique=False)

    # 5. marking_schemes
    op.create_table(
        'marking_schemes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), server_default=sa.text("'Official Marking Scheme'"), nullable=False),
        sa.Column('content_text', sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.Column('total_marks', sa.Integer(), server_default=sa.text('25'), nullable=False),
        sa.Column('is_official', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_premium_only', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_marking_schemes_question_id'), 'marking_schemes', ['question_id'], unique=False)
    op.create_index('idx_marking_schemes_question_id', 'marking_schemes', ['question_id', 'order_index'], unique=False)

    # 6. study_notes
    op.create_table(
        'study_notes',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject_id', sa.String(length=100), nullable=False),
        sa.Column('lesson_id', sa.String(length=100), nullable=True),
        sa.Column('content_text', sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.Column('is_premium', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['lesson_id'], ['syllabus_lessons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_notes_id'), 'study_notes', ['id'], unique=False)
    op.create_index(op.f('ix_study_notes_subject_id'), 'study_notes', ['subject_id'], unique=False)
    op.create_index(op.f('ix_study_notes_lesson_id'), 'study_notes', ['lesson_id'], unique=False)
    op.create_index(op.f('ix_study_notes_is_deleted'), 'study_notes', ['is_deleted'], unique=False)
    op.create_index('idx_study_notes_subject_order', 'study_notes', ['subject_id', 'order_index', 'created_at'], unique=False)
    op.create_index('idx_study_notes_subject_lesson', 'study_notes', ['subject_id', 'lesson_id', 'order_index', 'is_deleted'], unique=False)

    # 7. users
    op.create_table(
        'users',
        sa.Column('uid', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('telephone_no', sa.String(length=50), nullable=True),
        sa.Column('role', sa.String(length=50), server_default=sa.text("'USER'"), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('school_name', sa.String(length=255), nullable=True),
        sa.Column('district_id', sa.Integer(), nullable=True),
        sa.Column('stream', sa.String(length=50), nullable=True),
        sa.Column('grade', sa.String(length=50), nullable=True),
        sa.Column('attempt', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['district_id'], ['districts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('uid')
    )
    op.create_index(op.f('ix_users_uid'), 'users', ['uid'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_district_id'), 'users', ['district_id'], unique=False)

    # 8. user_stats
    op.create_table(
        'user_stats',
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('xp', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('current_streak_days', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('longest_streak_days', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_solved_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_study_time_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('accuracy_rate', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('last_active_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.uid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_user_stats_user_id'), 'user_stats', ['user_id'], unique=False)

    # 9. user_subscriptions
    op.create_table(
        'user_subscriptions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('plan_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('original_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('latest_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('store_entitlement_id', sa.String(length=100), server_default=sa.text("'pro_access'"), nullable=True),
        sa.Column('amount_lkr', sa.Float(), nullable=True),
        sa.Column('slip_image_url', sa.Text(), nullable=True),
        sa.Column('reference_note', sa.String(length=500), nullable=True),
        sa.Column('admin_notes', sa.String(length=500), nullable=True),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_auto_renew', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.uid'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.uid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_subscriptions_id'), 'user_subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_user_id'), 'user_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_plan_id'), 'user_subscriptions', ['plan_id'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_status'), 'user_subscriptions', ['status'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_provider'), 'user_subscriptions', ['provider'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_original_transaction_id'), 'user_subscriptions', ['original_transaction_id'], unique=False)
    op.create_index('idx_user_subs_active_lookup', 'user_subscriptions', ['user_id', 'status', 'expires_at'], unique=False)
    op.create_index(
        'idx_active_subs_partial',
        'user_subscriptions',
        ['user_id'],
        unique=False,
        postgresql_where=sa.text("status IN ('ACTIVE', 'GRACE_PERIOD')"),
    )

    # 10. processed_webhook_events
    op.create_table(
        'processed_webhook_events',
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('app_user_id', sa.String(length=128), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_processed_webhook_events_app_user_id'), 'processed_webhook_events', ['app_user_id'], unique=False)

    # 11. user_question_attempts
    op.create_table(
        'user_question_attempts',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('question_id', sa.String(length=100), nullable=False),
        sa.Column('time_spent_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('target_duration_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('was_overtime', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('is_daily_question', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('completed_date', sa.Date(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_bookmarked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('confidence', sa.String(length=50), nullable=True),
        sa.Column('student_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.uid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'question_id', name='uq_user_question_attempt')
    )
    op.create_index(op.f('ix_user_question_attempts_user_id'), 'user_question_attempts', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_question_attempts_question_id'), 'user_question_attempts', ['question_id'], unique=False)
    op.create_index(op.f('ix_user_question_attempts_completed_date'), 'user_question_attempts', ['completed_date'], unique=False)
    op.create_index('idx_attempt_user_question', 'user_question_attempts', ['user_id', 'question_id'], unique=False)
    op.create_index('idx_attempt_user_date', 'user_question_attempts', ['user_id', 'completed_date'], unique=False)

    # 12. user_daily_activities
    op.create_table(
        'user_daily_activities',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('date_key', sa.String(length=10), nullable=False),
        sa.Column('questions_solved_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_time_spent_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('daily_challenge_completed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.uid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date_key', name='uq_user_daily_activity')
    )
    op.create_index(op.f('ix_user_daily_activities_user_id'), 'user_daily_activities', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_daily_activities_date_key'), 'user_daily_activities', ['date_key'], unique=False)
    op.create_index('idx_daily_activity_user_date', 'user_daily_activities', ['user_id', 'date_key'], unique=False)


def downgrade() -> None:
    """Drop all v1 tables in reverse topological order."""
    op.drop_table('user_daily_activities')
    op.drop_table('user_question_attempts')
    op.drop_table('processed_webhook_events')
    op.drop_table('user_subscriptions')
    op.drop_table('user_stats')
    op.drop_table('users')
    op.drop_table('study_notes')
    op.drop_table('marking_schemes')
    op.drop_table('questions')
    op.drop_table('syllabus_lessons')
    op.drop_table('subjects')
    op.drop_table('districts')
