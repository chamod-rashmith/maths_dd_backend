"""drop_question_difficulty_column

Revision ID: 0008_drop_question_difficulty_column
Revises: 0007_drop_question_schedule_column
Create Date: 2026-11-07 08:15:00.000000

Drops the `difficulty` column from the `questions` table.
Questions are categorized objectively by `type` (SHORT/ESSAY), `allocated_marks`,
and `source`, while perceived difficulty is captured per-student via `confidence`
on `user_question_attempts`.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_drop_question_difficulty_column"
down_revision: Union[str, None] = "0007_drop_question_schedule_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "questions" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("questions")}
        if "difficulty" in columns:
            op.drop_column("questions", "difficulty")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "questions" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("questions")}
        if "difficulty" not in columns:
            op.add_column(
                "questions",
                sa.Column(
                    "difficulty",
                    sa.String(length=50),
                    nullable=False,
                    server_default=sa.text("'MEDIUM'"),
                ),
            )
