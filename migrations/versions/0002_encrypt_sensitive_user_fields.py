"""Allow encrypted sensitive user fields to be stored.

Revision ID: 0002_encrypt_sensitive_user_fields
Revises: 0001_initial_schema_v1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_encrypt_sensitive_user_fields"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Expand telephone storage for authenticated encrypted values."""
    op.alter_column(
        "users",
        "telephone_no",
        existing_type=sa.String(length=50),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Restore the legacy telephone column size."""
    op.alter_column(
        "users",
        "telephone_no",
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
