from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import ChannelType, CreatedAtMixin, str_enum


class Channel(CreatedAtMixin, Base):
    """`feed` stores no posts: it aggregates `general` + every academy channel."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[ChannelType] = mapped_column(str_enum(ChannelType), nullable=False)
    academy_id: Mapped[int | None] = mapped_column(
        ForeignKey("academies.id", ondelete="CASCADE"), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)


class Post(CreatedAtMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (Index("ix_posts_channel_id_created_at", "channel_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)  # sanitized
    image_url: Mapped[str | None] = mapped_column(String(500))
    link_url: Mapped[str | None] = mapped_column(String(500))
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author = relationship("User", foreign_keys=[author_id], lazy="raise")


# Feed ordering scans posts by recency across channels.
Index("ix_posts_created_at", Post.created_at)


class Comment(CreatedAtMixin, Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author = relationship("User", foreign_keys=[author_id], lazy="raise")


class Reaction(Base):
    __tablename__ = "reactions"

    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
