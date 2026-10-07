from datetime import datetime
from typing import Annotated

from pydantic import StringConstraints

from app.models.common import ChannelType
from app.schemas.common import HttpUrl, InModel, OutModel
from app.schemas.users import PublicUser

PostBody = Annotated[str, StringConstraints(min_length=1, max_length=5_000)]
CommentBody = Annotated[str, StringConstraints(min_length=1, max_length=2_000)]


class ChannelOut(OutModel):
    id: int
    type: ChannelType
    academy_id: int | None
    name: str
    slug: str


class PostIn(InModel):
    """Multipart variant (with image) is built by the community router from these same fields."""

    body: PostBody
    link_url: HttpUrl | None = None


class PostOut(OutModel):
    id: int
    channel_id: int
    channel_slug: str | None = None
    author: PublicUser
    body: str
    image_url: str | None
    link_url: str | None
    created_at: datetime
    comment_count: int = 0
    reactions: dict[str, int] = {}
    is_hidden: bool = False


class CommentIn(InModel):
    body: CommentBody


class CommentOut(OutModel):
    id: int
    post_id: int
    author: PublicUser
    body: str
    created_at: datetime
