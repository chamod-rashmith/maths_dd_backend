"""decouple_user_stats_table

Revision ID: a41e98d19e02
Revises: 6f1863b5fc11
Create Date: 2026-11-02 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a41e98d19e02'
down_revision: Union[str, Sequence[str], None] = '6f1863b5fc11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Decouple gamification telemetry into user_stats table."""
    # 1. Create user_stats table
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

    # 2. Backfill existing user telemetry into user_stats
    op.execute(
        """
        INSERT INTO user_stats (
            user_id, xp, current_streak_days, longest_streak_days,
            total_solved_count, total_study_time_seconds, accuracy_rate,
            last_active_date, updated_at
        )
        SELECT
            uid,
            COALESCE(xp, 0),
            COALESCE(current_streak_days, 0),
            COALESCE(longest_streak_days, 0),
            COALESCE(total_solved_count, 0),
            COALESCE(total_study_time_seconds, 0),
            COALESCE(accuracy_rate, 0.0),
            last_active_date,
            NOW()
        FROM users
        ON CONFLICT (user_id) DO NOTHING;
        """
    )

    # 3. Drop gamification & telemetry columns from users table
    op.drop_column('users', 'last_active_date')
    op.drop_column('users', 'accuracy_rate')
    op.drop_column('users', 'total_study_time_seconds')
    op.drop_column('users', 'total_solved_count')
    op.drop_column('users', 'questions_solved')
    op.drop_column('users', 'longest_streak_days')
    op.drop_column('users', 'current_streak_days')
    op.drop_column('users', 'streak_count')
    op.drop_column('users', 'xp')


def downgrade() -> None:
    """Restore telemetry columns to users table and drop user_stats."""
    # 1. Re-add telemetry columns to users
    op.add_column('users', sa.Column('xp', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('streak_count', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('current_streak_days', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('longest_streak_days', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('questions_solved', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('total_solved_count', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('total_study_time_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('users', sa.Column('accuracy_rate', sa.Float(), server_default=sa.text('0.0'), nullable=False))
    op.add_column('users', sa.Column('last_active_date', sa.Date(), nullable=True))

    # 2. Copy data back to users from user_stats
    op.execute(
        """
        UPDATE users u
        SET
            xp = s.xp,
            streak_count = s.current_streak_days,
            current_streak_days = s.current_streak_days,
            longest_streak_days = s.longest_streak_days,
            questions_solved = s.total_solved_count,
            total_solved_count = s.total_solved_count,
            total_study_time_seconds = s.total_study_time_seconds,
            accuracy_rate = s.accuracy_rate,
            last_active_date = s.last_active_date
        FROM user_stats s
        WHERE u.uid = s.user_id;
        """
    )

    # 3. Drop user_stats table
    op.drop_index(op.f('ix_user_stats_user_id'), table_name='user_stats')
    op.drop_table('user_stats')
