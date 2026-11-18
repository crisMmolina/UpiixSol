"""Event photo (UPS-094): upload, replace, remove, scope and storage rules. Mirrors the blog cover tests."""

import io
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event
from app.models.common import utcnow
from app.tests.conftest import make_academy

MB = 1024 * 1024


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def _file(name: str = "a.png", data: bytes | None = None, kind: str = "image/png") -> dict:
    return {"file": (name, _png() if data is None else data, kind)}


@pytest.fixture
def own_event(db: Session, seeded: dict) -> Event:
    return db.scalar(select(Event).where(Event.academy_id == seeded["academy_id"]))


@pytest.fixture
def global_event(db: Session, seeded: dict) -> Event:
    return db.scalar(select(Event).where(Event.academy_id.is_(None)))


def test_manager_uploads_replaces_and_removes_an_event_cover(
    as_admin_ia: TestClient, as_superadmin: TestClient, own_event: Event, global_event: Event
) -> None:
    first = as_admin_ia.post(f"/api/events/{own_event.id}/cover", files=_file())
    assert first.status_code == 200
    old = first.json()["cover_url"]
    assert old.startswith("/media/cover/") and old.endswith(".webp")
    assert first.json()["id"] == own_event.id and first.json()["title"] == own_event.title
    assert as_admin_ia.get(old).status_code == 200

    second = as_admin_ia.post(f"/api/events/{own_event.id}/cover", files=_file("b.png")).json()
    new = second["cover_url"]
    assert new.startswith("/media/cover/") and new != old
    assert as_admin_ia.get(old).status_code == 404  # the previous file goes away after the commit
    assert as_admin_ia.get(new).status_code == 200

    removed = as_admin_ia.delete(f"/api/events/{own_event.id}/cover")
    assert removed.status_code == 200 and removed.json()["cover_url"] is None
    assert as_admin_ia.get(new).status_code == 404
    assert as_admin_ia.delete(f"/api/events/{own_event.id}/cover").json()["cover_url"] is None  # idempotent

    # The superadmin handles a global event, and the list carries the url.
    done = as_superadmin.post(f"/api/events/{global_event.id}/cover", files=_file())
    assert done.status_code == 200 and done.json()["academy_id"] is None
    listed = {e["id"]: e for e in as_superadmin.get("/api/events").json()["items"]}
    assert listed[global_event.id]["cover_url"] == done.json()["cover_url"]
    assert as_superadmin.post("/api/events/9999/cover", files=_file()).status_code == 404
    assert as_superadmin.delete("/api/events/9999/cover").status_code == 404


def test_academy_admin_cannot_touch_the_cover_of_another_club_or_a_global_event(
    as_admin_ia: TestClient,
    as_member: TestClient,
    as_superadmin: TestClient,
    client: TestClient,
    db: Session,
    own_event: Event,
    global_event: Event,
) -> None:
    robo = make_academy(db, "robotica", "Robótica")
    foreign = Event(
        academy_id=robo.id, title="Robots", starts_at=utcnow(), ends_at=utcnow() + timedelta(hours=1)
    )
    db.add(foreign)
    db.flush()
    seeded_cover = as_superadmin.post(f"/api/events/{foreign.id}/cover", files=_file()).json()["cover_url"]

    for event_id in (foreign.id, global_event.id):
        assert as_admin_ia.post(f"/api/events/{event_id}/cover", files=_file()).status_code == 403
        assert as_admin_ia.delete(f"/api/events/{event_id}/cover").status_code == 403
    assert db.get(Event, foreign.id).cover_url == seeded_cover
    assert db.get(Event, global_event.id).cover_url is None

    for denied, code in ((as_member, 403), (client, 401)):
        assert denied.post(f"/api/events/{own_event.id}/cover", files=_file()).status_code == code
        assert denied.delete(f"/api/events/{own_event.id}/cover").status_code == code
    assert db.get(Event, own_event.id).cover_url is None


def test_rejects_svg_fake_image_and_oversized_cover(
    as_admin_ia: TestClient, db: Session, own_event: Event
) -> None:
    url = f"/api/events/{own_event.id}/cover"
    good = as_admin_ia.post(url, files=_file()).json()["cover_url"]
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="5"/></svg>'
    for files, status in (
        (_file("x.svg", svg, "image/svg+xml"), 422),
        (_file("x.png", b"<html>not an image</html>", "image/png"), 422),
        (_file("x.png", b"", "image/png"), 422),
        (_file("big.png", b"x" * (5 * MB + 1), "image/png"), 413),
    ):
        response = as_admin_ia.post(url, files=files)
        assert response.status_code == status
        assert response.json()["error"]["message"]  # the existing media error, in Spanish
    db.expire_all()
    assert db.get(Event, own_event.id).cover_url == good  # a bad file leaves the event unchanged
    assert as_admin_ia.get(good).status_code == 200


def test_deleting_an_event_deletes_its_cover_after_commit(
    as_admin_ia: TestClient, db: Session, own_event: Event, monkeypatch: pytest.MonkeyPatch
) -> None:
    cover = as_admin_ia.post(f"/api/events/{own_event.id}/cover", files=_file()).json()["cover_url"]

    def boom() -> None:
        raise RuntimeError("db down")

    event_id = own_event.id
    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", boom)
        assert as_admin_ia.delete(f"/api/events/{event_id}").status_code == 500
    db.rollback()  # what the request teardown does for a failed commit
    assert as_admin_ia.get(cover).status_code == 200  # the commit failed: the file stays

    assert as_admin_ia.delete(f"/api/events/{event_id}").status_code == 204
    assert as_admin_ia.get(cover).status_code == 404
    assert db.get(Event, event_id) is None


def test_event_payload_carries_cover_url_and_no_personal_data(
    as_admin_ia: TestClient, as_member: TestClient, own_event: Event
) -> None:
    expected = {
        "id",
        "academy_id",
        "academy_slug",
        "title",
        "description",
        "location",
        "link",
        "starts_at",
        "ends_at",
        "cover_url",
    }
    uploaded = as_admin_ia.post(f"/api/events/{own_event.id}/cover", files=_file()).json()
    assert set(uploaded) == expected
    listed = {e["id"]: e for e in as_member.get("/api/events").json()["items"]}
    assert set(listed[own_event.id]) == expected
    assert listed[own_event.id]["cover_url"] == uploaded["cover_url"]
    assert set(as_admin_ia.delete(f"/api/events/{own_event.id}/cover").json()) == expected
