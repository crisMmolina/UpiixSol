"""Base classes and shared types for every API contract."""

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.sanitize import safe_url


class InModel(BaseModel):
    """Request bodies: unknown fields are rejected (blocks mass assignment, e.g. `role`)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OutModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(str.upper)]
HttpUrl = Annotated[str, StringConstraints(max_length=500), AfterValidator(safe_url)]
Title = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=60)]
MarkdownText = Annotated[str, StringConstraints(max_length=20_000)]


def _as_utc(value: datetime) -> datetime:
    """Naive input is read as UTC; aware input is converted, so comparisons never mix the two."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UTCDatetime = Annotated[datetime, AfterValidator(_as_utc)]


class Page[T](BaseModel):
    """Cursor page: at most 50 items; `next_cursor` is opaque (None = last page)."""

    items: list[T]
    next_cursor: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorOut(BaseModel):
    error: ErrorBody


class ReorderIn(InModel):
    """Full ordered list of sibling ids; positions are rewritten 0..n-1."""

    ids: list[int] = Field(min_length=1, max_length=200)


class MessageOut(BaseModel):
    message: str
