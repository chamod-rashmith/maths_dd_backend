"""Add admin_audit_logs immutable table (Ring 4) and user_stats leaderboard index.

Revision ID: 0005_add_admin_audit_logs_and_leaderboard_index
Revises: 0004_add_study_note_votes_and_bookmarks
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_admin_audit_logs_and_leaderboard_index"
down_revision: Union[str, Sequence[str], None] = "0004_add_study_note_votes_and_bookmarks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create admin_audit_logs table and composite leaderboard index on user_stats."""
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("actor_uid", sa.String(length=128), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_method", sa.String(length=16), nullable=True),
        sa.Column("request_path", sa.String(length=255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_admin_audit_logs_actor_uid", "admin_audit_logs", ["actor_uid"], unique=False)
    op.create_index("ix_admin_audit_logs_actor_role", "admin_audit_logs", ["actor_role"], unique=False)
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"], unique=False)
    op.create_index("ix_admin_audit_logs_resource_type", "admin_audit_logs", ["resource_type"], unique=False)
    op.create_index("ix_admin_audit_logs_resource_id", "admin_audit_logs", ["resource_id"], unique=False)
    op.create_index("ix_admin_audit_logs_ip_address", "admin_audit_logs", ["ip_address"], unique=False)
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"], unique=False)
    op.create_index(
        "idx_admin_audit_logs_actor_created",
        "admin_audit_logs",
        ["actor_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_admin_audit_logs_action_created",
        "admin_audit_logs",
        ["action", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_admin_audit_logs_resource",
        "admin_audit_logs",
        ["resource_type", "resource_id"],
        unique=False,
    )

    op.create_index(
        "idx_user_stats_leaderboard_xp",
        "user_stats",
        ["xp", "total_solved_count", "current_streak_days"],
        unique=False,
    )


def downgrade() -> None:
    """Drop user_stats leaderboard index and admin_audit_logs table."""
    op.drop_index("idx_user_stats_leaderboard_xp", table_name="user_stats")

    op.drop_index("idx_admin_audit_logs_resource", table_name="admin_audit_logs")
    op.drop_index("idx_admin_audit_logs_action_created", table_name="admin_audit_logs")
    op.drop_index("idx_admin_audit_logs_actor_created", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_ip_address", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_resource_id", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_resource_type", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_actor_role", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_actor_uid", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
