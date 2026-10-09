"""site_settings: the site brand (name, logo, mascot, wordmark colors) edited in /admin (UPS-041)

Singleton row (id = 1), seeded with the brand the web shipped with until now.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

DEFAULTS = {
    "id": 1,
    "name": "UpiixSol",
    "logo_url": "/brand/upiixsol/wordmark.png",
    "mascot_url": "/brand/upiixsol/mascot.png",
    "color_primary": "#00BF63",
    "color_secondary": "#04944F",
    "color_accent": "#F28034",
}


def upgrade() -> None:
    table = op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("mascot_url", sa.String(length=500), nullable=True),
        sa.Column("color_primary", sa.String(length=7), nullable=False),
        sa.Column("color_secondary", sa.String(length=7), nullable=False),
        sa.Column("color_accent", sa.String(length=7), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_settings")),
    )
    op.bulk_insert(table, [DEFAULTS])


def downgrade() -> None:
    op.drop_table("site_settings")
