"""mail_audience_mix: combined audience `mix` and the delivery-detail index (UPS-105, spec 006)

Expand-only: the `mail_campaigns.audience_kind` CHECK gains `mix` (batch mode, so SQLite rebuilds the
table) and `mail_recipients` gets an index on (campaign_id, status). Downgrade restores the narrower
CHECK; on a DB that already holds `mix` campaigns, roll back the web instead (plan 006 §Data).

Revision ID: 0012
Revises: 0011
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

CHECK = "ck_mail_campaigns_audience_kind"
INDEX = "ix_mail_recipients_campaign_id_status"
OLD_KINDS = "audience_kind IN ('all', 'academy', 'role', 'individual')"
NEW_KINDS = "audience_kind IN ('all', 'academy', 'role', 'individual', 'mix')"


def _swap_check(condition: str) -> None:
    with op.batch_alter_table("mail_campaigns") as batch_op:
        batch_op.drop_constraint(op.f(CHECK), type_="check")
        batch_op.create_check_constraint(op.f(CHECK), condition)


def upgrade() -> None:
    _swap_check(NEW_KINDS)
    op.create_index(op.f(INDEX), "mail_recipients", ["campaign_id", "status"])


def downgrade() -> None:
    op.drop_index(op.f(INDEX), table_name="mail_recipients")
    _swap_check(OLD_KINDS)
