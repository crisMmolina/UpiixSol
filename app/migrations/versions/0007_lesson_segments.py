"""lessons: optional video segment start_s/end_s (UPS-045)

Expand only: two nullable columns (NULL = the whole video, as before) and their CHECKs. batch_alter_table so
SQLite can add the constraints. No backfill.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("lessons", schema=None) as batch_op:
        batch_op.add_column(sa.Column("start_s", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("end_s", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(op.f("ck_lessons_start_s"), "start_s IS NULL OR start_s >= 0")
        batch_op.create_check_constraint(op.f("ck_lessons_end_s"), "end_s IS NULL OR end_s > COALESCE(start_s, 0)")


def downgrade() -> None:
    with op.batch_alter_table("lessons", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_lessons_end_s"), type_="check")
        batch_op.drop_constraint(op.f("ck_lessons_start_s"), type_="check")
        batch_op.drop_column("end_s")
        batch_op.drop_column("start_s")
