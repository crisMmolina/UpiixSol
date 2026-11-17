"""Email channel tables (UPS-072, spec 003): campaigns, their frozen recipients and the suppression list.

Statuses are plain strings with CHECK constraints (no native enum, so PostgreSQL and SQLite behave the same).
Addresses live only here: normalized lowercase (`app/services/mailer.normalize_email`), never in logs.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import UTCDateTime, utcnow

AUDIENCE_KINDS = ("all", "academy", "role", "individual")
CAMPAIGN_STATUSES = ("draft", "sending", "sent", "partial", "failed")
RECIPIENT_STATUSES = ("pending", "accepted", "delivered", "failed", "bounced", "complained")
SUPPRESSION_REASONS = ("unsubscribed", "bounced", "complained")


def _one_of(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class MailCampaign(Base):
    __tablename__ = "mail_campaigns"
    __table_args__ = (
        CheckConstraint(_one_of("audience_kind", AUDIENCE_KINDS), name="audience_kind"),
        CheckConstraint(_one_of("status", CAMPAIGN_STATUSES), name="status"),
        Index("ix_mail_campaigns_academy_id_created_at", "academy_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    # Club scope of the sender/audience; taken from the DB row, never from the request body.
    academy_id: Mapped[int | None] = mapped_column(ForeignKey("academies.id", ondelete="SET NULL"))
    audience_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    # academy_id, role, user_ids: never email addresses.
    audience_params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="draft", nullable=False)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Counts per recipient status, kept when the recipient rows are purged (UPS-081).
    counts_snapshot: Mapped[dict[str, int] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class MailRecipient(Base):
    """One frozen row per address of a campaign. Only the SHA-256 of the unsubscribe token is stored."""

    __tablename__ = "mail_recipients"
    __table_args__ = (
        UniqueConstraint("campaign_id", "email"),
        CheckConstraint(_one_of("status", RECIPIENT_STATUSES), name="status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("mail_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    error_code: Mapped[str | None] = mapped_column(String(40))  # short, no PII
    unsubscribe_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, index=True, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False
    )


class MailSuppression(Base):
    """Addresses that must never get club email again; covers campus users and outside addresses."""

    __tablename__ = "mail_suppressions"
    __table_args__ = (CheckConstraint(_one_of("reason", SUPPRESSION_REASONS), name="reason"),)

    email: Mapped[str] = mapped_column(String(254), primary_key=True)  # normalized lowercase
    reason: Mapped[str] = mapped_column(String(12), nullable=False)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("mail_campaigns.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, server_default=func.now(), nullable=False
    )
