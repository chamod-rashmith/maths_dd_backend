"""create_user_subscriptions_table

Revision ID: b72f89c031d4
Revises: a41e98d19e02
Create Date: 2026-11-02 20:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b72f89c031d4'
down_revision: Union[str, Sequence[str], None] = 'a41e98d19e02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_subscriptions and processed_webhook_events tables, normalize users table."""
    # 1. Create user_subscriptions table
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

    # 2. Create processed_webhook_events table
    op.create_table(
        'processed_webhook_events',
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('app_user_id', sa.String(length=128), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_processed_webhook_events_app_user_id'), 'processed_webhook_events', ['app_user_id'], unique=False)

    # 3. Migrate existing premium users to user_subscriptions
    op.execute(
        """
        INSERT INTO user_subscriptions (
            id, user_id, plan_id, status, provider, starts_at, expires_at, is_auto_renew, created_at, updated_at
        )
        SELECT
            gen_random_uuid()::text,
            uid,
            'LIFETIME',
            'ACTIVE',
            'MANUAL_ADMIN',
            NOW(),
            CASE
                WHEN premium_expiry IS NOT NULL THEN (premium_expiry::timestamp at time zone 'UTC')
                ELSE NULL
            END,
            false,
            NOW(),
            NOW()
        FROM users
        WHERE is_premium = true;
        """
    )

    # 4. Drop is_premium and premium_expiry from users table
    op.drop_column('users', 'premium_expiry')
    op.drop_column('users', 'is_premium')


def downgrade() -> None:
    """Restore is_premium and premium_expiry columns, drop user_subscriptions."""
    # 1. Re-add columns to users
    op.add_column('users', sa.Column('is_premium', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('premium_expiry', sa.Date(), nullable=True))

    # 2. Backfill is_premium from user_subscriptions
    op.execute(
        """
        UPDATE users u
        SET
            is_premium = true,
            premium_expiry = s.expires_at::date
        FROM user_subscriptions s
        WHERE u.uid = s.user_id AND s.status = 'ACTIVE';
        """
    )

    # 3. Drop tables
    op.drop_table('processed_webhook_events')
    op.drop_table('user_subscriptions')
