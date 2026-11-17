"""One-click unsubscribe and the "Recibir correos del club" preference (UPS-076, spec 003 §Opt-out).

The unsubscribe endpoint is public: the token is the only credential, so the tests build real tokens
(`new_unsubscribe_token`) and store their hash in a recipient row, like a sent campaign does.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.main import app
from app.models.mail import MailCampaign, MailRecipient, MailSuppression
from app.services.mailer import new_unsubscribe_token

UNSUBSCRIBE = "/api/mail/unsubscribe"
PREFERENCES = "/api/mail/preferences"
CAMPAIGNS = "/api/mail/campaigns"
MEMBER_EMAIL = "alumno.demo@upiixsol.dev"


@pytest.fixture
def anon(db: Session) -> Iterator[TestClient]:
    """A caller with no session and no `X-Requested-With`, like a mail client doing the one-click POST."""
    from app.db import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _mail_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "mail_enabled", True)


def _recipient(db: Session, email: str, *, user_id: int | None = None) -> str:
    """A campaign recipient with a real token; returns the token that goes in the email link."""
    campaign = MailCampaign(audience_kind="individual", subject="Aviso", body="Hola", status="sent")
    db.add(campaign)
    db.flush()
    token, token_hash = new_unsubscribe_token()
    db.add(
        MailRecipient(
            campaign_id=campaign.id,
            user_id=user_id,
            email=email,
            name="Ana",
            status="accepted",
            unsubscribe_token_hash=token_hash,
        )
    )
    db.flush()
    return token


def _suppressions(db: Session) -> dict[str, str]:
    return dict(db.execute(select(MailSuppression.email, MailSuppression.reason)).all())


def test_one_click_post_form_encoded_suppresses_without_session(anon: TestClient, db: Session) -> None:
    token = _recipient(db, "ana@ipn.mx")
    response = anon.post(
        UNSUBSCRIBE,
        params={"t": token},
        content=b"List-Unsubscribe=One-Click",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, response.text
    assert "X-Requested-With" not in anon.headers
    assert _suppressions(db) == {"ana@ipn.mx": "unsubscribed"}
    again = anon.post(UNSUBSCRIBE, params={"t": token}, data={"List-Unsubscribe": "One-Click"})
    assert again.status_code == 200
    assert again.json() == response.json()
    assert _suppressions(db) == {"ana@ipn.mx": "unsubscribed"}  # idempotent


def test_json_post_from_the_baja_page_suppresses(anon: TestClient, db: Session) -> None:
    token = _recipient(db, "beto@ipn.mx")
    response = anon.post(UNSUBSCRIBE, params={"t": token}, json={})
    assert response.status_code == 200, response.text
    assert _suppressions(db) == {"beto@ipn.mx": "unsubscribed"}


def test_unknown_token_answers_like_a_valid_one(anon: TestClient, db: Session) -> None:
    token = _recipient(db, "ana@ipn.mx")
    valid = anon.post(UNSUBSCRIBE, params={"t": token}, json={})
    unknown = anon.post(UNSUBSCRIBE, params={"t": "no-existe-" + token[:20]}, json={})
    missing = anon.post(UNSUBSCRIBE, json={})
    assert valid.status_code == unknown.status_code == missing.status_code == 200
    assert valid.json() == unknown.json() == missing.json()
    assert valid.headers["content-type"] == unknown.headers["content-type"]
    assert _suppressions(db) == {"ana@ipn.mx": "unsubscribed"}  # only the valid one changed anything


def test_token_is_read_from_the_query_not_the_path(anon: TestClient, db: Session) -> None:
    token = _recipient(db, "ana@ipn.mx")
    assert anon.post(f"{UNSUBSCRIBE}/{token}", json={}).status_code in (404, 405)
    body_only = anon.post(UNSUBSCRIBE, json={"t": token})
    assert body_only.status_code == 200  # same answer as any unknown token
    assert _suppressions(db) == {}


def test_get_redirects_to_baja_without_suppressing(anon: TestClient, db: Session) -> None:
    """Mail scanners prefetch GET links: the footer URL only hands over to /baja (POST suppresses)."""
    token = _recipient(db, "ana@ipn.mx")
    response = anon.get(UNSUBSCRIBE, params={"t": token}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/baja?t={token}"
    assert _suppressions(db) == {}
    bare = anon.get(UNSUBSCRIBE, follow_redirects=False)
    assert bare.status_code == 303
    assert bare.headers["location"] == "/baja"


def test_suppressed_address_is_excluded_from_every_campaign(
    as_superadmin: TestClient, anon: TestClient, db: Session
) -> None:
    token = _recipient(db, "baja@ipn.mx")
    assert anon.post(UNSUBSCRIBE, params={"t": token}, json={}).status_code == 200
    audience = {"kind": "individual", "emails": ["BAJA@ipn.mx", "sigue@ipn.mx"]}
    preview = as_superadmin.post("/api/mail/audience/preview", json=audience)
    assert preview.json() == {
        "count": 1,
        "excluded": {"inactive": 0, "suppressed": 1, "blocked_domain": 0},
    }
    for subject in ("Primero", "Segundo"):
        created = as_superadmin.post(
            CAMPAIGNS, json={"subject": subject, "body": "Hola", "audience": audience}
        )
        assert created.status_code == 201, created.text
        assert created.json()["recipient_count"] == 1
        rows = db.scalars(
            select(MailRecipient.email).where(MailRecipient.campaign_id == created.json()["id"])
        ).all()
        assert rows == ["sigue@ipn.mx"]


def test_preference_get_and_put_toggle_the_current_address(as_member: TestClient, db: Session) -> None:
    assert as_member.get(PREFERENCES).json() == {"receive_club_email": True}
    off = as_member.put(PREFERENCES, json={"receive_club_email": False})
    assert off.status_code == 200, off.text
    assert off.json() == {"receive_club_email": False}
    assert _suppressions(db) == {MEMBER_EMAIL: "unsubscribed"}
    assert as_member.get(PREFERENCES).json() == {"receive_club_email": False}
    again = as_member.put(PREFERENCES, json={"receive_club_email": False})
    assert again.status_code == 200
    assert db.scalar(select(func.count()).select_from(MailSuppression)) == 1
    on = as_member.put(PREFERENCES, json={"receive_club_email": True})
    assert on.json() == {"receive_club_email": True}
    assert _suppressions(db) == {}
    # A bounce or a complaint is not the user's choice: the toggle never lifts it.
    db.add(MailSuppression(email=MEMBER_EMAIL, reason="bounced"))
    db.flush()
    assert as_member.get(PREFERENCES).json() == {"receive_club_email": False}
    assert as_member.put(PREFERENCES, json={"receive_club_email": True}).json() == {
        "receive_club_email": False
    }
    assert _suppressions(db) == {MEMBER_EMAIL: "bounced"}


def test_preference_needs_a_session(anon: TestClient) -> None:
    assert anon.get(PREFERENCES).status_code == 401
    assert anon.put(PREFERENCES, json={"receive_club_email": False}).status_code == 401


def test_outside_address_can_unsubscribe(anon: TestClient, db: Session) -> None:
    token = _recipient(db, "fuera@gmail.com", user_id=None)
    assert anon.post(UNSUBSCRIBE, params={"t": token}, json={}).status_code == 200
    assert _suppressions(db) == {"fuera@gmail.com": "unsubscribed"}


def test_unsubscribe_is_rate_limited(anon: TestClient, db: Session) -> None:
    statuses = [anon.post(UNSUBSCRIBE, params={"t": f"adivina-{i}"}, json={}).status_code for i in range(12)]
    assert statuses[:10] == [200] * 10
    assert 429 in statuses[10:]
