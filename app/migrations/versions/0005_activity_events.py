"""activity_events: append-only usage analytics stream (UPS-037)

One row per thing a user did (lesson completed, post created, page viewed...). See docs/analytics.md.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

INDEXES = {
    "ix_activity_events_occurred_at": ["occurred_at"],
    "ix_activity_events_name_occurred_at": ["name", "occurred_at"],
    "ix_activity_events_user_id_occurred_at": ["user_id", "occurred_at"],
    "ix_activity_events_academy_id_occurred_at": ["academy_id", "occurred_at"],
}


def upgrade() -> None:
    op.create_table(
        "activity_events",
        sa.Column(
            "id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("academy_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=True),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.CheckConstraint("source IN ('server', 'web')", name=op.f("ck_activity_events_source")),
        sa.ForeignKeyConstraint(
            ["academy_id"],
            ["academies.id"],
            name=op.f("fk_activity_events_academy_id_academies"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_activity_events_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_events")),
    )
    for name, columns in INDEXES.items():
        op.create_index(name, "activity_events", columns, unique=False)


def downgrade() -> None:
    for name in INDEXES:
        op.drop_index(name, table_name="activity_events")
    op.drop_table("activity_events")
