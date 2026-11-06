"""Create admin_totp_credentials table for RFC 6238 TOTP & recovery codes.

Revision ID: 0003_add_admin_totp_credentials
Revises: 0002_encrypt_sensitive_user_fields
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_admin_totp_credentials"
down_revision: Union[str, Sequence[str], None] = "0002_encrypt_sensitive_user_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create admin_totp_credentials table for encrypted TOTP secrets and hashed recovery codes."""
    op.create_table(
        "admin_totp_credentials",
        sa.Column(
            "user_id",
            sa.String(length=128),
            sa.ForeignKey("users.uid", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column(
            "recovery_codes_hash",
            sa.Text(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_admin_totp_credentials_user_id",
        "admin_totp_credentials",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop admin_totp_credentials table."""
    op.drop_index("ix_admin_totp_credentials_user_id", table_name="admin_totp_credentials")
    op.drop_table("admin_totp_credentials")
