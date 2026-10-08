"""media_objects: uploaded files stored in the database (UPS-030)

Used when MEDIA_STORAGE=database (hosts whose disk is wiped on restart). Empty otherwise.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_objects",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=40), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_media_objects")),
    )


def downgrade() -> None:
    op.drop_table("media_objects")
