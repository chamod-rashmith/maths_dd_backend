"""Add subscription_plans, plan_prices, payments, and bank_transfer_slips tables.

Revision ID: 0004_billing_and_bank_slips
Revises: 0003_daily_challenge_sets
Create Date: 2026-11-04 10:20:00.000000

This migration establishes the normalized (3NF/BCNF) Billing & Subscriptions architecture:
1. `subscription_plans`: Catalog of educational access tiers (Monthly, Annual, Lifetime).
2. `plan_prices`: Strict integer minor-unit pricing (cents / ශත) to prevent float inaccuracies.
3. `payments`: Normalized ledger of all financial transactions across providers.
4. `bank_transfer_slips`: Dedicated evidence and audit entity for Sri Lankan bank deposit verification.
5. Seeds standard initial plans and pricing (LKR 2,500 monthly, LKR 24,000 annual, LKR 50,000 lifetime).
"""

from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_billing_and_bank_slips"
down_revision: Union[str, Sequence[str], None] = "0003_daily_challenge_sets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create normalized billing tables, foreign keys, indexes, and seed default plans."""

    # 1. Create subscription_plans table
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
    op.create_index("ix_subscription_plans_code", "subscription_plans", ["code"], unique=True)
    op.create_index("ix_subscription_plans_is_active", "subscription_plans", ["is_active"], unique=False)

    # 2. Create plan_prices table
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
    op.create_index("ix_plan_prices_plan_id", "plan_prices", ["plan_id"], unique=False)
    op.create_index("ix_plan_prices_is_active", "plan_prices", ["is_active"], unique=False)

    # 3. Add subscription_plan_id to user_subscriptions
    with op.batch_alter_table("user_subscriptions") as batch_op:
        batch_op.add_column(sa.Column("subscription_plan_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_user_subscriptions_plan_id",
            "subscription_plans",
            ["subscription_plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_user_subscriptions_sub_plan_id", ["subscription_plan_id"], unique=False)

    # 4. Create payments table
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
    op.create_index("ix_payments_subscription_id", "payments", ["subscription_id"], unique=False)
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)
    op.create_index("ix_payments_method", "payments", ["method"], unique=False)
    op.create_index("ix_payments_status", "payments", ["status"], unique=False)
    op.create_index("ix_payments_external_tx_id", "payments", ["external_transaction_id"], unique=False)

    # 5. Create bank_transfer_slips table
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
    op.create_index("ix_bank_transfer_slips_review_status", "bank_transfer_slips", ["review_status"], unique=False)

    # 6. Seed Default Subscription Plans & Minor-Unit Prices
    # Use deterministic UUIDs for seeded records so repeated runs or migrations stay idempotent
    monthly_plan_id = "00000000-0000-4000-a000-000000000001"
    annual_plan_id = "00000000-0000-4000-a000-000000000002"
    lifetime_plan_id = "00000000-0000-4000-a000-000000000003"

    plans_table = sa.table(
        "subscription_plans",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name_si", sa.String),
        sa.column("name_en", sa.String),
        sa.column("description_si", sa.Text),
        sa.column("interval", sa.String),
        sa.column("duration_days", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("display_order", sa.Integer),
        sa.column("features_si", sa.Text),
    )

    prices_table = sa.table(
        "plan_prices",
        sa.column("id", sa.String),
        sa.column("plan_id", sa.String),
        sa.column("currency", sa.String),
        sa.column("amount_minor", sa.BigInteger),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        plans_table,
        [
            {
                "id": monthly_plan_id,
                "code": "COMBINED_PRO_MONTHLY",
                "name_si": "සංයුක්ත ගණිතය මාසික සාමාජිකත්වය",
                "name_en": "Combined Maths Pro Monthly",
                "description_si": "සියලුම පසුගිය විභාග ප්‍රශ්න, ලකුණු දීමේ පටිපාටි සහ දිනපතා අභ්‍යාස සඳහා දින 30ක පූර්ණ ප්‍රවේශය.",
                "interval": "MONTH",
                "duration_days": 30,
                "is_active": True,
                "display_order": 1,
                "features_si": "සියලුම Theory සටහන්, වීඩියෝ විවරණ, ලකුණු දීමේ පටිපාටි (Marking Schemes), දිනපතා Challenge Series",
            },
            {
                "id": annual_plan_id,
                "code": "COMBINED_PRO_ANNUAL",
                "name_si": "සංයුක්ත ගණිතය වාර්ෂික සාමාජිකත්වය",
                "name_en": "Combined Maths Pro Annual",
                "description_si": "වසරක් පුරා විභාගය දක්වා අසීමිත ප්‍රවේශය. 20% ඉතිරියක් සහිතයි.",
                "interval": "YEAR",
                "duration_days": 365,
                "is_active": True,
                "display_order": 2,
                "features_si": "මාසික සැලැස්මේ සියලුම පහසුකම් + වසර පුරා Model Papers සහ විභාග පෙරහුරු ප්‍රශ්නාවලි",
            },
            {
                "id": lifetime_plan_id,
                "code": "LIFETIME",
                "name_si": "සම්පූර්ණ ජීවිත කාලීන සාමාජිකත්වය",
                "name_en": "Combined Maths Lifetime Access",
                "description_si": "කල් ඉකුත් වීමක් නොමැත. A/L විභාගය අවසන් වන තෙක් සියලුම යාවත්කාලීන කිරීම් සමඟ අසීමිත ප්‍රවේශය.",
                "interval": "LIFETIME",
                "duration_days": None,
                "is_active": True,
                "display_order": 3,
                "features_si": "ජීවිත කාලීන අසීමිත ප්‍රවේශය, සියලුම අනාගත පාඩම් මාලා සහ ප්‍රශ්න පත්‍ර",
            },
        ],
    )

    op.bulk_insert(
        prices_table,
        [
            {
                "id": "00000000-0000-4000-b000-000000000001",
                "plan_id": monthly_plan_id,
                "currency": "LKR",
                "amount_minor": 250000,  # Rs. 2,500.00
                "is_active": True,
            },
            {
                "id": "00000000-0000-4000-b000-000000000002",
                "plan_id": annual_plan_id,
                "currency": "LKR",
                "amount_minor": 2400000,  # Rs. 24,000.00
                "is_active": True,
            },
            {
                "id": "00000000-0000-4000-b000-000000000003",
                "plan_id": lifetime_plan_id,
                "currency": "LKR",
                "amount_minor": 5000000,  # Rs. 50,000.00
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    """Drop billing tables in reverse dependency order."""
    op.drop_table("bank_transfer_slips")
    op.drop_table("payments")
    with op.batch_alter_table("user_subscriptions") as batch_op:
        batch_op.drop_constraint("fk_user_subscriptions_plan_id", type_="foreignkey")
        batch_op.drop_index("ix_user_subscriptions_sub_plan_id")
        batch_op.drop_column("subscription_plan_id")
    op.drop_table("plan_prices")
    op.drop_table("subscription_plans")
