"""Blog (IDEA §9): public listing and detail of published posts, superadmin CRUD.

A post is a draft while `published_at` is NULL; drafts are invisible (404) to everyone but superadmins.
The author is exposed only as PublicUser (nickname + avatar).
"""

from fastapi import UploadFile
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import BlogPost, User
from app.models.common import utcnow
from app.sanitize import clean_markdown
from app.schemas.content import BlogPostIn, BlogPostOut
from app.schemas.users import PublicUser
from app.services import media
from app.services.gallery import is_superadmin


def _not_found() -> AppError:
    return AppError(404, "No encontramos esa entrada.")


def outs(db: Session, posts: list[BlogPost]) -> list[BlogPostOut]:
    """BlogPostOut with its author as PublicUser; one query for all the authors of a page."""
    ids = {p.author_id for p in posts if p.author_id is not None}
    authors = {u.id: PublicUser.model_validate(u) for u in db.scalars(select(User).where(User.id.in_(ids)))}
    return [
        BlogPostOut.model_validate(p).model_copy(update={"author": authors.get(p.author_id)}) for p in posts
    ]


def list_stmt(drafts: bool) -> Select:
    """Published posts, or only the drafts (`drafts=True`, superadmins): never both mixed."""
    published = BlogPost.published_at.is_not(None)
    return select(BlogPost).where(~published if drafts else published)


def get_by_slug(db: Session, slug: str, user: User | None) -> BlogPostOut:
    post = db.scalar(select(BlogPost).where(BlogPost.slug == slug))
    if post is None or (post.published_at is None and not is_superadmin(user)):
        raise _not_found()
    return outs(db, [post])[0]


def get(db: Session, post_id: int) -> BlogPost:
    post = db.get(BlogPost, post_id)
    if post is None:
        raise _not_found()
    return post


def save(db: Session, post: BlogPost, data: BlogPostIn, author: User) -> BlogPostOut:
    post.title = data.title
    post.slug = data.slug
    post.body = clean_markdown(data.body)
    if post.author_id is None:
        post.author_id = author.id
    if data.published and post.published_at is None:
        post.published_at = utcnow()
    elif not data.published:
        post.published_at = None
    try:
        with db.begin_nested():  # duplicate slug (even concurrent) → 409, never 500
            db.add(post)
            db.flush()
    except IntegrityError as exc:
        raise AppError(409, "Ese identificador (slug) ya está en uso.", code="conflict") from exc
    return outs(db, [post])[0]


async def replace_cover(db: Session, post: BlogPost, file: UploadFile) -> BlogPostOut:
    """Store the new cover, commit, and only then delete the previous one (no orphans, no data loss)."""
    url = await media.save_upload(file, "cover")
    previous = post.cover_url
    try:
        post.cover_url = url
        db.commit()
    except Exception:
        db.rollback()
        media.delete_media(url)
        raise
    media.delete_media(previous)
    return outs(db, [post])[0]


def delete(db: Session, post: BlogPost) -> None:
    cover = post.cover_url
    db.delete(post)
    db.commit()
    media.delete_media(cover)
