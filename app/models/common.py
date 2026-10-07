"""Shared column helpers and enums for the models."""

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(enum.StrEnum):
    superadmin = "superadmin"
    academy_admin = "academy_admin"
    member = "member"


class ResourceType(enum.StrEnum):
    document = "document"
    link = "link"
    video = "video"
    other = "other"


class ProjectStatus(enum.StrEnum):
    draft = "draft"
    published = "published"


class ChannelType(enum.StrEnum):
    feed = "feed"
    general = "general"
    academy = "academy"


def str_enum(enum_cls: type[enum.StrEnum]) -> Enum:
    """Portable enum: VARCHAR + CHECK constraint (no native PG enum to migrate)."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=20,
        validate_strings=True,
        values_callable=lambda members: [m.value for m in members],
        create_constraint=True,
        name=f"{enum_cls.__name__.lower()}",
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
