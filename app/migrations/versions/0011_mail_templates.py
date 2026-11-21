"""mail_templates: saved email templates per scope (UPS-100, spec 005)

Expand-only: one new table. Downgrade drops it.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

INDEX = "uq_mail_templates_scope_academy_name"


def upgrade() -> None:
    op.create_table(
        "mail_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(length=7), nullable=False),
        sa.Column("academy_id", sa.Integer(), sa.ForeignKey("academies.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("description", sa.String(length=140)),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("preheader", sa.String(length=140)),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("scope IN ('site', 'academy')", name=op.f("ck_mail_templates_scope")),
        sa.CheckConstraint(
            "(scope = 'site' AND academy_id IS NULL) OR (scope = 'academy' AND academy_id IS NOT NULL)",
            name=op.f("ck_mail_templates_scope_academy"),
        ),
    )
    op.create_index(
        INDEX,
        "mail_templates",
        ["scope", sa.text("coalesce(academy_id, 0)"), sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(INDEX, table_name="mail_templates")
    op.drop_table("mail_templates")
