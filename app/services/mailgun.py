"""Mailgun transport (UPS-073, spec 003): `POST {base}/v3/{domain}/messages` with recipient variables.

    transport = MailgunTransport()                       # env settings, httpx with a 10 s timeout
    result = transport.send_batch(message, recipients)   # split into ordered calls of ≤ 1 000 recipients

Unsubscribe headers (docs/spikes/mailgun.md §3): whether Mailgun substitutes `%recipient.*%` inside a custom
`h:List-Unsubscribe` is UNVERIFIED. Until it is, the plan's fallback applies: below `PER_RECIPIENT_BELOW`
recipients, one call per recipient with the real URL in the header; above it, batches without a custom
header (Mailgun's own unsubscribe, synced by webhook in UPS-077). Once verified, set
`UNSUBSCRIBE_HEADER_IN_BATCH = True`: every send batches and the header carries the recipient variable.

Errors never carry the key or an address: a failed call marks its recipients with a short code
(`auth`, `rate_limited`, `provider_error`, `rejected`, `timeout`, `network`, `bad_response`) and the log
has status, code and counts only.
"""

import json
import logging
from collections.abc import Iterator

import httpx

from app.config import Settings, get_settings
from app.services.mailer import MAX_BATCH, BatchResult, MailMessage, MailRecipientVars

logger = logging.getLogger("mail.mailgun")

TIMEOUT_SECONDS = 10.0
UNSUBSCRIBE_HEADER_IN_BATCH = False  # flip once spike §3 is verified with a test-mode call
PER_RECIPIENT_BELOW = 100  # plan §Design fallback: one call per recipient below this many recipients
ONE_CLICK = "List-Unsubscribe=One-Click"  # RFC 8058 §3.1


def unsubscribe_headers(recipient: MailRecipientVars | None) -> dict[str, str]:
    """The only place the unsubscribe headers are built.

    `recipient` given: a one-recipient call, so the real URL goes in the header. `None`: a batch call, which
    gets the recipient variable only when `UNSUBSCRIBE_HEADER_IN_BATCH` is on; otherwise no custom header.
    """
    if recipient is not None:
        url = recipient.unsubscribe_url
    elif UNSUBSCRIBE_HEADER_IN_BATCH:
        url = "%recipient.unsubscribe_url%"
    else:
        return {}
    return {"h:List-Unsubscribe": f"<{url}>", "h:List-Unsubscribe-Post": ONE_CLICK}


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
        for chunk, headers in self._calls(recipients):
            self._send_one(message, chunk, headers, result)
        return result

    def _calls(self, recipients: list[MailRecipientVars]) -> Iterator[tuple[list[MailRecipientVars], dict]]:
        if not UNSUBSCRIBE_HEADER_IN_BATCH and len(recipients) < PER_RECIPIENT_BELOW:
            for recipient in recipients:
                yield [recipient], unsubscribe_headers(recipient)
            return
        for start in range(0, len(recipients), MAX_BATCH):
            yield recipients[start : start + MAX_BATCH], unsubscribe_headers(None)

    def _form(self, message: MailMessage, chunk: list[MailRecipientVars], headers: dict) -> dict:
        settings = self._settings
        form: dict[str, str | list[str]] = {
            "from": settings.mail_from,
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
        if settings.mail_reply_to:
            form["h:Reply-To"] = settings.mail_reply_to
        if message.campaign_id is not None:
            form["v:campaign_id"] = str(message.campaign_id)
        if settings.mailgun_test_mode:
            form["o:testmode"] = "yes"
        return form

    def _send_one(
        self, message: MailMessage, chunk: list[MailRecipientVars], headers: dict, result: BatchResult
    ) -> None:
        code = self._post(self._form(message, chunk, headers))
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

    def _post(self, form: dict) -> str:
        """`id:<message id>` on success, else a short error code. Never raises, never echoes the reply."""
        key = self._settings.mailgun_api_key
        if key is None:
            return "auth"
        try:
            response = self._client.post(self._url, data=form, auth=("api", key.get_secret_value()))
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
