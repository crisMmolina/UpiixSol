"""Post reactions (IDEA §8.1 P2): one per user and kind, idempotent PUT/DELETE.

Counts per post already come in the post listings (`services.academies.posts_out`); this module adds
the writes and which kinds the current user chose, so the UI can show the toggled state.
"""

from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Post, Reaction, User
from app.services import community


class ReactionKind(StrEnum):
    like = "like"
    love = "love"
    fire = "fire"
    idea = "idea"
    clap = "clap"


class ReactionsOut(BaseModel):
    post_id: int
    reactions: dict[str, int]
    mine: list[str]


def _visible_post(db: Session, post_id: int) -> Post:
    """Same visibility as the community: not hidden, and its channel is visible (active academy)."""
    post = db.get(Post, post_id)
    if post is None or post.is_hidden:
        raise AppError(404, "No encontramos esa publicación.")
    community.get_channel(db, post.channel_id)
    return post


def _summary(db: Session, post_id: int, user: User) -> ReactionsOut:
    counts = db.execute(
        select(Reaction.kind, func.count()).where(Reaction.post_id == post_id).group_by(Reaction.kind)
    ).all()
    mine = db.scalars(
        select(Reaction.kind)
        .where(Reaction.post_id == post_id, Reaction.user_id == user.id)
        .order_by(Reaction.kind)
    ).all()
    return ReactionsOut(post_id=post_id, reactions=dict(counts), mine=list(mine))


def add(db: Session, post_id: int, user: User, kind: ReactionKind) -> ReactionsOut:
    post = _visible_post(db, post_id)
    try:
        # Insert-or-nothing: a repeated (or concurrent) identical PUT hits the primary key and is a no-op.
        with db.begin_nested():
            db.add(Reaction(post_id=post.id, user_id=user.id, kind=kind.value))
            db.flush()
    except IntegrityError:
        pass
    return _summary(db, post.id, user)


def remove(db: Session, post_id: int, user: User, kind: ReactionKind) -> ReactionsOut:
    post = _visible_post(db, post_id)
    db.execute(
        delete(Reaction).where(
            Reaction.post_id == post.id, Reaction.user_id == user.id, Reaction.kind == kind.value
        )
    )
    return _summary(db, post.id, user)


def mine(db: Session, post_ids: list[int], user: User) -> dict[str, list[str]]:
    """Kinds the user chose, for posts the caller already has (no visibility filter needed: only ids)."""
    result: dict[str, list[str]] = {}
    rows = db.execute(
        select(Reaction.post_id, Reaction.kind)
        .where(Reaction.user_id == user.id, Reaction.post_id.in_(post_ids))
        .order_by(Reaction.post_id, Reaction.kind)
    )
    for post_id, kind in rows:
        result.setdefault(str(post_id), []).append(kind)
    return result
