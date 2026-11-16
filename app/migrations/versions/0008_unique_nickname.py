"""users: unique nicknames, case-insensitive, and no reserved ones (UPS-070)

Data first, then the index. Existing duplicates keep the name for the oldest user (lowest id) and the rest get
a number ("ana", "ana2", "ana3"…); "admin" and "upiixia" (compared as in app/services/nicknames.py) are renamed
the same way. Then a unique index on lower(nickname) keeps it that way. The renames are not undone on
downgrade: only the index goes.

Revision ID: 0008
Revises: 0007
"""

import unicodedata

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

RESERVED = {"admin", "upiixia"}  # frozen copy of app.services.nicknames.RESERVED_NICKNAMES
MAX_LENGTH = 40
INDEX = "uq_users_nickname_lower"


def _reserved(value: str) -> bool:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "".join(c for c in ascii_text.lower() if c.isalnum()) in RESERVED


def _rename_taken_and_reserved() -> None:
    conn = op.get_bind()
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("nickname", sa.String))
    rows = conn.execute(sa.select(users.c.id, users.c.nickname).order_by(users.c.id)).all()
    keepers: set[str] = set()
    to_rename: list[tuple[int, str]] = []
    for user_id, nickname in rows:
        if _reserved(nickname) or nickname.lower() in keepers:
            to_rename.append((user_id, nickname))
        else:
            keepers.add(nickname.lower())
    for user_id, nickname in to_rename:
        stem = nickname[: MAX_LENGTH - 4]
        number = 2
        while f"{stem}{number}".lower() in keepers or _reserved(f"{stem}{number}"):
            number += 1
        new_name = f"{stem}{number}"
        keepers.add(new_name.lower())
        conn.execute(users.update().where(users.c.id == user_id).values(nickname=new_name))


def upgrade() -> None:
    if not op.get_context().as_sql:  # offline SQL has no rows to read: dedupe by hand before running it
        _rename_taken_and_reserved()
    op.create_index(INDEX, "users", [sa.text("lower(nickname)")], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX, table_name="users")
