"""add_soft_deletes_and_partial_indexes

Revision ID: c83e10d94f21
Revises: b72f89c031d4
Create Date: 2026-11-02 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c83e10d94f21'
down_revision: Union[str, Sequence[str], None] = 'b72f89c031d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add soft-delete support and partial indexing for performance and data preservation."""
    # 1. Soft-delete for questions
    op.add_column('questions', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index(op.f('ix_questions_is_deleted'), 'questions', ['is_deleted'], unique=False)
    op.drop_index('idx_questions_subject_lesson', table_name='questions')
    op.create_index('idx_questions_subject_lesson', 'questions', ['subject_id', 'lesson_id', 'is_published', 'is_deleted'], unique=False)

    # 2. Soft-delete for study notes
    op.add_column('study_notes', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index(op.f('ix_study_notes_is_deleted'), 'study_notes', ['is_deleted'], unique=False)
    op.drop_index('idx_study_notes_subject_lesson', table_name='study_notes')
    op.create_index('idx_study_notes_subject_lesson', 'study_notes', ['subject_id', 'lesson_id', 'order_index', 'is_deleted'], unique=False)

    # 3. Partial index on active user subscriptions for sub-millisecond lookups
    op.create_index(
        'idx_active_subs_partial',
        'user_subscriptions',
        ['user_id'],
        unique=False,
        postgresql_where=sa.text("status IN ('ACTIVE', 'GRACE_PERIOD')"),
    )


def downgrade() -> None:
    """Revert soft-deletes and partial indexes."""
    op.drop_index('idx_active_subs_partial', table_name='user_subscriptions')

    op.drop_index('idx_study_notes_subject_lesson', table_name='study_notes')
    op.create_index('idx_study_notes_subject_lesson', 'study_notes', ['subject_id', 'lesson_id', 'order_index'], unique=False)
    op.drop_index(op.f('ix_study_notes_is_deleted'), table_name='study_notes')
    op.drop_column('study_notes', 'is_deleted')

    op.drop_index('idx_questions_subject_lesson', table_name='questions')
    op.create_index('idx_questions_subject_lesson', 'questions', ['subject_id', 'lesson_id', 'is_published'], unique=False)
    op.drop_index(op.f('ix_questions_is_deleted'), table_name='questions')
    op.drop_column('questions', 'is_deleted')
