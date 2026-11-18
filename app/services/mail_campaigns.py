"""Mail campaigns (UPS-075, spec 003 §Composing and sending, §History; plan §Design, §Contracts).

    send_test(db, sender, mail, transport)                # only to the sender; no campaign, no quota
    create_campaign(db, sender, data)                     # draft + frozen recipients (pending)
    confirm(db, sender, campaign_id) -> (campaign, start) # draft → sending once (conditional UPDATE)
    resume(db, sender, campaign_id) -> (campaign, start)  # a stuck `sending`: only its pending rows
    send_pending(campaign_id, transport)                  # BackgroundTasks job: batches, commit per batch
    list_campaigns / get_campaign                         # history: superadmin all, academy_admin own club

The kill switch (`MAIL_ENABLED`), the hourly limit (5 started campaigns per sender) and the monthly quota
(counted in `mail_recipients`) are checked before anything is sent. Logs carry ids and counts only.

Unsubscribe tokens: only their hash is stored, so the hash written at creation is a placeholder and every
batch writes a fresh token's hash right before the call that carries the token in its URL.
"""

import logging
import unicodedata
from datetime import datetime, timedelta
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.errors import AppError
from app.models import Academy, Role, User
from app.models.analytics import ActivityEvent
from app.models.common import utcnow
from app.models.mail import MailCampaign, MailRecipient
from app.pagination import paginate
from app.schemas.common import InModel, Page
from app.schemas.users import PublicUser
from app.services import mail_template
from app.services.mail_audience import (
    AcademyAudience,
    Audience,
    IndividualAudience,
    RoleAudience,
    mail_status,
    resolve_audience,
)
from app.services.mailer import (
    MAX_BATCH,
    BatchResult,
    MailMessage,
    MailRecipientVars,
    MailTransport,
    new_unsubscribe_token,
)
from app.services.site import get_site

logger = logging.getLogger("mail.campaign")

BATCH_SIZE = MAX_BATCH  # recipients per committed batch (tests lower it)
HOURLY_LIMIT = 5
STALE_AFTER = timedelta(minutes=15)  # a `sending` campaign this old is stuck and may be resumed
RETRYABLE = {"rate_limited", "provider_error", "network"}  # contract #464: timeout/bad_response may be queued
# Background jobs open their own session (the request's one is closed by then). Tests swap it.
session_factory = SessionLocal


# ── Contracts ───────────────────────────────────────────────


class MailIn(InModel):
    subject: Annotated[str, Field(min_length=1, max_length=150)]
    body: Annotated[str, Field(min_length=1, max_length=20_000)]

    @field_validator("subject")
    @classmethod
    def _one_line(cls, value: str) -> str:
        # CR/LF (and other line or control characters) could inject headers: one line only.
        if any(unicodedata.category(char) in ("Cc", "Zl", "Zp") for char in value):
            raise ValueError("El asunto debe ser una sola línea.")
        return value


class CampaignIn(MailIn):
    audience: Audience


class TestSentOut(BaseModel):
    sent: bool


class CampaignOut(BaseModel):
    id: int
    subject: str
    audience: dict[str, Any]
    sender: PublicUser | None
    status: str
    recipient_count: int
    counts_by_status: dict[str, int]
    created_at: datetime
    sent_at: datetime | None = None
    finished_at: datetime | None = None


# ── Guards ──────────────────────────────────────────────────


def ensure_enabled() -> None:
    if not get_settings().mail_enabled:
        raise AppError(503, "El correo está desactivado", code="mail_disabled")


def _visible(user: User, campaign: MailCampaign) -> bool:
    if user.role == Role.superadmin:
        return True
    return user.academy_id is not None and campaign.academy_id == user.academy_id


def _load(db: Session, user: User, campaign_id: int, *, to_send: bool = False) -> MailCampaign:
    """The campaign if the user may see it (history) or send it (its sender or a superadmin), else 403."""
    campaign = db.get(MailCampaign, campaign_id)
    if campaign is None:
        raise AppError(404)
    allowed = (
        user.role == Role.superadmin or campaign.sender_id == user.id if to_send else _visible(user, campaign)
    )
    if not allowed:
        raise AppError(403)
    return campaign


def _pending(db: Session, campaign_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(MailRecipient)
        .where(MailRecipient.campaign_id == campaign_id, MailRecipient.status == "pending")
    )


MESES = (
    *("enero", "febrero", "marzo", "abril", "mayo", "junio"),
    *("julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
)


def _check_quota(db: Session, campaign_id: int) -> None:
    quota = mail_status(db)
    remaining = quota.remaining
    needed = _pending(db, campaign_id)
    if needed > remaining:
        raise AppError(
            422,
            f"Este periodo quedan {remaining} envíos y esta campaña necesita {needed}; "
            f"la cuota se renueva el {quota.period_end.day} de {MESES[quota.period_end.month - 1]}.",
            code="quota_exceeded",
            details={"remaining": remaining},
        )


def _check_hourly(db: Session, sender: User, campaign_id: int) -> None:
    started = db.scalar(
        select(func.count())
        .select_from(MailCampaign)
        .where(
            MailCampaign.sender_id == sender.id,
            MailCampaign.id != campaign_id,
            MailCampaign.sent_at >= utcnow() - timedelta(hours=1),
        )
    )
    if started >= HOURLY_LIMIT:
        raise AppError(
            429, f"Puedes iniciar como máximo {HOURLY_LIMIT} campañas por hora.", code="rate_limited"
        )


# ── Test send and drafts ────────────────────────────────────


def _unsubscribe_url(token: str) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/api/mail/unsubscribe?t={token}"


def send_test(db: Session, sender: User, mail: MailIn, transport: MailTransport) -> TestSentOut:
    """The rendered email, only to the sender's own address; not a campaign and not counted."""
    ensure_enabled()
    site = get_site(db)
    reason = "Recibes esta prueba porque la pediste tú."
    html, text = mail_template.render(mail.subject, mail.body, reason, site=site)
    token, _hash = new_unsubscribe_token()  # never stored: an unknown token unsubscribes nobody
    recipient = MailRecipientVars(0, sender.email, sender.full_name, _unsubscribe_url(token))
    result = transport.send_batch(MailMessage(mail.subject, html, text), [recipient])
    logger.info("mail.campaign test sender_id=%s accepted=%d", sender.id, len(result.accepted))
    if not result.accepted:
        raise AppError(502, "No se pudo enviar la prueba. Intenta de nuevo más tarde.", code="mail_failed")
    return TestSentOut(sent=True)


def _audience_params(audience: Audience) -> dict[str, Any]:
    """What the history shows of the audience: ids and counts, never addresses."""
    if isinstance(audience, AcademyAudience):
        return {"academy_id": audience.academy_id}
    if isinstance(audience, RoleAudience):
        return {"role": audience.role.value}
    if isinstance(audience, IndividualAudience):
        return {"user_ids": list(audience.user_ids), "outside": len(audience.emails)}
    return {}


def create_campaign(db: Session, sender: User, data: CampaignIn) -> CampaignOut:
    recipients = resolve_audience(db, sender, data.audience)  # 403 outside the sender's scope
    if not recipients:
        raise AppError(422, "La audiencia no tiene destinatarios.", code="empty_audience")
    if sender.role == Role.superadmin:
        club = data.audience.academy_id if isinstance(data.audience, AcademyAudience) else None
    else:
        club = sender.academy_id  # from the DB row, never the request body
    campaign = MailCampaign(
        sender_id=sender.id,
        academy_id=club,
        audience_kind=data.audience.kind,
        audience_params=_audience_params(data.audience),
        subject=data.subject,
        body=data.body,
        status="draft",
        recipient_count=len(recipients),
    )
    db.add(campaign)
    db.flush()
    db.add_all(
        MailRecipient(
            campaign_id=campaign.id,
            user_id=r.user_id,
            email=r.email,
            name=r.name[:120],
            unsubscribe_token_hash=new_unsubscribe_token()[1],  # placeholder; replaced when it is sent
        )
        for r in recipients
    )
    db.commit()
    logger.info(
        "mail.campaign draft campaign_id=%s sender_id=%s audience=%s recipients=%d",
        campaign.id,
        sender.id,
        campaign.audience_kind,
        campaign.recipient_count,
    )
    return campaign_out(db, campaign)


# ── Confirm, resume ─────────────────────────────────────────


def confirm(db: Session, sender: User, campaign_id: int) -> tuple[MailCampaign, bool]:
    """draft → sending exactly once. `start` is True only for the request that won the UPDATE."""
    campaign = _load(db, sender, campaign_id, to_send=True)
    ensure_enabled()
    if campaign.status != "draft":
        return campaign, False  # a repeated confirm: same campaign, nothing new is sent
    _check_hourly(db, sender, campaign.id)
    _check_quota(db, campaign.id)
    won = db.execute(
        update(MailCampaign)
        .where(MailCampaign.id == campaign.id, MailCampaign.status == "draft")
        .values(status="sending", sent_at=utcnow())
        .execution_options(synchronize_session=False)
    ).rowcount
    db.commit()
    db.refresh(campaign)
    return campaign, won == 1


def resume(db: Session, sender: User, campaign_id: int) -> tuple[MailCampaign, bool]:
    """A campaign stuck in `sending` (no progress for STALE_AFTER) sends only its `pending` rows."""
    campaign = _load(db, sender, campaign_id, to_send=True)
    ensure_enabled()
    if campaign.status != "sending" or _pending(db, campaign.id) == 0:
        if campaign.status == "sending":
            _finish(db, campaign)  # nothing left: close it
        return campaign, False
    _check_quota(db, campaign.id)
    won = db.execute(
        update(MailCampaign)
        .where(
            MailCampaign.id == campaign.id,
            and_(MailCampaign.status == "sending", MailCampaign.sent_at < utcnow() - STALE_AFTER),
        )
        .values(sent_at=utcnow())  # the new start is the lease: a second resume now finds it fresh
        .execution_options(synchronize_session=False)
    ).rowcount
    db.commit()
    db.refresh(campaign)
    return campaign, won == 1


# ── Background sending ──────────────────────────────────────


def send_pending(campaign_id: int, transport: MailTransport) -> None:
    """BackgroundTasks job: every `pending` row, in batches, one commit per batch. Never raises."""
    with session_factory() as db:
        try:
            _send(db, campaign_id, transport)
        except Exception as error:  # the log names the error type only: messages may carry addresses
            db.rollback()
            logger.error("mail.campaign error campaign_id=%s error=%s", campaign_id, type(error).__name__)


def _reason(db: Session, campaign: MailCampaign, site_name: str) -> str:
    club = db.get(Academy, campaign.academy_id) if campaign.academy_id else None
    sender = db.get(User, campaign.sender_id) if campaign.sender_id else None
    return mail_template.footer_reason(
        campaign.audience_kind,
        site_name=site_name,
        club_name=club.name if club and campaign.audience_kind == "academy" else None,
        sender_nickname=sender.nickname if sender else None,
    )


def _deliver(transport: MailTransport, message: MailMessage, batch: list[MailRecipientVars]) -> BatchResult:
    """One call, plus one retry of the recipients that failed with a retryable code (contract #464)."""
    try:
        result = transport.send_batch(message, batch)
    except Exception:
        result = BatchResult(failed={r.recipient_id: "network" for r in batch})
    retry = [r for r in batch if result.failed.get(r.recipient_id) in RETRYABLE]
    if retry:
        try:
            second = transport.send_batch(message, retry)
        except Exception:
            second = BatchResult()
        for recipient_id, message_id in second.accepted.items():
            result.failed.pop(recipient_id, None)
            result.accepted[recipient_id] = message_id
        result.failed.update(second.failed)
    return result


def _send(db: Session, campaign_id: int, transport: MailTransport) -> None:
    campaign = db.get(MailCampaign, campaign_id)
    if campaign is None or campaign.status != "sending":
        return
    site = get_site(db)
    html, text = mail_template.render(
        campaign.subject, campaign.body, _reason(db, campaign, site.name), site=site
    )
    message = MailMessage(campaign.subject, html, text, campaign_id=campaign.id)
    number = 0
    while rows := db.scalars(
        select(MailRecipient)
        .where(MailRecipient.campaign_id == campaign.id, MailRecipient.status == "pending")
        .order_by(MailRecipient.id)
        .limit(BATCH_SIZE)
    ).all():
        number += 1
        batch = []
        for row in rows:
            token, token_hash = new_unsubscribe_token()
            row.unsubscribe_token_hash = token_hash
            batch.append(MailRecipientVars(row.id, row.email, row.name, _unsubscribe_url(token)))
        db.flush()
        result = _deliver(transport, message, batch)
        for row in rows:
            if row.id in result.accepted:
                row.status = "accepted"
                row.provider_message_id = result.accepted[row.id][:255]
            else:
                row.status = "failed"
                row.error_code = result.failed.get(row.id, "bad_response")[:40]
        db.commit()  # one commit per batch: a crash keeps what went out and leaves the rest `pending`
        logger.info(
            "mail.campaign batch campaign_id=%s batch=%d accepted=%d failed=%d",
            campaign.id,
            number,
            len(rows) - sum(row.status == "failed" for row in rows),
            sum(row.status == "failed" for row in rows),
        )
    _finish(db, campaign)


def _counts(db: Session, campaign_id: int) -> dict[str, int]:
    rows = db.execute(
        select(MailRecipient.status, func.count())
        .where(MailRecipient.campaign_id == campaign_id)
        .group_by(MailRecipient.status)
    ).all()
    return {status: count for status, count in sorted(rows)}


def _finish(db: Session, campaign: MailCampaign) -> None:
    counts = _counts(db, campaign.id)
    failed = counts.get("failed", 0)
    accepted = sum(counts.values()) - failed - counts.get("pending", 0)
    if failed == 0:
        campaign.status = "sent"
    else:
        campaign.status = "partial" if accepted else "failed"
    campaign.finished_at = utcnow()
    db.add(
        ActivityEvent(
            occurred_at=utcnow(),
            user_id=campaign.sender_id,
            academy_id=campaign.academy_id,
            name="mail.campaign_sent",
            properties={"count": accepted},  # the count only (plan §Observability)
            source="server",
        )
    )
    db.commit()
    logger.info(
        "mail.campaign finished campaign_id=%s status=%s accepted=%d failed=%d",
        campaign.id,
        campaign.status,
        accepted,
        failed,
    )


# ── History ─────────────────────────────────────────────────


def campaign_out(db: Session, campaign: MailCampaign) -> CampaignOut:
    sender = db.get(User, campaign.sender_id) if campaign.sender_id else None
    counts = _counts(db, campaign.id) or dict(campaign.counts_snapshot or {})
    return CampaignOut(
        id=campaign.id,
        subject=campaign.subject,
        audience={"kind": campaign.audience_kind, **campaign.audience_params},
        sender=PublicUser.model_validate(sender) if sender else None,
        status=campaign.status,
        recipient_count=campaign.recipient_count,
        counts_by_status=counts,
        created_at=campaign.created_at,
        sent_at=campaign.sent_at,
        finished_at=campaign.finished_at,
    )


def list_campaigns(db: Session, user: User, cursor: str | None, limit: int) -> Page[CampaignOut]:
    stmt = select(MailCampaign)
    if user.role != Role.superadmin:
        if user.academy_id is None:
            stmt = stmt.where(MailCampaign.id.is_(None))  # no club: nothing to see
        else:
            stmt = stmt.where(MailCampaign.academy_id == user.academy_id)
    return paginate(
        db,
        stmt,
        [MailCampaign.created_at, MailCampaign.id],
        cursor=cursor,
        limit=limit,
        transform=lambda campaign: campaign_out(db, campaign),
    )


def get_campaign(db: Session, user: User, campaign_id: int) -> CampaignOut:
    return campaign_out(db, _load(db, user, campaign_id))
