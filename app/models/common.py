"""Shared column helpers and enums for the models."""

import enum
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend.

    SQLite drops the offset and returns naive values; the API then serialized them without `Z`
    and browsers read them as local time (Mexico = UTC-6 → "dentro de 5 horas"). This type
    stores UTC and always returns aware UTC datetimes.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value

    def process_result_value(self, value: datetime | None, _dialect) -> datetime | None:
        if value is not None:
            value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return value


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
    """Portable enum: VARCHAR(20), no native PG enum. The CHECK comes from `enum_check` (one per column).

    `create_constraint=True` is not used: with the naming convention it emitted the same named CHECK
    several times, which Postgres rejects (DuplicateObject) and SQLite silently accepts.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        length=20,
        validate_strings=True,
        values_callable=lambda members: [m.value for m in members],
        create_constraint=False,
    )


def enum_check(column: str, enum_cls: type[enum.StrEnum]) -> CheckConstraint:
    """CHECK (column IN (...)) named `ck_<table>_<column>` by the naming convention."""
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=column)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, server_default=func.now(), nullable=False
    )
