"""mail_campaigns, mail_recipients, mail_suppressions: the email channel (UPS-072, spec 003)

Expand-only: three new tables, nothing existing changes. Downgrade drops them (children first).

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

NOW = sa.text("(CURRENT_TIMESTAMP)")
INDEXES = {
    "mail_campaigns": {
        "ix_mail_campaigns_sender_id": ["sender_id"],
        "ix_mail_campaigns_academy_id_created_at": ["academy_id", "created_at"],
    },
    "mail_recipients": {
        "ix_mail_recipients_status": ["status"],
        "ix_mail_recipients_created_at": ["created_at"],
    },
}


def upgrade() -> None:
    op.create_table(
        "mail_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("academy_id", sa.Integer(), nullable=True),
        sa.Column("audience_kind", sa.String(length=12), nullable=False),
        sa.Column("audience_params", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("recipient_count", sa.Integer(), nullable=False),
        sa.Column("counts_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "audience_kind IN ('all', 'academy', 'role', 'individual')",
            name=op.f("ck_mail_campaigns_audience_kind"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'sending', 'sent', 'partial', 'failed')",
            name=op.f("ck_mail_campaigns_status"),
        ),
        sa.ForeignKeyConstraint(
            ["academy_id"],
            ["academies.id"],
            name=op.f("fk_mail_campaigns_academy_id_academies"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["users.id"], name=op.f("fk_mail_campaigns_sender_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_campaigns")),
    )
    op.create_table(
        "mail_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("unsubscribe_token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'delivered', 'failed', 'bounced', 'complained')",
            name=op.f("ck_mail_recipients_status"),
        ),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_mail_recipients_email_lowercase")),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["mail_campaigns.id"],
            name=op.f("fk_mail_recipients_campaign_id_mail_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_mail_recipients_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_recipients")),
        sa.UniqueConstraint("campaign_id", "email", name=op.f("uq_mail_recipients_campaign_id")),
        sa.UniqueConstraint("unsubscribe_token_hash", name=op.f("uq_mail_recipients_unsubscribe_token_hash")),
    )
    op.create_table(
        "mail_suppressions",
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("reason", sa.String(length=12), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "reason IN ('unsubscribed', 'bounced', 'complained')", name=op.f("ck_mail_suppressions_reason")
        ),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_mail_suppressions_email_lowercase")),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["mail_campaigns.id"],
            name=op.f("fk_mail_suppressions_campaign_id_mail_campaigns"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("email", name=op.f("pk_mail_suppressions")),
    )
    for table, indexes in INDEXES.items():
        for name, columns in indexes.items():
            op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    for table, indexes in INDEXES.items():
        for name in indexes:
            op.drop_index(name, table_name=table)
    op.drop_table("mail_suppressions")
    op.drop_table("mail_recipients")
    op.drop_table("mail_campaigns")
