"""Community endpoints (flow step 4)."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.pagination import CursorParam, LimitParam
from app.ratelimit import POST_LIMIT, limiter
from app.schemas.common import Page
from app.schemas.community import ChannelOut, CommentIn, CommentOut, PostIn, PostOut
from app.security import current_user
from app.services import community as service
from app.services import media

router = APIRouter(prefix="/api", tags=["community"])


def _per_user(request: Request) -> str:
    return f"user:{getattr(request.state, 'user_id', None)}"


@router.get("/channels", response_model=list[ChannelOut])
def list_channels(_user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[ChannelOut]:
    return service.list_channels(db)


@router.get("/channels/{channel_id}/posts", response_model=Page[PostOut])
def list_posts(
    channel_id: int,
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    _user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Page[PostOut]:
    return service.list_posts(db, service.get_channel(db, channel_id), cursor, limit)


@router.post("/channels/{channel_id}/posts", response_model=PostOut, status_code=201)
@limiter.limit(POST_LIMIT, key_func=_per_user)
async def create_post(
    request: Request,
    channel_id: int,
    body: str = Form(...),
    link_url: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PostOut:
    try:
        data = PostIn(body=body, link_url=link_url or None)
    except ValidationError as exc:
        details = [{"loc": ["body", *e["loc"]], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        raise AppError(422, "Revisa los datos enviados.", code="validation_error", details=details) from exc
    channel = service.get_channel(db, channel_id)
    service.ensure_postable(channel)  # 404 / 422 before storing any file
    image_url = await media.save_upload(image, "post") if image is not None and image.filename else None
    try:
        post = service.create_post(db, channel, user, data.body, data.link_url, image_url)
        db.commit()
    except Exception:
        db.rollback()
        media.delete_media(image_url)
        raise
    return post


@router.get("/posts/{post_id}/comments", response_model=Page[CommentOut])
def list_comments(
    post_id: int,
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    _user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Page[CommentOut]:
    return service.list_comments(db, post_id, cursor, limit)


@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
@limiter.limit(POST_LIMIT, key_func=_per_user)
def create_comment(
    request: Request,
    post_id: int,
    data: CommentIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CommentOut:
    comment = service.create_comment(db, post_id, user, data.body)
    db.commit()
    return comment


@router.post("/posts/{post_id}/hide")
def hide_post(post_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    result = service.hide_post(db, post_id, user)
    db.commit()
    return result


@router.post("/comments/{comment_id}/hide")
def hide_comment(comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    result = service.hide_comment(db, comment_id, user)
    db.commit()
    return result
