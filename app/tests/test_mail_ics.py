"""Calendar links and `.ics` for the email event card (UPS-087, spec 004 §Events and calendar)."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.main import app
from app.models import Academy, Event, User
from app.models.mail import MailCampaign
from app.services import mail_ics
from app.services.mail_blocks import Blocks, EventBlock
from app.services.mail_ics import CalendarEvent, build_ics, google_url, outlook_url, resolve_event

START = datetime(2026, 11, 20, 21, 0, tzinfo=UTC)  # 15:00 in Mexico City
STAMP = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


def _event(**overrides: object) -> CalendarEvent:
    base = {
        "title": "Taller de IA",
        "start": START,
        "end": START + timedelta(hours=2),
        "place": "Aula 3, UPIIZ",
        "description": "Trae tu laptop",
        "link": "https://upiixsol.com/eventos/1",
    }
    return CalendarEvent(**(base | overrides))  # type: ignore[arg-type]


def _unfold(raw: bytes) -> list[str]:
    return raw.decode("utf-8").replace("\r\n ", "").split("\r\n")


def test_ics_is_rfc5545_with_crlf_folding_and_escaping() -> None:
    long_title = "Taller " + "ñ" * 80
    raw = build_ics(
        _event(title=long_title, description="Uno, dos; tres\\ cuatro\nlínea 2\r\nlínea 3", place="A,B;C"),
        "uid-1@upiixsol.com",
        stamp=STAMP,
    )
    text = raw.decode("utf-8")
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "\n" not in text.replace("\r\n", "")  # every line break is CRLF
    assert "\r" not in text.replace("\r\n", "")
    physical = text.split("\r\n")[:-1]
    assert all(len(line.encode("utf-8")) <= 75 for line in physical)
    assert any(line.startswith(" ") for line in physical)  # the long title was folded
    assert "PRODID:" in text
    assert "VERSION:2.0" in text
    assert "METHOD:PUBLISH" in text
    lines = _unfold(raw)
    assert f"SUMMARY:{long_title}" in lines  # unfolding restores it, no split inside a character
    assert "DESCRIPTION:Uno\\, dos\\; tres\\\\ cuatro\\nlínea 2\\nlínea 3" in lines
    assert "LOCATION:A\\,B\\;C" in lines
    assert "URL:https://upiixsol.com/eventos/1" in lines


def test_ics_uses_utc_and_stable_uid() -> None:
    uid = mail_ics.ics_uid("tok_abc-123")
    assert uid == mail_ics.ics_uid("tok_abc-123") != mail_ics.ics_uid("tok_other")
    assert "tok_abc-123" in uid
    lines = _unfold(build_ics(_event(), uid, stamp=STAMP))
    assert f"UID:{uid}" in lines
    assert "DTSTAMP:20261117T120000Z" in lines
    assert "DTSTART:20261120T210000Z" in lines
    assert "DTEND:20261120T230000Z" in lines
    assert build_ics(_event(), uid, stamp=STAMP) == build_ics(_event(), uid, stamp=STAMP)
    token = mail_ics.new_ics_token()
    assert len(token) == 43 and token != mail_ics.new_ics_token()


def test_typed_15h_is_210000Z_in_ics_and_google() -> None:
    block = Blocks.model_validate(
        [{"kind": "event", "title": "Taller", "start": "2026-11-20T15:00:00", "end": "2026-11-20T17:00:00"}]
    ).root[0]
    assert isinstance(block, EventBlock)
    event = CalendarEvent(title=block.title or "", start=block.start, end=block.end)  # type: ignore[arg-type]
    assert "DTSTART:20261120T210000Z" in _unfold(build_ics(event, "u@x", stamp=STAMP))
    assert "20261120T210000Z/20261120T230000Z" in google_url(event)


def test_google_calendar_url() -> None:
    url = urlsplit(google_url(_event()))
    assert (url.scheme, url.netloc, url.path) == ("https", "calendar.google.com", "/calendar/render")
    query = parse_qs(url.query)
    assert query["action"] == ["TEMPLATE"]
    assert query["text"] == ["Taller de IA"]
    assert query["dates"] == ["20261120T210000Z/20261120T230000Z"]
    assert query["location"] == ["Aula 3, UPIIZ"]
    assert "Trae tu laptop" in query["details"][0]
    assert "https://upiixsol.com/eventos/1" in query["details"][0]
    bare = parse_qs(urlsplit(google_url(_event(place=None, description=None, link=None))).query)
    assert "location" not in bare and "details" not in bare


def test_outlook_calendar_url() -> None:
    url = urlsplit(outlook_url(_event()))
    assert (url.scheme, url.netloc) == ("https", "outlook.live.com")
    assert url.path == "/calendar/0/deeplink/compose"
    query = parse_qs(url.query)
    assert query["subject"] == ["Taller de IA"]
    assert query["startdt"] == ["2026-11-20T21:00:00Z"]
    assert query["enddt"] == ["2026-11-20T23:00:00Z"]
    assert query["location"] == ["Aula 3, UPIIZ"]
    assert "Trae tu laptop" in query["body"][0]


def _campus_event(db: Session, academy_id: int | None, **extra: object) -> Event:
    event = Event(
        academy_id=academy_id,
        title="Demo Day",
        description="Proyectos",
        location="Auditorio",
        link="https://upiixsol.com/demo",
        starts_at=START,
        ends_at=START + timedelta(hours=3),
        **extra,
    )
    db.add(event)
    db.flush()
    return event


def _user(db: Session, email: str) -> User:
    return db.scalar(select(User).where(User.email == email))


def _block(event_id: int) -> EventBlock:
    block = Blocks.model_validate([{"kind": "event", "event_id": event_id}]).root[0]
    assert isinstance(block, EventBlock)
    return block


def test_resolve_event_block_from_campus_event(db: Session, seeded: dict) -> None:
    mine = _campus_event(db, seeded["academy_id"])
    glob = _campus_event(db, None)
    for sender in ("admin.ia@upiixsol.dev", "superadmin1@upiixsol.dev"):
        resolved = resolve_event(db, _user(db, sender), _block(mine.id))
        assert resolved == CalendarEvent(
            title="Demo Day",
            start=START,
            end=START + timedelta(hours=3),
            place="Auditorio",
            description="Proyectos",
            link="https://upiixsol.com/demo",
        )
    assert resolve_event(db, _user(db, "admin.ia@upiixsol.dev"), _block(glob.id)).title == "Demo Day"
    typed = Blocks.model_validate(
        [{"kind": "event", "title": "Mío", "start": "2026-11-20T15:00:00", "end": "2026-11-20T16:00:00"}]
    ).root[0]
    assert isinstance(typed, EventBlock)
    out = resolve_event(db, _user(db, "admin.ia@upiixsol.dev"), typed)
    assert (out.title, out.start) == ("Mío", START)
    with pytest.raises(AppError) as missing:
        resolve_event(db, _user(db, "admin.ia@upiixsol.dev"), _block(999999))
    assert missing.value.status == 404


def test_academy_admin_cannot_reference_other_club_event(db: Session, seeded: dict) -> None:
    other = Academy(slug="robotica", name="Robótica")
    db.add(other)
    db.flush()
    foreign = _campus_event(db, other.id)
    with pytest.raises(AppError) as denied:
        resolve_event(db, _user(db, "admin.ia@upiixsol.dev"), _block(foreign.id))
    assert denied.value.status == 403
    assert resolve_event(db, _user(db, "superadmin1@upiixsol.dev"), _block(foreign.id)).title == "Demo Day"


@pytest.fixture
def anon(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def test_ics_endpoint_serves_text_calendar(db: Session, seeded: dict, anon: TestClient) -> None:
    token = mail_ics.new_ics_token()
    campus = _campus_event(db, seeded["academy_id"])
    db.add(
        MailCampaign(
            sender_id=seeded["admin_ia_id"],
            academy_id=seeded["academy_id"],
            audience_kind="academy",
            audience_params={"academy_id": seeded["academy_id"]},
            subject="Evento",
            body="",
            status="sent",
            content=[{"kind": "event", "event_id": campus.id}],
            ics_token=token,
        )
    )
    db.flush()
    response = anon.get(f"/api/mail/ics/{token}.ics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/calendar; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="evento.ics"'
    body = response.content
    assert body == build_ics(
        resolve_event(db, _user(db, "admin.ia@upiixsol.dev"), _block(campus.id)),
        mail_ics.ics_uid(token),
        stamp=_stamp_of(body),
    )
    assert b"SUMMARY:Demo Day\r\n" in body


def _stamp_of(raw: bytes) -> datetime:
    line = next(item for item in _unfold(raw) if item.startswith("DTSTAMP:"))
    return datetime.strptime(line[8:], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


@pytest.mark.parametrize("token", ["nope", "A" * 43, "x" * 200, "%20"])
def test_unknown_ics_token_is_404(anon: TestClient, token: str) -> None:
    response = anon.get(f"/api/mail/ics/{token}.ics")
    assert response.status_code == 404
    assert "campaña" not in response.text.lower() and "campaign" not in response.text.lower()


def _campaign(db: Session, seeded: dict, content: object, *, sender_id: int | None) -> str:
    token = mail_ics.new_ics_token()
    db.add(
        MailCampaign(
            sender_id=sender_id,
            academy_id=seeded["academy_id"],
            audience_kind="academy",
            audience_params={"academy_id": seeded["academy_id"]},
            subject="Aviso",
            body="",
            status="sent",
            content=content,
            ics_token=token,
        )
    )
    db.flush()
    return token


def test_ics_endpoint_is_404_without_event_sender_or_scope(
    db: Session, seeded: dict, anon: TestClient
) -> None:
    other = Academy(slug="robotica", name="Robótica")
    db.add(other)
    db.flush()
    foreign = _campus_event(db, other.id)
    admin = seeded["admin_ia_id"]
    typed = {"kind": "event", "title": "T", "start": "2026-11-20T21:00:00Z", "end": "2026-11-20T22:00:00Z"}
    cases = [
        _campaign(db, seeded, [{"kind": "divider"}, "x"], sender_id=admin),  # no event block
        _campaign(db, seeded, None, sender_id=admin),  # legacy campaign
        _campaign(db, seeded, [typed], sender_id=None),  # sender deleted: fail closed
        _campaign(db, seeded, [{"kind": "event", "event_id": foreign.id}], sender_id=admin),  # scope
    ]
    assert [anon.get(f"/api/mail/ics/{token}.ics").status_code for token in cases] == [404] * 4
    ok = _campaign(db, seeded, [typed], sender_id=admin)
    assert anon.get(f"/api/mail/ics/{ok}.ics").status_code == 200


def test_ics_omits_empty_optional_fields() -> None:
    lines = _unfold(build_ics(_event(place=None, description=None, link=None), "u@x", stamp=STAMP))
    assert not [item for item in lines if item.split(":")[0] in {"LOCATION", "DESCRIPTION", "URL"}]
    assert "body" not in parse_qs(urlsplit(outlook_url(_event(description=None, link=None))).query)
    only_link = parse_qs(urlsplit(google_url(_event(description=None))).query)
    assert only_link["details"] == ["https://upiixsol.com/eventos/1"]


def test_outlook_without_place_keeps_body() -> None:
    query = parse_qs(urlsplit(outlook_url(_event(place=None))).query)
    assert "location" not in query and "Trae tu laptop" in query["body"][0]
