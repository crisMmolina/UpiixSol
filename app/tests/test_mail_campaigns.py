"""Mail campaigns (UPS-075, spec 003 §Composing and sending, §History): draft → confirm →
background batches, quota, hourly limit, kill switch, history.

A Fake transport replaces Mailgun through `app.dependency_overrides[get_mail_transport]`; the background
job opens its own session, bound here to the test engine. Recipients are outside addresses (`@ipn.mx`),
since the seeded accounts are on the blocked `upiixsol.dev` domain.
"""

import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.main import app
from app.models import Academy, Event, Role, User
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


def test_monthly_quota_exceeded_is_422_before_sending(
    as_superadmin: TestClient, db: Session, fake: FakeTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "mail_monthly_limit", 2)
    campaign = _create(as_superadmin, _emails(3))
    response = as_superadmin.post(f"{CAMPAIGNS}/{campaign['id']}/send")
    assert response.status_code == 422, response.text
    assert response.json()["error"]["details"] == {"remaining": 2}
    message = response.json()["error"]["message"]
    assert "2" in message and "se renueva el" in message
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


def test_unknown_campaign_is_404(as_superadmin: TestClient, db: Session, fake: FakeTransport) -> None:
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


# ── Spec 004 (UPS-089): blocks, sender, Reply-To, .ics ──────

PARAGRAPH = {"kind": "paragraph", "text": "Hola a **todos**"}
EVENT = {
    "kind": "event",
    "title": "Taller de IA",
    "start": "2026-12-01T20:00:00Z",
    "end": "2026-12-01T22:00:00Z",
    "place": "Aula 3",
}


def _create_blocks(client: TestClient, blocks: list[dict], **extra: object) -> "object":
    payload = {
        "subject": "Aviso",
        "blocks": blocks,
        "audience": {"kind": "individual", "emails": _emails(2)},
    } | extra
    return client.post(CAMPAIGNS, json=payload)


def test_create_campaign_with_blocks_preheader_and_reply_to(
    as_superadmin: TestClient, db: Session, fake: FakeTransport
) -> None:
    response = _create_blocks(as_superadmin, [PARAGRAPH], preheader="Mira esto", reply_to="Club@Ipn.mx")
    assert response.status_code == 201, response.text
    row = db.get(MailCampaign, response.json()["id"])
    assert row.content == [{"kind": "paragraph", "text": "Hola a **todos**"}]
    assert (row.preheader, row.reply_to, row.ics_token) == ("Mira esto", "club@ipn.mx", None)
    bad = _create_blocks(as_superadmin, [PARAGRAPH], reply_to="a@b.mx\r\nBcc: x@y.mx")
    assert bad.status_code == 422
    assert _create_blocks(as_superadmin, []).status_code == 422
    both = _create_blocks(as_superadmin, [PARAGRAPH], body="Hola")
    assert both.status_code == 422  # one format per campaign
    with_event = _create_blocks(as_superadmin, [PARAGRAPH, EVENT])
    assert len(db.get(MailCampaign, with_event.json()["id"]).ics_token) == 43


def test_superadmin_picks_sender_club_or_board(
    as_superadmin: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    ia = seeded["academy_id"]
    robotica = Academy(slug="robotica", name="Robótica")
    closed = Academy(slug="cerrado", name="Cerrado", is_active=False)
    db.add_all([robotica, closed])
    db.flush()
    make_user(db, email="ana@ipn.mx", academy_id=ia, role=Role.academy_admin)

    def sender_of(response) -> int | None:  # noqa: ANN001
        assert response.status_code == 201, response.text
        return db.get(MailCampaign, response.json()["id"]).sender_academy_id

    club = _create_blocks(as_superadmin, [PARAGRAPH], audience={"kind": "academy", "academy_id": ia})
    assert sender_of(club) == ia  # defaults to the audience's club
    assert sender_of(_create_blocks(as_superadmin, [PARAGRAPH])) is None  # UpiixSol
    picked = _create_blocks(
        as_superadmin,
        [PARAGRAPH],
        audience={"kind": "academy", "academy_id": ia},
        sender_academy_id=robotica.id,
    )
    assert sender_of(picked) == robotica.id
    assert _create_blocks(as_superadmin, [PARAGRAPH], sender_academy_id=closed.id).status_code == 422
    assert _create_blocks(as_superadmin, [PARAGRAPH], sender_academy_id=9999).status_code == 422
    out = as_superadmin.get(f"{CAMPAIGNS}/{club.json()['id']}").json()
    assert out["sender_academy_id"] == ia and out["sender_name"] == "UpiixIA"
    board = as_superadmin.get(f"{CAMPAIGNS}/{_create_blocks(as_superadmin, [PARAGRAPH]).json()['id']}").json()
    assert board["sender_academy_id"] is None and board["sender_name"] == "UpiixSol"


def test_academy_admin_sender_is_always_own_club(
    as_admin_ia: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    other = Academy(slug="robotica", name="Robótica")
    db.add(other)
    db.flush()
    response = _create_blocks(as_admin_ia, [PARAGRAPH], sender_academy_id=other.id)
    assert response.status_code == 201, response.text
    assert db.get(MailCampaign, response.json()["id"]).sender_academy_id == seeded["academy_id"]


def test_send_uses_sender_in_from_name_and_header(
    as_superadmin: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    campaign = _create_blocks(as_superadmin, [PARAGRAPH], sender_academy_id=seeded["academy_id"]).json()
    _send(as_superadmin, campaign["id"])
    message = fake.calls[0][0]
    assert message.from_name == "UpiixIA · UpiixSol"
    assert "UpiixIA" in message.html
    board = _create_blocks(as_superadmin, [PARAGRAPH]).json()
    _send(as_superadmin, board["id"])
    assert fake.calls[-1][0].from_name is None  # the board: the plain From


def test_send_attaches_evento_ics_and_sets_reply_to(
    as_superadmin: TestClient, db: Session, fake: FakeTransport
) -> None:
    campaign = _create_blocks(as_superadmin, [PARAGRAPH, EVENT], reply_to="club@ipn.mx").json()
    _send(as_superadmin, campaign["id"])
    message = fake.calls[0][0]
    ((name, kind, data),) = message.attachments
    assert (name, kind) == ("evento.ics", "text/calendar; charset=utf-8; method=PUBLISH")
    assert b"SUMMARY:Taller de IA" in data
    assert message.reply_to == "club@ipn.mx"
    token = db.get(MailCampaign, campaign["id"]).ics_token
    assert f"/api/mail/ics/{token}.ics" in message.html
    plain = _create_blocks(as_superadmin, [PARAGRAPH]).json()
    _send(as_superadmin, plain["id"])
    assert fake.calls[-1][0].attachments == []
    assert fake.calls[-1][0].reply_to is None


def test_event_resolved_at_send_time(as_superadmin: TestClient, db: Session, fake: FakeTransport) -> None:
    event = Event(
        title="Título viejo",
        starts_at=datetime(2026, 12, 2, 20, tzinfo=UTC),
        ends_at=datetime(2026, 12, 2, 22, tzinfo=UTC),
    )
    db.add(event)
    db.flush()
    block = {"kind": "event", "event_id": event.id}
    campaign = _create_blocks(as_superadmin, [block]).json()
    event.title = "Título nuevo"
    db.commit()
    _send(as_superadmin, campaign["id"])
    message = fake.calls[0][0]
    assert "Título nuevo" in message.html and "Título viejo" not in message.html
    assert b"SUMMARY:T\xc3\xadtulo nuevo" in message.attachments[0][2]


def test_legacy_body_campaign_still_sends_and_lists(
    as_superadmin: TestClient, db: Session, fake: FakeTransport
) -> None:
    legacy = _create(as_superadmin, _emails(2))
    blocks = _create_blocks(as_superadmin, [PARAGRAPH]).json()
    _send(as_superadmin, legacy["id"])
    _send(as_superadmin, blocks["id"])
    assert "Hola a todos" in fake.calls[0][0].html
    assert fake.calls[0][0].attachments == [] and fake.calls[0][0].from_name is None
    listed = as_superadmin.get(CAMPAIGNS).json()["items"]
    assert {item["id"] for item in listed} == {legacy["id"], blocks["id"]}


def test_test_send_endpoint_is_gone(as_superadmin: TestClient, fake: FakeTransport) -> None:
    response = as_superadmin.post("/api/mail/test", json={"subject": "Prueba", "body": "Hola"})
    assert response.status_code in (404, 405)
    assert fake.calls == []


def test_send_resolves_mix_at_send_time(
    as_admin_ia: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    from app.models import Enrollment
    from app.models.mail import MailSuppression

    ia = seeded["academy_id"]
    uno = make_user(db, email="uno@ipn.mx")
    dos = make_user(db, email="dos@ipn.mx")
    db.add_all([Enrollment(user_id=uno.id, academy_id=ia), Enrollment(user_id=dos.id, academy_id=ia)])
    db.add(MailSuppression(email="baja.fuera@gmail.com", reason="unsubscribed"))
    db.flush()
    audience = {
        "kind": "mix",
        "sources": [{"kind": "academy", "academy_id": ia}],
        "exclude_user_ids": [dos.id],
        "emails": ["fuera@gmail.com", "baja.fuera@gmail.com"],
    }
    preview = as_admin_ia.post("/api/mail/audience/preview", json=audience).json()
    assert preview["count"] == 3  # blind for a club admin: the unsubscribed typed address still counts
    tres = make_user(db, email="tres@ipn.mx")  # joins the club after the preview
    db.add(Enrollment(user_id=tres.id, academy_id=ia))
    db.flush()
    response = as_admin_ia.post(CAMPAIGNS, json={"subject": "Hola", "body": "Texto", "audience": audience})
    assert response.status_code == 201, response.text
    campaign = response.json()
    assert campaign["audience"] == {
        "kind": "mix",
        "sources": [{"kind": "academy", "academy_id": ia}],
        "user_ids": [],
        "excluded": 1,
        "outside": 2,
    }  # ids and counts, never addresses
    stored = db.get(MailCampaign, campaign["id"])
    assert stored.academy_id == ia and stored.sender_academy_id == ia and stored.audience_kind == "mix"
    _send(as_admin_ia, campaign["id"])
    assert sorted(fake.sent_to) == ["fuera@gmail.com", "tres@ipn.mx", "uno@ipn.mx"]


def test_old_audience_kinds_still_work(
    as_superadmin: TestClient, db: Session, seeded: dict, fake: FakeTransport
) -> None:
    from app.models import Enrollment

    ia = seeded["academy_id"]
    robotica = Academy(slug="robotica", name="Robótica")
    db.add(robotica)
    db.flush()
    ana = make_user(db, email="ana@ipn.mx")
    db.add(Enrollment(user_id=ana.id, academy_id=robotica.id))
    db.flush()
    for audience in (
        {"kind": "all"},
        {"kind": "academy", "academy_id": robotica.id},
        {"kind": "role", "role": "member"},
        {"kind": "individual", "user_ids": [ana.id], "emails": ["fuera@gmail.com"]},
    ):
        preview = as_superadmin.post("/api/mail/audience/preview", json=audience)
        assert preview.status_code == 200, preview.text
        assert "removed" not in preview.json()  # old kinds answer exactly as before (`removed` is mix-only)
        response = as_superadmin.post(CAMPAIGNS, json={"subject": "A", "body": "B", "audience": audience})
        assert response.status_code == 201, response.text
        assert response.json()["audience"]["kind"] == audience["kind"]
    # superadmin mix: one club source → that club is the campaign's club and its sender
    mix = {"kind": "mix", "sources": [{"kind": "academy", "academy_id": robotica.id}], "user_ids": [ana.id]}
    response = as_superadmin.post(CAMPAIGNS, json={"subject": "A", "body": "B", "audience": mix})
    assert response.status_code == 201, response.text
    stored = db.get(MailCampaign, response.json()["id"])
    assert (stored.academy_id, stored.sender_academy_id) == (robotica.id, robotica.id)
    wide = {"kind": "mix", "sources": [{"kind": "all"}, {"kind": "academy", "academy_id": ia}]}
    response = as_superadmin.post(CAMPAIGNS, json={"subject": "A", "body": "B", "audience": wide})
    assert response.status_code == 201, response.text
    stored = db.get(MailCampaign, response.json()["id"])
    assert (stored.academy_id, stored.sender_academy_id) == (None, None)
