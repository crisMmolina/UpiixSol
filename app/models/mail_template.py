"""Saved email templates (UPS-100, spec 005): a subject, preheader and validated blocks, per scope.

Scope `site` = UpiixSol (academy_id NULL), `academy` = one club. Never stores audience, sender or Reply-To.
The name is unique per scope and club ignoring case; NULL academy ids collapse to 0 in the index so two
UpiixSol templates cannot share a name either.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import UTCDateTime, utcnow

TEMPLATE_SCOPES = ("site", "academy")


class MailTemplate(Base):
    __tablename__ = "mail_templates"
    __table_args__ = (
        CheckConstraint("scope IN ('site', 'academy')", name="scope"),
        CheckConstraint(
            "(scope = 'site' AND academy_id IS NULL) OR (scope = 'academy' AND academy_id IS NOT NULL)",
            name="scope_academy",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(7), nullable=False)
    academy_id: Mapped[int | None] = mapped_column(ForeignKey("academies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(String(140))
    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    preheader: Mapped[str | None] = mapped_column(String(140))
    # Validated blocks (services/mail_blocks.py), same JSON as mail_campaigns.content.
    content: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False
    )


Index(
    "uq_mail_templates_scope_academy_name",
    MailTemplate.scope,
    func.coalesce(MailTemplate.academy_id, 0),
    func.lower(MailTemplate.name),
    unique=True,
)
