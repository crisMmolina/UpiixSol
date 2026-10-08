"""reactions: one per user and post (UPS-025)

Keeps one existing reaction per (post, user) (the alphabetically first kind) and moves the primary key
from (post_id, user_id, kind) to (post_id, user_id).

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM reactions WHERE (post_id, user_id, kind) NOT IN "
            "(SELECT post_id, user_id, MIN(kind) FROM reactions GROUP BY post_id, user_id)"
        )
    )
    with op.batch_alter_table("reactions", schema=None) as batch_op:
        batch_op.drop_constraint("pk_reactions", type_="primary")
        batch_op.create_primary_key("pk_reactions", ["post_id", "user_id"])


def downgrade() -> None:
    with op.batch_alter_table("reactions", schema=None) as batch_op:
        batch_op.drop_constraint("pk_reactions", type_="primary")
        batch_op.create_primary_key("pk_reactions", ["post_id", "user_id", "kind"])
