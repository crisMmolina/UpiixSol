"""Usage analytics: an append-only stream of activity events (UPS-037).

Rows are only ever inserted (`app/services/analytics.py`); nothing updates or deletes them in the app.
Indexes serve time-range queries per event name, per user and per club (`docs/analytics.md`).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import UTCDateTime, utcnow

# BIGINT in Postgres (the stream outgrows 2^31); SQLite only autoincrements an INTEGER primary key.
EventId = BigInteger().with_variant(Integer, "sqlite")
SOURCES = ("server", "web")


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (
        CheckConstraint(f"source IN ({', '.join(repr(s) for s in SOURCES)})", name="source"),
        Index("ix_activity_events_name_occurred_at", "name", "occurred_at"),
        Index("ix_activity_events_user_id_occurred_at", "user_id", "occurred_at"),
        Index("ix_activity_events_academy_id_occurred_at", "academy_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(EventId, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    academy_id: Mapped[int | None] = mapped_column(ForeignKey("academies.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(40), nullable=False)  # allowlisted, e.g. "lesson.completed"
    subject_type: Mapped[str | None] = mapped_column(String(20))  # "lesson", "post", "resource"...
    subject_id: Mapped[int | None] = mapped_column(Integer)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)  # small, no PII
    session_id: Mapped[str | None] = mapped_column(String(64))  # random id from the browser tab
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # "server" | "web"
