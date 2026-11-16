"""Nickname rules (UPS-070): unique ignoring case, and "admin" / "upiixia" are reserved.

A nickname is reserved when, lower-cased, without accents and keeping only letters and digits, it equals a
reserved name: "Admin", "a.d.m.i.n" and "ÚPIIXIA" all collide. Seeded accounts such as "admin.ia" are not
reserved (their key is "adminia"). The unique index on lower(nickname) (migration 0008) backs the check up."""

import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import User

RESERVED_NICKNAMES = frozenset({"admin", "upiixia"})
MAX_NICKNAME = 40
_SUFFIX_ROOM = 4  # digits kept free so "name" + number fits the 40-character column


def nickname_key(value: str) -> str:
    """The identity used for the reserved list: accents removed, letters and digits only, lower case."""
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "".join(c for c in ascii_text.lower() if c.isalnum())


def is_reserved(value: str) -> bool:
    return nickname_key(value) in RESERVED_NICKNAMES


def ensure_available(db: Session, nickname: str, *, user_id: int | None = None) -> None:
    """422 for a reserved nickname, 409 when another user (not `user_id`) already has it."""
    if is_reserved(nickname):
        raise AppError(422, "Ese nombre de usuario está reservado. Elige otro.", code="nickname_reserved")
    query = select(User.id).where(func.lower(User.nickname) == nickname.lower())
    if user_id is not None:
        query = query.where(User.id != user_id)
    if db.scalar(query.limit(1)) is not None:
        raise AppError(409, "Ese nombre de usuario ya está en uso. Elige otro.", code="nickname_taken")


def unique_nickname(db: Session, base: str) -> str:
    """`base` when free, else with a number: "aud", "aud2", "aud3"… Reserved names count as taken."""
    stem = base[: MAX_NICKNAME - _SUFFIX_ROOM]
    like_stem = func.lower(User.nickname).startswith(stem.lower(), autoescape=True)
    taken = {name.lower() for name in db.scalars(select(User.nickname).where(like_stem))}
    if base.lower() not in taken and not is_reserved(base):
        return base
    number = 2
    while f"{stem}{number}".lower() in taken or is_reserved(f"{stem}{number}"):
        number += 1
    return f"{stem}{number}"
