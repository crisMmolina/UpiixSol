from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import CreatedAtMixin, ProjectStatus, ResourceType, enum_check, str_enum, utcnow


class Resource(CreatedAtMixin, Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint("url IS NOT NULL OR file_url IS NOT NULL", name="url_or_file"),
        enum_check("type", ResourceType),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academy_id: Mapped[int] = mapped_column(
        ForeignKey("academies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[ResourceType] = mapped_column(str_enum(ResourceType), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    file_url: Mapped[str | None] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))


class Event(CreatedAtMixin, Base):
    __tablename__ = "events"
    __table_args__ = (CheckConstraint("ends_at >= starts_at", name="ends_after_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academy_id: Mapped[int | None] = mapped_column(  # NULL = global event
        ForeignKey("academies.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    link: Mapped[str | None] = mapped_column(String(500))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)


class Project(CreatedAtMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (enum_check("status", ProjectStatus),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    summary: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    authors: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    academy_id: Mapped[int | None] = mapped_column(
        ForeignKey("academies.id", ondelete="SET NULL"), index=True
    )
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        str_enum(ProjectStatus), default=ProjectStatus.draft, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class BlogPost(CreatedAtMixin, Base):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)  # NULL = draft


class HomeContent(Base):
    """Singleton row (id = 1) edited by superadmins."""

    __tablename__ = "home_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hero_title: Mapped[str] = mapped_column(String(120), nullable=False)
    hero_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    highlighted_academy_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    featured_project_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False
    )
