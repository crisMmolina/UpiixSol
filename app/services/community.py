"""Community (flow step 4): Feed / General / one channel per academy, posts, comments, moderation.

Only nickname + avatar of authors are exposed (PublicUser). Hidden posts/comments disappear for
everyone; who hid them and when is recorded (repudiation, plan 001 STRIDE).
"""

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import Academy, Channel, ChannelType, Comment, Post, Role, User
from app.models.common import utcnow
from app.pagination import paginate
from app.sanitize import clean_markdown
from app.schemas.common import Page
from app.schemas.community import ChannelOut, CommentOut, PostOut
from app.schemas.users import PublicUser
from app.services.academies import posts_out


def _not_found() -> AppError:
    return AppError(404, "No encontramos ese canal o publicación.")


def _visible_channels_stmt() -> Select:
    return (
        select(Channel)
        .outerjoin(Academy, Academy.id == Channel.academy_id)
        .where(or_(Channel.academy_id.is_(None), Academy.is_active.is_(True)))
    )


def list_channels(db: Session) -> list[ChannelOut]:
    order = {ChannelType.feed: 0, ChannelType.general: 1, ChannelType.academy: 2}
    rows = db.execute(
        _visible_channels_stmt().add_columns(Academy.position).order_by(Academy.position, Channel.id)
    ).all()
    channels = sorted(rows, key=lambda row: (order[row[0].type], row[1] or 0, row[0].id))
    return [ChannelOut.model_validate(row[0]) for row in channels]


def get_channel(db: Session, channel_id: int) -> Channel:
    channel = db.scalar(_visible_channels_stmt().where(Channel.id == channel_id))
    if channel is None:
        raise _not_found()
    return channel


def _posts_stmt(db: Session, channel: Channel) -> Select:
    stmt = select(Post).options(selectinload(Post.author)).where(Post.is_hidden.is_(False))
    if channel.type == ChannelType.feed:
        postable = (
            _visible_channels_stmt().where(Channel.type != ChannelType.feed).with_only_columns(Channel.id)
        )
        return stmt.where(Post.channel_id.in_(postable))
    return stmt.where(Post.channel_id == channel.id)


def list_posts(db: Session, channel: Channel, cursor: str | None, limit: int) -> Page[PostOut]:
    page = paginate(db, _posts_stmt(db, channel), [Post.created_at, Post.id], cursor=cursor, limit=limit)
    return Page[PostOut](items=posts_out(db, page.items), next_cursor=page.next_cursor)


def ensure_postable(channel: Channel) -> None:
    if channel.type == ChannelType.feed:
        raise AppError(422, "El Feed reúne los canales: publica en General o en el canal de una academia.")


def create_post(
    db: Session, channel: Channel, author: User, body: str, link_url: str | None, image_url: str | None
) -> PostOut:
    ensure_postable(channel)
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
        body=comment.body,
        created_at=comment.created_at,
    )


def list_comments(db: Session, post_id: int, cursor: str | None, limit: int) -> Page[CommentOut]:
    post, _channel = _visible_post(db, post_id)
    stmt = (
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.post_id == post.id, Comment.is_hidden.is_(False))
    )
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


def hide_post(db: Session, post_id: int, moderator: User) -> dict:
    post, channel = _visible_post(db, post_id)
    if not _can_moderate(moderator, channel):
        raise AppError(403)
    post.is_hidden, post.hidden_by_id, post.hidden_at = True, moderator.id, utcnow()
    db.flush()
    return {"id": post.id, "is_hidden": True}


def hide_comment(db: Session, comment_id: int, moderator: User) -> dict:
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
    if not _can_moderate(moderator, channel):
        raise AppError(403)
    comment.is_hidden, comment.hidden_by_id, comment.hidden_at = True, moderator.id, utcnow()
    db.flush()
    return {"id": comment.id, "is_hidden": True}
