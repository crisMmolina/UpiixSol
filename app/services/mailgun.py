"""Mailgun transport (UPS-073, spec 003): `POST {base}/v3/{domain}/messages` with recipient variables.

    transport = MailgunTransport()                       # env settings, httpx with a 10 s timeout
    result = transport.send_batch(message, recipients)   # split into ordered calls of ≤ 1 000 recipients

Unsubscribe header (docs/spikes/mailgun.md §3, verified 2026-11-18): every send batches (≤ 1 000 per call) and
`h:List-Unsubscribe` carries `%recipient.unsubscribe_url%`, which Mailgun resolves per recipient to the API
one-click URL (RFC 8058).

Errors never carry the key or an address: a failed call marks its recipients with a short code
(`auth`, `rate_limited`, `provider_error`, `rejected`, `timeout`, `network`, `bad_response`) and the log
has status, code and counts only.
"""

import json
import logging
import re

import httpx

from app.config import Settings, get_settings
from app.services.mailer import MAX_BATCH, BatchResult, MailMessage, MailRecipientVars

logger = logging.getLogger("mail.mailgun")

TIMEOUT_SECONDS = 10.0
ONE_CLICK = "List-Unsubscribe=One-Click"  # RFC 8058 §3.1
NAME_UNSAFE = re.compile(r'[\x00-\x1f\x7f"<>\\]')  # controls, quotes, angle brackets: break the From header
UNSAFE = re.compile(r'[\s,;<>"]')  # never valid in an address or URL; would split `to` or break a header


def unsubscribe_headers() -> dict[str, str]:
    """The only place the unsubscribe headers are built: the per-recipient variable, resolved by Mailgun."""
    return {"h:List-Unsubscribe": "<%recipient.unsubscribe_url%>", "h:List-Unsubscribe-Post": ONE_CLICK}


def sender_from(mail_from: str, from_name: str | None) -> str:
    """`"<from_name> · UpiixSol" <address>`: the display name carries the sender, the address never changes.

    The name is cut to one line without quotes, angle brackets or control characters; a name that ends up
    empty leaves `MAIL_FROM` as configured.
    """
    name = " ".join(NAME_UNSAFE.sub(" ", from_name or "").split())[:60].strip()
    if not name:
        return mail_from
    address = mail_from.rpartition("<")[2].rstrip(">").strip()
    return f'"{name} · UpiixSol" <{address}>'


def error_code(status: int) -> str:
    if status in (401, 403):
        return "auth"  # configuration: wrong key or region, never retried
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "provider_error"
    return "rejected"


class MailgunTransport:
    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self._settings = settings or get_settings()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def __repr__(self) -> str:
        return f"MailgunTransport(domain={self._settings.mailgun_domain!r})"

    @property
    def _url(self) -> str:
        return f"{self._settings.mailgun_api_base.rstrip('/')}/v3/{self._settings.mailgun_domain}/messages"

    def send_batch(self, message: MailMessage, recipients: list[MailRecipientVars]) -> BatchResult:
        result = BatchResult()
        safe = []
        for recipient in recipients:
            if UNSAFE.search(recipient.email) or UNSAFE.search(recipient.unsubscribe_url):
                result.failed[recipient.recipient_id] = "rejected"  # could add recipients or inject a header
            else:
                safe.append(recipient)
        headers = unsubscribe_headers()
        for start in range(0, len(safe), MAX_BATCH):
            self._send_one(message, safe[start : start + MAX_BATCH], headers, result)
        return result

    def _form(self, message: MailMessage, chunk: list[MailRecipientVars], headers: dict) -> dict:
        settings = self._settings
        form: dict[str, str | list[str]] = {
            "from": sender_from(settings.mail_from, message.from_name),
            "to": [r.email for r in chunk],
            "recipient-variables": json.dumps(
                {r.email: {"name": r.name, "unsubscribe_url": r.unsubscribe_url} for r in chunk}
            ),
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
            "o:tracking": "no",
            **headers,
        }
        reply_to = message.reply_to or settings.mail_reply_to  # the campaign's wins
        if reply_to:
            form["h:Reply-To"] = reply_to
        if message.campaign_id is not None:
            form["v:campaign_id"] = str(message.campaign_id)
        if settings.mailgun_test_mode:
            form["o:testmode"] = "yes"
        return form

    def _send_one(
        self, message: MailMessage, chunk: list[MailRecipientVars], headers: dict, result: BatchResult
    ) -> None:
        code = self._post(self._form(message, chunk, headers), message.attachments)
        if code.startswith("id:"):
            message_id = code[3:]
            result.accepted.update({r.recipient_id: message_id for r in chunk})
            logger.info("mail.mailgun accepted campaign_id=%s recipients=%d", message.campaign_id, len(chunk))
        else:
            result.failed.update({r.recipient_id: code for r in chunk})
            logger.warning(
                "mail.mailgun failed campaign_id=%s code=%s recipients=%d",
                message.campaign_id,
                code,
                len(chunk),
            )

    def _post(self, form: dict, attachments: list[tuple[str, str, bytes]] | None = None) -> str:
        """`id:<message id>` on success, else a short error code. Never raises, never echoes the reply."""
        key = self._settings.mailgun_api_key
        if key is None or not self._settings.mailgun_api_base.startswith("https://"):
            return "auth"  # no key, or a base URL that would send it in clear text
        try:
            files = [("attachment", (name, data, kind)) for name, kind, data in attachments or []]
            response = self._client.post(
                self._url, data=form, files=files or None, auth=("api", key.get_secret_value())
            )
        except httpx.InvalidURL:
            return "network"
        except httpx.TimeoutException:
            return "timeout"
        except httpx.HTTPError:
            return "network"
        if response.status_code != 200:
            return error_code(response.status_code)
        try:
            message_id = response.json()["id"].strip().strip("<>")
        except (ValueError, KeyError, TypeError, AttributeError):
            return "bad_response"
        return "id:" + message_id if message_id else "bad_response"
