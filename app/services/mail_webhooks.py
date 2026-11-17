"""Mailgun event webhook (UPS-077, spec 003 §History and delivery status, plan §STRIDE spoofing).

    verify(body)            # HMAC-SHA256(signing key, timestamp + token), 5 min window, token used once
    apply_event(db, event)  # delivered / bounced / complained; bounces and complaints suppress

The hash covers only `timestamp + token`, not the body, so the single-use token cache is what stops a captured
signature being replayed with another body. The cache is in memory: one process in v1 (ADR 0002). Logs carry
the event name, the campaign id and counts, never an address or the payload (spec 003 §Privacy).
"""

import hashlib
import hmac
import logging
import threading
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.mail import MailRecipient
from app.services.mail_suppressions import add_suppression
from app.services.mailer import normalize_email

log = logging.getLogger("app.mail.webhook")

MAX_AGE_SECONDS = 300
# A recipient status only moves forward: a late `delivered` never undoes a bounce or a complaint.
_RANK = {"pending": 0, "accepted": 1, "delivered": 2, "failed": 2, "bounced": 3, "complained": 4}

_seen: dict[str, float] = {}  # token -> when it stops mattering (its timestamp is out of the window)
_lock = threading.Lock()


def _now() -> float:
    return time.time()


def reset_seen_tokens() -> None:
    with _lock:
        _seen.clear()


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def verify(body: object) -> dict[str, Any] | None:
    """The `event-data` of a validly signed, fresh, first-use body; `None` for anything else."""
    key = get_settings().mailgun_webhook_signing_key
    if key is None or not isinstance(body, dict):
        return None
    signature, event = body.get("signature"), body.get("event-data")
    if not isinstance(signature, dict) or not isinstance(event, dict):
        return None
    timestamp, token, given = (_text(signature.get(name)) for name in ("timestamp", "token", "signature"))
    if not (timestamp and token and given):
        return None
    expected = hmac.new(
        key.get_secret_value().encode(), (timestamp + token).encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected.encode(), given.encode()):
        return None
    try:
        sent_at = int(timestamp)
    except ValueError:
        return None
    now = _now()
    if abs(now - sent_at) > MAX_AGE_SECONDS:
        return None
    with _lock:
        for old in [t for t, until in _seen.items() if until < now]:
            del _seen[old]
        if token in _seen:
            return None
        _seen[token] = sent_at + MAX_AGE_SECONDS  # only after the signature held: forgeries burn nothing
    return event


def _campaign_id(event: dict[str, Any]) -> int | None:
    variables = event.get("user-variables")
    raw = variables.get("campaign_id") if isinstance(variables, dict) else None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _outcome(event: dict[str, Any]) -> tuple[str, str | None] | None:
    """(recipient status or "", suppression reason) for an event we act on; `None` to ignore it."""
    name = event.get("event")
    if name == "delivered":
        return "delivered", None
    if name == "failed" and event.get("severity") == "permanent":
        return "bounced", "bounced"
    if name == "complained":
        return "complained", "complained"
    if name == "unsubscribed":
        return "", "unsubscribed"
    return None  # temporary failures (Mailgun retries), opened, clicked, unknown names


def apply_event(db: Session, event: dict[str, Any]) -> None:
    outcome = _outcome(event)
    email = normalize_email(_text(event.get("recipient")))
    if outcome is None or not email:
        log.info("mail webhook ignored event=%s", _text(event.get("event"))[:30])
        return
    status, reason = outcome
    campaign_id = _campaign_id(event)
    recipient = None
    if campaign_id is not None:
        recipient = db.scalar(
            select(MailRecipient).where(
                MailRecipient.campaign_id == campaign_id, MailRecipient.email == email
            )
        )
    if recipient is not None and status and _RANK.get(recipient.status, 0) < _RANK[status]:
        recipient.status = status
        recipient.error_code = _text(event.get("reason"))[:40] or None if status != "delivered" else None
    if reason is not None:
        # By address, even if the campaign is unknown or its rows were purged: it protects the person.
        add_suppression(db, email, reason, recipient.campaign_id if recipient is not None else None)
    db.flush()
    log.info(
        "mail webhook event=%s campaign=%s matched=%s", event.get("event"), campaign_id, recipient is not None
    )
