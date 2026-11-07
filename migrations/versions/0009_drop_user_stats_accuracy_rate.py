"""drop_user_stats_accuracy_rate_column

Revision ID: 0009_drop_user_stats_accuracy_rate
Revises: 0008_drop_question_difficulty_column
Create Date: 2026-11-07 08:40:00.000000

Drops the `accuracy_rate` column from the `user_stats` table.
The platform operates on an active learning / self-learning philosophy
for Combined Mathematics, focusing on consistency (streaks), cumulative study
time, solved problem counts, and student self-assessed confidence rather than
simplistic binary quiz-style accuracy rates.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_drop_user_stats_accuracy_rate"
down_revision: Union[str, None] = "0008_drop_question_difficulty_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_stats" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("user_stats")}
        if "accuracy_rate" in columns:
            op.drop_column("user_stats", "accuracy_rate")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_stats" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("user_stats")}
        if "accuracy_rate" not in columns:
            op.add_column(
                "user_stats",
                sa.Column(
                    "accuracy_rate",
                    sa.Float(),
                    server_default=sa.text("0.0"),
                    nullable=False,
                ),
            )
