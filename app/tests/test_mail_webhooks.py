"""Mailgun webhook (UPS-077, spec 003 §History and delivery status, plan §STRIDE spoofing).

The endpoint is public: the HMAC signature is the only credential, so every test sends a really signed
payload (the UPS-071 fixtures, re-signed with a fake key and a controlled clock).
"""

import hashlib
import hmac
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.main import app
from app.models.mail import MailCampaign, MailRecipient, MailSuppression
from app.services import mail_webhooks

URL = "/api/mail/webhooks/mailgun"
KEY = "test-signing-key-not-a-real-secret"
NOW = 1770920772  # timestamp of the recorded fixtures
FIXTURES = Path(__file__).parent / "fixtures" / "mailgun"


@pytest.fixture
def anon(db: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    from app.db import get_db

    monkeypatch.setattr(get_settings(), "mailgun_webhook_signing_key", SecretStr(KEY))
    monkeypatch.setattr(mail_webhooks, "_now", lambda: float(NOW))
    mail_webhooks.reset_seen_tokens()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def _sign(key: str, timestamp: str, token: str) -> str:
    return hmac.new(key.encode(), (timestamp + token).encode(), hashlib.sha256).hexdigest()


def _event(
    name: str, *, token: str = "t" * 50, timestamp: int = NOW, key: str = KEY, **changes: Any
) -> dict[str, Any]:
    """A fixture event signed for real. `changes` override fields of `event-data`."""
    body = json.loads((FIXTURES / f"event_{name}.json").read_text())
    body["event-data"].update(changes)
    stamp = str(timestamp)
    body["signature"] = {"timestamp": stamp, "token": token, "signature": _sign(key, stamp, token)}
    return body


def _campaign(db: Session, *emails: str, status: str = "accepted") -> MailCampaign:
    campaign = MailCampaign(audience_kind="all", subject="Aviso", body="Hola", status="sent")
    db.add(campaign)
    db.flush()
    for index, email in enumerate(emails):
        db.add(
            MailRecipient(
                campaign_id=campaign.id,
                email=email,
                name="Ana",
                status=status,
                unsubscribe_token_hash=hashlib.sha256(f"{campaign.id}-{index}".encode()).hexdigest(),
            )
        )
    db.flush()
    return campaign


def _vars(campaign: MailCampaign) -> dict[str, str]:
    return {"campaign_id": str(campaign.id)}


def _status(db: Session, campaign: MailCampaign, email: str) -> str:
    db.expire_all()
    return db.scalar(
        select(MailRecipient.status).where(
            MailRecipient.campaign_id == campaign.id, MailRecipient.email == email
        )
    )


def _suppressions(db: Session) -> dict[str, str]:
    db.expire_all()
    return dict(db.execute(select(MailSuppression.email, MailSuppression.reason)).all())


def test_delivered_event_updates_the_recipient(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "recipient@example.com", "otra@example.com")
    response = anon.post(URL, json=_event("delivered", **{"user-variables": _vars(campaign)}))
    assert response.status_code == 200, response.text
    assert _status(db, campaign, "recipient@example.com") == "delivered"
    assert _status(db, campaign, "otra@example.com") == "accepted"
    assert _suppressions(db) == {}


def test_delivered_never_downgrades_a_bounce(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "recipient@example.com", status="bounced")
    response = anon.post(URL, json=_event("delivered", **{"user-variables": _vars(campaign)}))
    assert response.status_code == 200
    assert _status(db, campaign, "recipient@example.com") == "bounced"


def test_permanent_failure_marks_bounced_and_suppresses(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "badrecipient@example.com")
    response = anon.post(URL, json=_event("failed_permanent", **{"user-variables": _vars(campaign)}))
    assert response.status_code == 200, response.text
    assert _status(db, campaign, "badrecipient@example.com") == "bounced"
    assert _suppressions(db) == {"badrecipient@example.com": "bounced"}
    assert db.get(MailSuppression, "badrecipient@example.com").campaign_id == campaign.id


def test_temporary_failure_keeps_accepted(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "tempfailrecipient@example.com")
    response = anon.post(URL, json=_event("failed_temporary", **{"user-variables": _vars(campaign)}))
    assert response.status_code == 200, response.text
    assert _status(db, campaign, "tempfailrecipient@example.com") == "accepted"
    assert _suppressions(db) == {}


def test_complaint_suppresses(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "recipient@example.com", status="delivered")
    # The complained fixture carries no user variables: the address alone is enough to suppress.
    response = anon.post(URL, json=_event("complained"))
    assert response.status_code == 200, response.text
    assert _suppressions(db) == {"recipient@example.com": "complained"}
    # With the campaign variable the recipient row follows.
    again = anon.post(URL, json=_event("complained", token="u" * 50, **{"user-variables": _vars(campaign)}))
    assert again.status_code == 200
    assert _status(db, campaign, "recipient@example.com") == "complained"


def test_unsubscribed_event_suppresses_as_unsubscribed(anon: TestClient, db: Session) -> None:
    response = anon.post(URL, json=_event("unsubscribed"))
    assert response.status_code == 200, response.text
    assert _suppressions(db) == {"recipient@example.com": "unsubscribed"}


def test_webhook_rejects_bad_signature(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "badrecipient@example.com")
    changes = {"user-variables": _vars(campaign)}
    wrong_key = anon.post(URL, json=_event("failed_permanent", key="otra-llave", **changes))
    tampered = _event("failed_permanent", **changes)
    tampered["signature"]["signature"] = "0" * 64
    assert wrong_key.status_code == 403
    assert anon.post(URL, json=tampered).status_code == 403
    for broken in ({}, [], "x", {"event-data": {}}, {"signature": {}, "event-data": {}}):
        assert anon.post(URL, json=broken).status_code == 403
    assert anon.post(URL, content=b"not json").status_code == 403
    assert _status(db, campaign, "badrecipient@example.com") == "accepted"
    assert _suppressions(db) == {}


def test_webhook_rejects_when_no_signing_key_is_configured(
    anon: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "mailgun_webhook_signing_key", None)
    assert anon.post(URL, json=_event("unsubscribed")).status_code == 403
    assert _suppressions(db) == {}


def test_webhook_rejects_old_timestamp(
    anon: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mail_webhooks, "_now", lambda: float(NOW + 301))
    assert anon.post(URL, json=_event("unsubscribed")).status_code == 403
    monkeypatch.setattr(mail_webhooks, "_now", lambda: float(NOW - 301))  # from the future too
    assert anon.post(URL, json=_event("unsubscribed", token="u" * 50)).status_code == 403
    assert _suppressions(db) == {}
    monkeypatch.setattr(mail_webhooks, "_now", lambda: float(NOW + 300))  # the edge still passes
    assert anon.post(URL, json=_event("unsubscribed", token="v" * 50)).status_code == 200
    assert _suppressions(db) == {"recipient@example.com": "unsubscribed"}


def test_webhook_rejects_replayed_token(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "badrecipient@example.com")
    first = _event("failed_permanent", **{"user-variables": _vars(campaign)})
    assert anon.post(URL, json=first).status_code == 200
    # Same signature, other body: the hash covers only timestamp + token, so the token must be single use.
    replay = {**first, "event-data": {**first["event-data"], "recipient": "victima@example.com"}}
    assert anon.post(URL, json=replay).status_code == 403
    assert anon.post(URL, json=first).status_code == 403
    assert _suppressions(db) == {"badrecipient@example.com": "bounced"}


def test_bad_signature_does_not_burn_the_token(anon: TestClient, db: Session) -> None:
    forged = _event("unsubscribed", key="otra-llave")
    assert anon.post(URL, json=forged).status_code == 403
    genuine = _event("unsubscribed")  # same token, real signature
    assert anon.post(URL, json=genuine).status_code == 200


def test_unknown_campaign_or_recipient_is_ignored_with_200(anon: TestClient, db: Session) -> None:
    campaign = _campaign(db, "otra@example.com")
    cases = [
        {"user-variables": {"campaign_id": "999999"}},
        {"user-variables": {"campaign_id": "no-numero"}},
        {"user-variables": []},
        {"user-variables": _vars(campaign)},  # known campaign, recipient not in it
        {"event": "opened"},  # an event we do not handle
    ]
    for index, changes in enumerate(cases):
        response = anon.post(URL, json=_event("delivered", token=f"{index:050d}", **changes))
        assert response.status_code == 200, (changes, response.text)
    assert _status(db, campaign, "otra@example.com") == "accepted"
    assert _suppressions(db) == {}


def test_webhook_logs_have_no_addresses(
    anon: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    campaign = _campaign(db, "badrecipient@example.com")
    caplog.set_level(logging.DEBUG)
    anon.post(URL, json=_event("failed_permanent", **{"user-variables": _vars(campaign)}))
    anon.post(URL, json=_event("failed_permanent", token="x" * 50, key="otra-llave"))
    anon.post(URL, json=_event("complained", token="y" * 50))
    anon.post(URL, json=_event("failed_temporary", token="z" * 50))
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "mail webhook" in text  # it does log something, just not the person
    for secret in ("example.com", KEY, "x" * 50, "otra-llave"):
        assert secret not in text
