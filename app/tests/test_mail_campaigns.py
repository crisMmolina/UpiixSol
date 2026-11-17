"""Mail campaigns (UPS-075, spec 003 §Composing and sending, §History): test send, draft → confirm →
background batches, quota, hourly limit, kill switch, history.

A Fake transport replaces Mailgun through `app.dependency_overrides[get_mail_transport]`; the background
job opens its own session, bound here to the test engine. Recipients are outside addresses (`@ipn.mx`),
since the seeded accounts are on the blocked `upiixsol.dev` domain.
"""

import logging
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.main import app
from app.models import Academy, Role, User
from app.models.analytics import ActivityEvent
from app.models.common import utcnow
from app.models.mail import MailCampaign, MailRecipient
from app.services import mail_campaigns
from app.services.mailer import BatchResult, MailMessage, MailRecipientVars, get_mail_transport
from app.tests.conftest import make_user

CAMPAIGNS = "/api/mail/campaigns"


class FakeTransport:
    """Records every call; the calls whose index is in `fail_calls` fail with `code`."""

    def __init__(self) -> None:
        self.calls: list[tuple[MailMessage, list[MailRecipientVars]]] = []
        self.fail_calls: set[int] = set()
        self.code = "rejected"

    def send_batch(self, message: MailMessage, recipients: list[MailRecipientVars]) -> BatchResult:
        index = len(self.calls)
        self.calls.append((message, list(recipients)))
        if index in self.fail_calls:
            return BatchResult(failed={r.recipient_id: self.code for r in recipients})
        return BatchResult(accepted={r.recipient_id: f"fake-{r.recipient_id}" for r in recipients})

    @property
    def sent_to(self) -> list[str]:
        return [r.email for _, recipients in self.calls for r in recipients]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, engine: Engine) -> Iterator[FakeTransport]:
    monkeypatch.setattr(get_settings(), "mail_enabled", True)
    monkeypatch.setattr(mail_campaigns, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))
    transport = FakeTransport()
    app.dependency_overrides[get_mail_transport] = lambda: transport
    yield transport
    app.dependency_overrides.pop(get_mail_transport, None)


def _emails(n: int, prefix: str = "persona") -> list[str]:
    return [f"{prefix}{i}@ipn.mx" for i in range(n)]


def _create(client: TestClient, emails: list[str], subject: str = "Aviso semanal") -> dict:
    response = client.post(
        CAMPAIGNS,
        json={
            "subject": subject,
            "body": "Hola a todos",
            "audience": {"kind": "individual", "emails": emails},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _send(client: TestClient, campaign_id: int, action: str = "send") -> dict:
    response = client.post(f"{CAMPAIGNS}/{campaign_id}/{action}")
    assert response.status_code == 202, response.text
    return response.json()


def _get(client: TestClient, campaign_id: int) -> dict:
    response = client.get(f"{CAMPAIGNS}/{campaign_id}")
    assert response.status_code == 200, response.text
    return response.json()


def test_test_send_goes_only_to_the_sender(
    as_superadmin: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    response = as_superadmin.post("/api/mail/test", json={"subject": "Prueba", "body": "Hola"})
    assert response.status_code == 202, response.text
    me = as_superadmin.get("/api/auth/me").json()
    assert fake.sent_to == [me["email"]]
    assert fake.calls[0][0].subject == "Prueba"
    assert db.scalar(select(func.count()).select_from(MailCampaign)) == 0
    assert db.scalar(select(func.count()).select_from(MailRecipient)) == 0


def test_create_campaign_freezes_recipients_as_draft(
    as_superadmin: TestClient, db: Session, fake: FakeTransport
) -> None:
    body = _create(as_superadmin, _emails(3))
    assert body["status"] == "draft"
    assert body["recipient_count"] == 3
    assert body["counts_by_status"] == {"pending": 3}
    assert body["audience"] == {"kind": "individual", "user_ids": [], "outside": 3}  # never the addresses
    rows = db.scalars(select(MailRecipient).where(MailRecipient.campaign_id == body["id"])).all()
    assert sorted(r.email for r in rows) == sorted(_emails(3))
    assert {r.status for r in rows} == {"pending"}
    assert all(len(r.unsubscribe_token_hash) == 64 for r in rows)
    assert fake.calls == []


def test_confirm_twice_sends_once(as_superadmin: TestClient, db: Session, fake: FakeTransport) -> None:
    campaign = _create(as_superadmin, _emails(3))
    first = _send(as_superadmin, campaign["id"])
    second = _send(as_superadmin, campaign["id"])
    assert first["id"] == second["id"] == campaign["id"]
    assert sorted(fake.sent_to) == sorted(_emails(3))  # every address once, across both confirms
    assert _get(as_superadmin, campaign["id"])["status"] == "sent"


def test_batches_are_sent_in_the_background(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mail_campaigns, "BATCH_SIZE", 2)
    campaign = _create(as_superadmin, _emails(5))
    answer = _send(as_superadmin, campaign["id"])
    assert answer["status"] == "sending"  # the answer leaves before the batches run
    assert [len(recipients) for _, recipients in fake.calls] == [2, 2, 1]
    assert all(message.campaign_id == campaign["id"] for message, _ in fake.calls)
    urls = [r.unsubscribe_url for _, recipients in fake.calls for r in recipients]
    assert len(set(urls)) == 5
    assert all(
        url.startswith(get_settings().public_base_url.rstrip("/") + "/api/mail/unsubscribe?t=")
        for url in urls
    )
    done = _get(as_superadmin, campaign["id"])
    assert done["status"] == "sent"
    assert done["counts_by_status"] == {"accepted": 5}
    assert done["sent_at"] is not None


def test_failed_batch_marks_partial_and_keeps_others(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mail_campaigns, "BATCH_SIZE", 2)
    fake.fail_calls = {1}
    campaign = _create(as_superadmin, _emails(5))
    _send(as_superadmin, campaign["id"])
    assert len(fake.calls) == 3  # a rejected batch is not retried; the next one still goes
    done = _get(as_superadmin, campaign["id"])
    assert done["status"] == "partial"
    assert done["counts_by_status"] == {"accepted": 3, "failed": 2}
    failed = db.scalars(
        select(MailRecipient).where(
            MailRecipient.campaign_id == campaign["id"], MailRecipient.status == "failed"
        )
    ).all()
    assert {r.error_code for r in failed} == {"rejected"}


def test_resume_sends_only_pending(as_superadmin: TestClient, db: Session, fake: FakeTransport) -> None:
    campaign_id = _create(as_superadmin, _emails(4))["id"]
    # A crash mid-send: the campaign stayed `sending` and two recipients already went out.
    campaign = db.get(MailCampaign, campaign_id)
    campaign.status = "sending"
    campaign.sent_at = utcnow() - timedelta(hours=1)
    rows = db.scalars(
        select(MailRecipient).where(MailRecipient.campaign_id == campaign_id).order_by(MailRecipient.id)
    ).all()
    for row in rows[:2]:
        row.status = "accepted"
    db.commit()
    _send(as_superadmin, campaign_id, "resume")
    assert sorted(fake.sent_to) == sorted(r.email for r in rows[2:])
    _send(as_superadmin, campaign_id, "resume")  # nothing pending: nothing new
    assert len(fake.sent_to) == 2
    assert _get(as_superadmin, campaign_id)["status"] == "sent"


def test_quota_exceeded_is_422_before_sending(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "mail_daily_limit", 2)
    campaign = _create(as_superadmin, _emails(3))
    response = as_superadmin.post(f"{CAMPAIGNS}/{campaign['id']}/send")
    assert response.status_code == 422, response.text
    assert response.json()["error"]["details"] == {"remaining": 2}
    assert "2" in response.json()["error"]["message"]
    assert fake.calls == []
    assert _get(as_superadmin, campaign["id"])["status"] == "draft"


def test_rate_limit_6th_campaign_is_429(as_superadmin: TestClient, db: Session, fake: FakeTransport) -> None:
    for i in range(5):
        _send(as_superadmin, _create(as_superadmin, [f"uno{i}@ipn.mx"])["id"])
    sixth = _create(as_superadmin, ["seis@ipn.mx"])
    response = as_superadmin.post(f"{CAMPAIGNS}/{sixth['id']}/send")
    assert response.status_code == 429, response.text
    assert len(fake.calls) == 5
    assert _get(as_superadmin, sixth["id"])["status"] == "draft"


def test_mail_disabled_answers_503(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _create(as_superadmin, _emails(2))
    monkeypatch.setattr(get_settings(), "mail_enabled", False)
    for path, payload in (
        ("/api/mail/test", {"subject": "Prueba", "body": "Hola"}),
        (f"{CAMPAIGNS}/{campaign['id']}/send", None),
        (f"{CAMPAIGNS}/{campaign['id']}/resume", None),
    ):
        response = as_superadmin.post(path, json=payload)
        assert response.status_code == 503, (path, response.text)
        assert response.json()["error"]["message"] == "El correo está desactivado"
    assert fake.calls == []


def test_history_scoped_by_club_for_academy_admin(
    as_admin_ia: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    robotica = Academy(slug="robotica", name="Robótica")
    db.add(robotica)
    db.flush()
    other = MailCampaign(
        academy_id=robotica.id,
        audience_kind="academy",
        audience_params={"academy_id": robotica.id},
        subject="De otro club",
        body="x",
    )
    db.add(other)
    db.flush()
    own = _create(as_admin_ia, _emails(1), subject="De UpiixIA")
    items = as_admin_ia.get(CAMPAIGNS).json()["items"]
    assert [item["id"] for item in items] == [own["id"]]
    assert as_admin_ia.get(f"{CAMPAIGNS}/{other.id}").status_code == 403
    assert as_admin_ia.post(f"{CAMPAIGNS}/{other.id}/send").status_code == 403
    assert fake.calls == []


def test_history_shows_sender_and_counts(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mail_campaigns, "BATCH_SIZE", 2)
    fake.fail_calls = {0}
    campaign = _create(as_superadmin, _emails(3), subject="Reunión del viernes")
    _send(as_superadmin, campaign["id"])
    me = as_superadmin.get("/api/auth/me").json()
    page = as_superadmin.get(CAMPAIGNS).json()
    item = next(item for item in page["items"] if item["id"] == campaign["id"])
    assert item["sender"]["nickname"] == me["nickname"]
    assert "email" not in item["sender"]
    assert item["subject"] == "Reunión del viernes"
    assert item["audience"]["kind"] == "individual"
    assert item["recipient_count"] == 3
    assert item["counts_by_status"] == {"accepted": 1, "failed": 2}
    assert item["status"] == "partial"
    assert item["created_at"] and item["sent_at"]


def test_send_logs_have_no_addresses(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, caplog: pytest.LogCaptureFixture
) -> None:
    emails = _emails(2, prefix="privado")
    with caplog.at_level(logging.DEBUG):
        campaign = _create(as_superadmin, emails, subject="Asunto secreto")
        _send(as_superadmin, campaign["id"])
    assert "mail.campaign" in caplog.text  # the send was logged...
    for email in emails:
        assert email not in caplog.text  # ...with ids and counts only
    assert "Asunto secreto" not in caplog.text
    sender_id = db.scalar(select(User.id).where(User.email == "superadmin1@upiixsol.dev"))
    event = db.scalar(select(ActivityEvent).where(ActivityEvent.name == "mail.campaign_sent"))
    assert event is not None
    assert event.properties == {"count": 2}
    assert event.user_id == sender_id


class BrokenTransport(FakeTransport):
    """Raises on the calls listed in `raise_calls`; a retryable code makes the job retry once."""

    def __init__(self) -> None:
        super().__init__()
        self.raise_calls: set[int] = set()

    def send_batch(self, message: MailMessage, recipients: list[MailRecipientVars]) -> BatchResult:
        if len(self.calls) in self.raise_calls:
            self.calls.append((message, list(recipients)))
            raise RuntimeError("caída de red con ana@ipn.mx")
        return super().send_batch(message, recipients)


def test_retryable_failures_are_retried_once_and_errors_never_escape(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = BrokenTransport()
    app.dependency_overrides[get_mail_transport] = lambda: broken
    broken.fail_calls, broken.code = {0}, "provider_error"  # first call fails, the retry goes through
    first = _create(as_superadmin, _emails(2))
    _send(as_superadmin, first["id"])
    assert len(broken.calls) == 2
    assert _get(as_superadmin, first["id"])["counts_by_status"] == {"accepted": 2}
    broken.calls, broken.fail_calls, broken.raise_calls = [], set(), {0, 1}  # call and retry both raise
    second = _create(as_superadmin, _emails(2, prefix="otra"))
    _send(as_superadmin, second["id"])
    done = _get(as_superadmin, second["id"])
    assert done["status"] == "failed" and done["counts_by_status"] == {"failed": 2}
    mail_campaigns._send(db, 10_000, broken)  # a campaign that is gone, or not sending: nothing happens
    draft = _create(as_superadmin, _emails(1, prefix="borrador"))
    assert _send(as_superadmin, draft["id"], "resume")["status"] == "draft"  # resume never starts a draft
    # A job that blows up is logged by type and leaves the campaign as it was.
    monkeypatch.setattr(mail_campaigns, "_send", lambda *_args: 1 / 0)
    mail_campaigns.send_pending(second["id"], broken)
    mail_campaigns.send_pending(10_000, broken)


def test_failed_test_send_is_502_and_unknown_campaign_is_404(
    as_superadmin: TestClient, db: Session, fake: FakeTransport
) -> None:
    fake.fail_calls = {0}
    response = as_superadmin.post("/api/mail/test", json={"subject": "Prueba", "body": "Hola"})
    assert response.status_code == 502
    assert "@" not in response.text
    assert as_superadmin.get(f"{CAMPAIGNS}/999").status_code == 404
    assert as_superadmin.post(f"{CAMPAIGNS}/999/send").status_code == 404


def test_audience_params_keep_ids_not_addresses(
    as_superadmin: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    ia = seeded["academy_id"]
    make_user(db, email="ana@ipn.mx", academy_id=ia, role=Role.academy_admin)
    for audience, expected in (
        ({"kind": "academy", "academy_id": ia}, {"kind": "academy", "academy_id": ia}),
        ({"kind": "role", "role": "academy_admin"}, {"kind": "role", "role": "academy_admin"}),
        ({"kind": "all"}, {"kind": "all"}),
    ):
        response = as_superadmin.post(CAMPAIGNS, json={"subject": "A", "body": "B", "audience": audience})
        assert response.status_code == 201, response.text
        assert response.json()["audience"] == expected
    empty = as_superadmin.post(
        CAMPAIGNS, json={"subject": "A", "body": "B", "audience": {"kind": "role", "role": "member"}}
    )
    assert empty.status_code == 422  # every member is on the blocked seed domain


def test_admin_without_club_sees_no_history(db: Session, seeded: dict) -> None:
    db.add(MailCampaign(audience_kind="all", audience_params={}, subject="x", body="y"))
    lonely = make_user(db, email="sin.club@ipn.mx", role=Role.academy_admin)
    assert mail_campaigns.list_campaigns(db, lonely, None, 20).items == []
