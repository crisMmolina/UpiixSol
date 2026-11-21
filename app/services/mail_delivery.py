"""Delivery detail per sent email (UPS-106, spec 006 §Delivery detail).

One row per frozen recipient: who it went to, its last status and, for bounces and failures, the reason in
Spanish. Same scope as the history detail (`mail_campaigns._load`): a club admin only sees their club's
campaigns. Purged campaigns (UPS-081) simply have no rows left.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import User
from app.models.mail import MailRecipient
from app.pagination import paginate
from app.schemas.common import Page
from app.services.mail_campaigns import _load

DeliveryStatus = Literal["pending", "accepted", "delivered", "failed", "bounced", "complained"]

# Statuses whose error_code explains what went wrong; any other status shows no reason.
_WITH_REASON = {"bounced", "failed"}

REASONS = {
    # Mailgun `failed` (permanent) reasons, stored by the webhook (UPS-077)
    "bounce": "El buzón no existe o no acepta correo",
    "suppress-bounce": "Dirección suprimida por rebotes previos",
    "suppress-unsubscribe": "Dirección suprimida: la persona se dio de baja",
    "suppress-complaint": "Dirección suprimida: marcó un correo anterior como spam",
    "old": "No se pudo entregar después de varios intentos",
    "generic": "El servidor lo rechazó",
    "espblock": "El proveedor del destinatario bloqueó el correo",
    "hardfail": "El servidor lo rechazó de forma definitiva",
    # send errors (app/services/mailgun.py, mail_campaigns._deliver)
    "auth": "El servicio de envío rechazó la configuración",
    "rate_limited": "El servicio de envío limitó los envíos",
    "provider_error": "El servicio de envío falló",
    "rejected": "El servicio de envío rechazó el mensaje",
    "network": "Error de red al enviarlo",
    "timeout": "El servicio de envío no respondió a tiempo",
    "bad_response": "El servicio de envío dio una respuesta inesperada",
}


def reason_text(status: str, code: str | None) -> str | None:
    """Spanish reason for a bounced or failed row; an unknown code is shown as is."""
    if status not in _WITH_REASON or not code:
        return None
    return REASONS.get(code, f"Motivo: {code}")


class DeliveryRow(BaseModel):
    user_id: int | None
    name: str
    email: str
    status: str
    reason_code: str | None = None
    reason: str | None = None
    updated_at: datetime


def _row(recipient: MailRecipient) -> DeliveryRow:
    code = recipient.error_code if recipient.status in _WITH_REASON else None
    return DeliveryRow(
        user_id=recipient.user_id,
        name=recipient.name,
        email=recipient.email,
        status=recipient.status,
        reason_code=code,
        reason=reason_text(recipient.status, code),
        updated_at=recipient.updated_at,
    )


def list_recipients(
    db: Session,
    user: User,
    campaign_id: int,
    *,
    status: str | None,
    q: str | None,
    cursor: str | None,
    limit: int,
) -> Page[DeliveryRow]:
    campaign = _load(db, user, campaign_id)
    stmt = select(MailRecipient).where(MailRecipient.campaign_id == campaign.id)
    if status:
        stmt = stmt.where(MailRecipient.status == status)
    term = (q or "").strip().lower()
    if term:
        stmt = stmt.where(
            or_(
                func.lower(MailRecipient.name).contains(term, autoescape=True),
                MailRecipient.email.contains(term, autoescape=True),  # stored lowercase
            )
        )
    # By id: stable across webhook updates and the same order on SQLite and PostgreSQL.
    return paginate(
        db, stmt, [MailRecipient.id], cursor=cursor, limit=limit, descending=False, transform=_row
    )
