"""Community (flow step 4): Feed / General / one channel per academy, posts, comments, moderation.

Only nickname + avatar of authors are exposed (PublicUser). Hidden posts/comments stay in place as
"Mensaje oculto": the API sends the flag and nothing of the content (redacted here, server-side), and
nobody can comment or react on them. Who hid them and when is recorded (repudiation, plan 001 STRIDE).
The image of a hidden post leaves `/media` (UPS-035): only moderators of its channel can still read it.

Who may post (UPS-035, decision): General is open to every signed-in user (spec: "conversación abierta para
todo el campus"); a club channel takes posts from that club's members (enrolled), its admins and
superadmins. Every active channel stays readable by any signed-in user (IDEA §2.1: all active academies
are visible), and comments/reactions stay open to them. Authors can delete their own visible posts and
comments; moderators hide (the hidden record stays as audit trail and cannot be deleted by its author).
"""

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import Academy, Channel, ChannelType, Comment, Enrollment, MediaObject, Post, Role, User
from app.models.common import utcnow
from app.pagination import paginate
from app.sanitize import clean_markdown
from app.schemas.common import Page
from app.schemas.community import ChannelOut, CommentOut, PostOut
from app.schemas.users import PublicUser
from app.services import media
from app.services.academies import posts_out


class ChannelAccessOut(ChannelOut):
    """A channel plus whether the caller may post in it (the composer is shown only then)."""

    can_post: bool = False


def _not_found() -> AppError:
    return AppError(404, "No encontramos ese canal o publicación.")


def _visible_channels_stmt() -> Select:
    return (
        select(Channel)
        .outerjoin(Academy, Academy.id == Channel.academy_id)
        .where(or_(Channel.academy_id.is_(None), Academy.is_active.is_(True)))
    )


def _enrolled(db: Session, user: User) -> set[int]:
    return set(db.scalars(select(Enrollment.academy_id).where(Enrollment.user_id == user.id)))


def _may_post(user: User, channel: Channel, enrolled: set[int]) -> bool:
    if channel.type == ChannelType.feed:
        return False
    if channel.academy_id is None or user.role == Role.superadmin:
        return True
    is_club_admin = user.role == Role.academy_admin and user.academy_id == channel.academy_id
    return is_club_admin or channel.academy_id in enrolled


def list_channels(db: Session, user: User) -> list[ChannelAccessOut]:
    order = {ChannelType.feed: 0, ChannelType.general: 1, ChannelType.academy: 2}
    rows = db.execute(
        _visible_channels_stmt().add_columns(Academy.position).order_by(Academy.position, Channel.id)
    ).all()
    channels = sorted(rows, key=lambda row: (order[row[0].type], row[1] or 0, row[0].id))
    enrolled = _enrolled(db, user)
    return [
        ChannelAccessOut.model_validate(row[0]).model_copy(
            update={"can_post": _may_post(user, row[0], enrolled)}
        )
        for row in channels
    ]


def get_channel(db: Session, channel_id: int) -> Channel:
    channel = db.scalar(_visible_channels_stmt().where(Channel.id == channel_id))
    if channel is None:
        raise _not_found()
    return channel


def _posts_stmt(db: Session, channel: Channel) -> Select:
    stmt = select(Post).options(selectinload(Post.author))
    if channel.type == ChannelType.feed:
        postable = (
            _visible_channels_stmt().where(Channel.type != ChannelType.feed).with_only_columns(Channel.id)
        )
        return stmt.where(Post.channel_id.in_(postable))
    return stmt.where(Post.channel_id == channel.id)


def _redact_post(out: PostOut) -> PostOut:
    return out.model_copy(
        update={
            "body": "",
            "image_url": None,
            "link_url": None,
            "reactions": {},
            "comment_count": 0,
            "is_hidden": True,
        }
    )


def list_posts(db: Session, channel: Channel, cursor: str | None, limit: int) -> Page[PostOut]:
    page = paginate(db, _posts_stmt(db, channel), [Post.created_at, Post.id], cursor=cursor, limit=limit)
    hidden = {p.id for p in page.items if p.is_hidden}
    items = [_redact_post(out) if out.id in hidden else out for out in posts_out(db, page.items)]
    return Page[PostOut](items=items, next_cursor=page.next_cursor)


def ensure_postable(db: Session, channel: Channel, author: User) -> None:
    if channel.type == ChannelType.feed:
        raise AppError(422, "El Feed reúne los canales: publica en General o en el canal de un club.")
    if not _may_post(author, channel, _enrolled(db, author)):
        raise AppError(403, f"Únete a {channel.name} para publicar en su canal.", code="not_a_member")


def create_post(
    db: Session, channel: Channel, author: User, body: str, link_url: str | None, image_url: str | None
) -> PostOut:
    ensure_postable(db, channel, author)
    post = Post(
        channel_id=channel.id,
        author_id=author.id,
        body=clean_markdown(body),
        link_url=link_url,
        image_url=image_url,
    )
    db.add(post)
    db.flush()
    db.refresh(post, attribute_names=["author"])
    return posts_out(db, [post])[0]


def _visible_post(db: Session, post_id: int) -> tuple[Post, Channel]:
    row = db.execute(
        select(Post, Channel)
        .join(Channel, Channel.id == Post.channel_id)
        .where(Post.id == post_id, Post.is_hidden.is_(False))
    ).first()
    if row is None:
        raise _not_found()
    get_channel(db, row[1].id)  # channel of an inactive academy → 404
    return row[0], row[1]


def _comment_out(comment: Comment) -> CommentOut:
    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        author=PublicUser.model_validate(comment.author),
        body="" if comment.is_hidden else comment.body,  # redacted server-side
        created_at=comment.created_at,
        is_hidden=comment.is_hidden,
    )


def list_comments(db: Session, post_id: int, cursor: str | None, limit: int) -> Page[CommentOut]:
    post, _channel = _visible_post(db, post_id)
    stmt = select(Comment).options(selectinload(Comment.author)).where(Comment.post_id == post.id)
    return paginate(
        db,
        stmt,
        [Comment.created_at, Comment.id],
        cursor=cursor,
        limit=limit,
        descending=False,
        transform=_comment_out,
    )


def create_comment(db: Session, post_id: int, author: User, body: str) -> CommentOut:
    post, _channel = _visible_post(db, post_id)
    comment = Comment(post_id=post.id, author_id=author.id, body=clean_markdown(body))
    db.add(comment)
    db.flush()
    db.refresh(comment, attribute_names=["author"])
    return _comment_out(comment)


def _can_moderate(user: User, channel: Channel) -> bool:
    if user.role == Role.superadmin:
        return True
    return (
        user.role == Role.academy_admin
        and channel.academy_id is not None
        and channel.academy_id == user.academy_id
    )


def hide_post(db: Session, post_id: int, moderator: User) -> tuple[dict, str | None]:
    """Hides the post; returns the response and the image URL the caller removes after committing."""
    post, channel = _visible_post(db, post_id)
    if not _can_moderate(moderator, channel):
        raise AppError(403)
    post.is_hidden, post.hidden_by_id, post.hidden_at = True, moderator.id, utcnow()
    media.withdraw_media(db, post.image_url)  # moderator-only copy, out of /media
    db.flush()
    return {"id": post.id, "is_hidden": True}, post.image_url


def hidden_image(db: Session, post_id: int, moderator: User) -> MediaObject:
    """The image of a hidden post, for moderators of its channel only."""
    row = db.execute(
        select(Post, Channel).join(Channel, Channel.id == Post.channel_id).where(Post.id == post_id)
    ).first()
    if row is None or not row[0].is_hidden:
        raise _not_found()
    post, channel = row
    get_channel(db, channel.id)
    if not _can_moderate(moderator, channel):
        raise AppError(403)
    stored = media.load_withdrawn(db, post.image_url)
    if stored is None:
        raise _not_found()
    return stored


def delete_post(db: Session, post_id: int, author: User) -> str | None:
    """Authors delete their own visible post (comments and reactions go with it, ON DELETE CASCADE).

    Returns the image URL the caller removes after committing."""
    post, _channel = _visible_post(db, post_id)
    if post.author_id != author.id:
        raise AppError(403, "Solo quien publicó puede borrar esta publicación.")
    image_url = post.image_url
    db.execute(delete(Post).where(Post.id == post.id))
    db.flush()
    return image_url


def _visible_comment(db: Session, comment_id: int) -> tuple[Comment, Channel]:
    row = db.execute(
        select(Comment, Channel)
        .join(Post, Post.id == Comment.post_id)
        .join(Channel, Channel.id == Post.channel_id)
        .where(Comment.id == comment_id, Comment.is_hidden.is_(False), Post.is_hidden.is_(False))
    ).first()
    if row is None:
        raise _not_found()
    comment, channel = row
    get_channel(db, channel.id)  # channel of an inactive academy → 404
    return comment, channel


def delete_comment(db: Session, comment_id: int, user: User) -> None:
    """The author, a superadmin, or the admin of the channel's academy (same rule as hiding)."""
    comment, channel = _visible_comment(db, comment_id)
    if comment.author_id != user.id and not _can_moderate(user, channel):
        raise AppError(403, "Solo quien comentó o un admin del club puede borrar este comentario.")
    db.execute(delete(Comment).where(Comment.id == comment.id))
    db.flush()


def hide_comment(db: Session, comment_id: int, moderator: User) -> dict:
    comment, channel = _visible_comment(db, comment_id)
    if not _can_moderate(moderator, channel):
        raise AppError(403)
    comment.is_hidden, comment.hidden_by_id, comment.hidden_at = True, moderator.id, utcnow()
    db.flush()
    return {"id": comment.id, "is_hidden": True}
