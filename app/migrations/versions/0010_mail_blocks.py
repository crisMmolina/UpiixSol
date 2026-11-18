"""mail_campaigns: block content, sender club, preheader, Reply-To and .ics token (UPS-085, spec 004)

Expand-only: five nullable columns; legacy rows keep `body` and `content` NULL. Downgrade drops them.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

FK = "fk_mail_campaigns_sender_academy_id_academies"
UQ = "uq_mail_campaigns_ics_token"


def upgrade() -> None:
    # batch mode: SQLite cannot add constraints with ALTER; PostgreSQL gets plain ALTERs.
    with op.batch_alter_table("mail_campaigns") as batch:
        batch.add_column(sa.Column("content", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("sender_academy_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("preheader", sa.String(length=140), nullable=True))
        batch.add_column(sa.Column("reply_to", sa.String(length=254), nullable=True))
        batch.add_column(sa.Column("ics_token", sa.String(length=43), nullable=True))
        batch.create_foreign_key(FK, "academies", ["sender_academy_id"], ["id"], ondelete="SET NULL")
        batch.create_unique_constraint(UQ, ["ics_token"])


def downgrade() -> None:
    with op.batch_alter_table("mail_campaigns") as batch:
        batch.drop_constraint(UQ, type_="unique")
        batch.drop_constraint(FK, type_="foreignkey")
        batch.drop_column("ics_token")
        batch.drop_column("reply_to")
        batch.drop_column("preheader")
        batch.drop_column("sender_academy_id")
        batch.drop_column("content")
