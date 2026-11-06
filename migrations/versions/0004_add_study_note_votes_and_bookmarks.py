"""Add study_note_votes and study_note_bookmarks normalized tables and vote counters.

Revision ID: 0004_add_study_note_votes_and_bookmarks
Revises: 0003_add_admin_totp_credentials
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_study_note_votes_and_bookmarks"
down_revision: Union[str, Sequence[str], None] = "0003_add_admin_totp_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add upvote_count/downvote_count to study_notes and create normalized votes & bookmarks tables."""
    op.add_column(
        "study_notes",
        sa.Column(
            "upvote_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "study_notes",
        sa.Column(
            "downvote_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )

    op.create_table(
        "study_note_votes",
        sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=128),
            sa.ForeignKey("users.uid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "note_id",
            sa.String(length=100),
            sa.ForeignKey("study_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vote_type", sa.SmallInteger(), nullable=False),
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
        sa.UniqueConstraint("user_id", "note_id", name="uq_study_note_votes_user_note"),
        sa.CheckConstraint("vote_type IN (1, -1)", name="ck_study_note_votes_valid_type"),
    )
    op.create_index("ix_study_note_votes_user_id", "study_note_votes", ["user_id"], unique=False)
    op.create_index("ix_study_note_votes_note_id", "study_note_votes", ["note_id"], unique=False)
    op.create_index(
        "idx_study_note_votes_user_note",
        "study_note_votes",
        ["user_id", "note_id"],
        unique=False,
    )
    op.create_index(
        "idx_study_note_votes_note_type",
        "study_note_votes",
        ["note_id", "vote_type"],
        unique=False,
    )

    op.create_table(
        "study_note_bookmarks",
        sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=128),
            sa.ForeignKey("users.uid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "note_id",
            sa.String(length=100),
            sa.ForeignKey("study_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "note_id", name="uq_study_note_bookmarks_user_note"),
    )
    op.create_index("ix_study_note_bookmarks_user_id", "study_note_bookmarks", ["user_id"], unique=False)
    op.create_index("ix_study_note_bookmarks_note_id", "study_note_bookmarks", ["note_id"], unique=False)
    op.create_index(
        "idx_study_note_bookmarks_user_note",
        "study_note_bookmarks",
        ["user_id", "note_id"],
        unique=False,
    )
    op.create_index(
        "idx_study_note_bookmarks_user_created",
        "study_note_bookmarks",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop study_note_bookmarks and study_note_votes tables and remove counter columns."""
    op.drop_index("idx_study_note_bookmarks_user_created", table_name="study_note_bookmarks")
    op.drop_index("idx_study_note_bookmarks_user_note", table_name="study_note_bookmarks")
    op.drop_index("ix_study_note_bookmarks_note_id", table_name="study_note_bookmarks")
    op.drop_index("ix_study_note_bookmarks_user_id", table_name="study_note_bookmarks")
    op.drop_table("study_note_bookmarks")

    op.drop_index("idx_study_note_votes_note_type", table_name="study_note_votes")
    op.drop_index("idx_study_note_votes_user_note", table_name="study_note_votes")
    op.drop_index("ix_study_note_votes_note_id", table_name="study_note_votes")
    op.drop_index("ix_study_note_votes_user_id", table_name="study_note_votes")
    op.drop_table("study_note_votes")

    op.drop_column("study_notes", "downvote_count")
    op.drop_column("study_notes", "upvote_count")
