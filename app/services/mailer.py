"""Mail transport contract (UPS-072, spec 003): what campaigns send through, and the helpers around it.

    transport = get_mail_transport()                     # FastAPI dependency: tests override it with a Fake
    result = transport.send_batch(message, recipients)   # ≤ 1 000 recipients per call; one To each
    normalize_email(" Ana@IPN.mx ")                      # "ana@ipn.mx": key of recipients and suppressions
    token, token_hash = new_unsubscribe_token()          # token goes in the email; only the hash is stored

`ConsoleTransport` (dev/test default) logs the subject length and recipient count, never addresses or text.
`MailgunTransport` lives in app/services/mailgun.py (UPS-073). Delivery state comes back by webhook (UPS-077);
`BatchResult` only says which recipients the provider accepted (with its message id) and which it refused.
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger("mail.campaign")

MAX_BATCH = 1000  # Mailgun's limit of recipients per call


@dataclass(frozen=True)
class MailMessage:
    """The rendered email, the same for every recipient of a batch (per-person parts are variables)."""

    subject: str = field(repr=False)
    html: str = field(repr=False)
    text: str = field(repr=False)
    campaign_id: int | None = None  # sent to the provider as a tag so webhooks find the campaign
    # UPS-085: (filename, content type, bytes) parts, e.g. evento.ics; Reply-To of the campaign (wins over
    # MAIL_REPLY_TO); display name of the sender (the From address always stays MAIL_FROM's).
    attachments: list[tuple[str, str, bytes]] = field(default_factory=list, repr=False)
    reply_to: str | None = field(default=None, repr=False)
    from_name: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class MailRecipientVars:
    """One recipient of a batch: `%recipient.name%` and `%recipient.unsubscribe_url%` come from here."""

    recipient_id: int  # mail_recipients.id
    email: str = field(repr=False)  # repr=False: a stray "%r" in a log must not leak the address or the token
    name: str = field(repr=False)
    unsubscribe_url: str = field(repr=False)


@dataclass
class BatchResult:
    """`accepted`: recipient id → provider message id. `failed`: recipient id → short error code (no PII)."""

    accepted: dict[int, str] = field(default_factory=dict)
    failed: dict[int, str] = field(default_factory=dict)


class MailTransport(Protocol):
    def send_batch(self, message: MailMessage, recipients: list[MailRecipientVars]) -> BatchResult: ...


class ConsoleTransport:
    """Dev/test default: nothing leaves the process; the log has counts only (spec 003, privacy)."""

    def send_batch(self, message: MailMessage, recipients: list[MailRecipientVars]) -> BatchResult:
        logger.info(
            "mail.console campaign_id=%s subject_length=%d recipients=%d",
            message.campaign_id,
            len(message.subject),
            len(recipients),
        )
        return BatchResult(accepted={r.recipient_id: f"console-{r.recipient_id}" for r in recipients})


def get_mail_transport() -> MailTransport:
    if get_settings().mail_backend == "mailgun":
        try:
            from app.services.mailgun import MailgunTransport
        except ModuleNotFoundError as error:
            raise RuntimeError("MAIL_BACKEND=mailgun needs app/services/mailgun.py (UPS-073)") from error
        return MailgunTransport()
    return ConsoleTransport()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def new_unsubscribe_token() -> tuple[str, str]:
    """A random token (32 bytes) and its SHA-256 hex. Only the hash is stored; the token goes in the link."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()
