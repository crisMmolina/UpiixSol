from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Academy, Event
from app.models.common import utcnow
from app.tests.conftest import make_academy


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def _event(academy_id: int | None = None, title: str = "Taller", days: int = 5) -> dict:
    start = (utcnow() + timedelta(days=days)).replace(microsecond=0)
    return {
        "academy_id": academy_id,
        "title": title,
        "description": "Trae laptop",
        "location": "Lab 3",
        "starts_at": _iso(start),
        "ends_at": _iso(start + timedelta(hours=2)),
    }


@pytest.fixture(autouse=True)
def _seed(seeded: dict) -> None:
    """Demo seed: one academy event + one global event."""


def test_list_events_in_range_ordered(as_member: TestClient) -> None:
    now = utcnow()
    page = as_member.get(
        "/api/events", params={"from": _iso(now), "to": _iso(now + timedelta(days=30))}
    ).json()
    titles = [e["title"] for e in page["items"]]
    assert titles == ["Taller: tu primera red neuronal", "Noche de proyectos UpiixSol"]
    assert page["items"][0]["academy_slug"] == "upiixia" and page["items"][1]["academy_slug"] is None
    empty = as_member.get(
        "/api/events", params={"from": _iso(now + timedelta(days=60)), "to": _iso(now + timedelta(days=90))}
    )
    assert empty.json()["items"] == []


def test_filter_by_academy_with_and_without_global(as_member: TestClient) -> None:
    with_global = as_member.get("/api/events", params={"academy": "upiixia"}).json()["items"]
    assert len(with_global) == 2
    only = as_member.get("/api/events", params={"academy": "upiixia", "include_global": "false"}).json()[
        "items"
    ]
    assert [e["academy_slug"] for e in only] == ["upiixia"]
    assert as_member.get("/api/events", params={"academy": "no-existe"}).status_code == 404


def test_events_of_inactive_academies_are_hidden(as_member: TestClient, db: Session, seeded: dict) -> None:
    db.get(Academy, seeded["academy_id"]).is_active = False
    db.flush()
    titles = [e["title"] for e in as_member.get("/api/events").json()["items"]]
    assert titles == ["Noche de proyectos UpiixSol"]


def test_superadmin_creates_global_event(as_superadmin: TestClient, as_member: TestClient) -> None:
    created = as_superadmin.post("/api/events", json=_event(title="Asamblea del club", days=2))
    assert created.status_code == 201
    body = created.json()
    assert body["academy_id"] is None and body["title"] == "Asamblea del club"
    titles = [e["title"] for e in as_member.get("/api/events").json()["items"]]
    assert titles[0] == "Asamblea del club"
    # It also shows in the campus home upcoming events (flow step 6).
    assert "Asamblea del club" in [e["title"] for e in as_member.get("/api/home").json()["upcoming_events"]]


def test_admin_ia_cannot_create_global_event_403(as_admin_ia: TestClient, seeded: dict) -> None:
    assert as_admin_ia.post("/api/events", json=_event()).status_code == 403
    created = as_admin_ia.post("/api/events", json=_event(academy_id=seeded["academy_id"]))
    assert created.status_code == 201 and created.json()["academy_slug"] == "upiixia"


def test_admin_cannot_touch_other_academy_events(as_admin_ia: TestClient, db: Session) -> None:
    robo = make_academy(db, "robotica", "Robótica")
    assert as_admin_ia.post("/api/events", json=_event(academy_id=robo.id)).status_code == 403
    foreign = Event(
        academy_id=robo.id, title="Robots", starts_at=utcnow(), ends_at=utcnow() + timedelta(hours=1)
    )
    db.add(foreign)
    db.flush()
    assert as_admin_ia.patch(f"/api/events/{foreign.id}", json=_event(academy_id=robo.id)).status_code == 403
    assert as_admin_ia.delete(f"/api/events/{foreign.id}").status_code == 403
    global_event = db.scalar(select(Event).where(Event.academy_id.is_(None)))
    assert as_admin_ia.delete(f"/api/events/{global_event.id}").status_code == 403


def test_admin_cannot_move_own_event_to_another_academy(
    as_admin_ia: TestClient, db: Session, seeded: dict
) -> None:
    robo = make_academy(db, "robotica", "Robótica")
    own = db.scalar(select(Event).where(Event.academy_id == seeded["academy_id"]))
    assert as_admin_ia.patch(f"/api/events/{own.id}", json=_event(academy_id=robo.id)).status_code == 403
    assert as_admin_ia.patch(f"/api/events/{own.id}", json=_event(academy_id=None)).status_code == 403


def test_update_and_delete(as_admin_ia: TestClient, as_member: TestClient, db: Session, seeded: dict) -> None:
    own = db.scalar(select(Event).where(Event.academy_id == seeded["academy_id"]))
    payload = {
        **_event(academy_id=seeded["academy_id"], title="Taller movido"),
        "description": "<script>x</script>Hola",
    }
    updated = as_admin_ia.patch(f"/api/events/{own.id}", json=payload).json()
    assert updated["title"] == "Taller movido" and "<script" not in updated["description"]
    assert as_member.patch(f"/api/events/{own.id}", json=payload).status_code == 403
    assert as_admin_ia.delete(f"/api/events/{own.id}").status_code == 204
    assert as_admin_ia.delete(f"/api/events/{own.id}").status_code == 404
    assert as_admin_ia.patch("/api/events/9999", json=payload).status_code == 404


def test_validation(as_superadmin: TestClient) -> None:
    bad = _event()
    bad["ends_at"] = bad["starts_at"].replace(bad["starts_at"][:4], str(int(bad["starts_at"][:4]) - 1))
    assert as_superadmin.post("/api/events", json=bad).status_code == 422
    assert (
        as_superadmin.post("/api/events", json={**_event(), "link": "javascript:alert(1)"}).status_code == 422
    )
    assert as_superadmin.post("/api/events", json={**_event(), "academy_id": 9999}).status_code == 404
    now = utcnow()
    inverted = as_superadmin.get(
        "/api/events", params={"from": _iso(now), "to": _iso(now - timedelta(days=1))}
    )
    assert inverted.status_code == 422


def test_members_cannot_create_and_anonymous_cannot_list(as_member: TestClient, client: TestClient) -> None:
    assert as_member.post("/api/events", json=_event()).status_code == 403
    assert client.get("/api/events").status_code == 401


def test_pagination(as_superadmin: TestClient, db: Session) -> None:
    base = datetime(2027, 1, 1, 12, tzinfo=UTC)
    for i in range(5):
        db.add(
            Event(
                title=f"E{i}", starts_at=base + timedelta(days=i), ends_at=base + timedelta(days=i, hours=1)
            )
        )
    db.flush()
    params = {"from": "2027-01-01T00:00:00+00:00", "to": "2027-02-01T00:00:00+00:00", "limit": 2}
    first = as_superadmin.get("/api/events", params=params).json()
    second = as_superadmin.get("/api/events", params={**params, "cursor": first["next_cursor"]}).json()
    assert [e["title"] for e in first["items"] + second["items"]] == ["E0", "E1", "E2", "E3"]


def test_naive_and_aware_datetimes_mix_without_500(as_superadmin: TestClient) -> None:
    """Naive values are read as UTC (reject #70 by joahan-claude)."""
    mixed = as_superadmin.get(
        "/api/events", params={"from": "2026-10-01T00:00:00Z", "to": "2026-10-31T00:00:00"}
    )
    assert mixed.status_code == 200
    inverted = as_superadmin.get(
        "/api/events", params={"from": "2026-10-31T00:00:00Z", "to": "2026-10-01T00:00:00"}
    )
    assert inverted.status_code == 422
    payload = {**_event(), "starts_at": "2027-03-01T18:00:00Z", "ends_at": "2027-03-01T20:00:00"}
    created = as_superadmin.post("/api/events", json=payload)
    assert created.status_code == 201
    assert created.json()["ends_at"].startswith("2027-03-01T20:00:00")
    shifted = {**payload, "starts_at": "2027-03-01T13:00:00-06:00", "ends_at": "2027-03-01T18:30:00"}
    assert as_superadmin.post("/api/events", json=shifted).status_code == 422  # 19:00Z > 18:30Z
