"""Post reactions: idempotent PUT/DELETE per user and kind, plus the caller's own reactions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.pagination import MAX_LIMIT
from app.ratelimit import limiter
from app.security import current_user
from app.services import reactions as service

router = APIRouter(prefix="/api", tags=["reactions"])
REACTION_LIMIT = "60/minute"  # toggling is cheap, but not free
MAX_ID = 2**31 - 1  # ids beyond the DB integer range are a 422, never an overflow 500
PostId = Annotated[int, Path(ge=1, le=MAX_ID)]


def _per_user(request: Request) -> str:
    return f"user:{getattr(request.state, 'user_id', None)}"


@router.put("/posts/{post_id}/reactions/{kind}", response_model=service.ReactionsOut)
@limiter.limit(REACTION_LIMIT, key_func=_per_user)
def add_reaction(
    request: Request,
    post_id: PostId,
    kind: service.ReactionKind,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> service.ReactionsOut:
    result = service.add(db, post_id, user, kind)
    db.commit()
    return result


@router.delete("/posts/{post_id}/reactions/{kind}", response_model=service.ReactionsOut)
@limiter.limit(REACTION_LIMIT, key_func=_per_user)
def remove_reaction(
    request: Request,
    post_id: PostId,
    kind: service.ReactionKind,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> service.ReactionsOut:
    result = service.remove(db, post_id, user, kind)
    db.commit()
    return result


@router.get("/reactions/mine", response_model=dict[str, list[str]])
def my_reactions(
    post_ids: Annotated[str, Query(min_length=1, max_length=400, description="Comma-separated, at most 50")],
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[str]]:
    try:
        ids = {int(part) for part in post_ids.split(",") if part.strip()}
    except ValueError as exc:
        raise AppError(422, "Lista de publicaciones inválida.", code="invalid_post_ids") from exc
    if not ids or len(ids) > MAX_LIMIT or not all(1 <= i <= MAX_ID for i in ids):
        raise AppError(422, f"Pide entre 1 y {MAX_LIMIT} publicaciones.", code="invalid_post_ids")
    return service.mine(db, sorted(ids), user)
