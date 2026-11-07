"""drop_question_schedule_column

Revision ID: 0007_drop_question_schedule_column
Revises: 0006_drop_marking_scheme_steps
Create Date: 2026-11-07 02:05:00.000000

Drops the redundant `schedule` column from the `questions` table.
Daily Challenge membership and release dates are already canonically represented
by `day_number` and `scheduled_date`.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_drop_question_schedule_column"
down_revision: Union[str, None] = "0006_drop_marking_scheme_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "questions" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("questions")}
        if "schedule" in columns:
            op.drop_column("questions", "schedule")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "questions" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("questions")}
        if "schedule" not in columns:
            op.add_column(
                "questions",
                sa.Column(
                    "schedule",
                    sa.String(length=50),
                    nullable=False,
                    server_default=sa.text("'REGULAR'"),
                ),
            )
