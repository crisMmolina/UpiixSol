"""Usage analytics (UPS-037): client endpoint, server capture middleware and helpers."""

import logging
from datetime import UTC, datetime, timedelta

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse

from app.models import (
    Academy,
    ActivityEvent,
    Channel,
    LearningRoute,
    Lesson,
    Module,
    Post,
    Resource,
    User,
)
from app.models.common import utcnow
from app.services import analytics as service
from app.tests.conftest import auth_headers

SESSION = "tab-1234abcd"


@pytest.fixture
def tracking(monkeypatch: pytest.MonkeyPatch, engine: Engine) -> None:
    """Analytics on (ENV=test turns it off by default) and background writes on the test database."""
    monkeypatch.setattr(
        service, "get_analytics_settings", lambda: service.AnalyticsSettings(analytics_enabled=True)
    )
    monkeypatch.setattr(service, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))


def _events(db: Session) -> list[ActivityEvent]:
    db.expire_all()
    return list(db.scalars(select(ActivityEvent).order_by(ActivityEvent.id)))


def _lesson(db: Session, academy_id: int) -> Lesson:
    return db.scalar(
        select(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(LearningRoute, Module.route_id == LearningRoute.id)
        .where(LearningRoute.academy_id == academy_id, Lesson.is_published.is_(True))
        .order_by(Lesson.id)
    )


def _post(db: Session) -> Post:
    return db.scalar(select(Post).where(Post.is_hidden.is_(False)).order_by(Post.id))


# ── Settings ────────────────────────────────────────────────


def test_enabled_by_default_except_in_tests() -> None:
    assert service.AnalyticsSettings(env="dev").enabled is True
    assert service.AnalyticsSettings(env="test").enabled is False
    assert service.AnalyticsSettings(env="test", analytics_enabled=True).enabled is True
    assert service.AnalyticsSettings(env="prod", analytics_enabled=False).enabled is False
    assert isinstance(service.get_analytics_settings(), service.AnalyticsSettings)


# ── Client endpoint ─────────────────────────────────────────


def test_events_require_a_session(client: TestClient, tracking: None) -> None:
    body = {"session_id": SESSION, "events": [{"name": "page.view", "path": "/"}]}
    assert client.post("/api/analytics/events", json=body).status_code == 401


def test_events_are_recorded_with_user_session_and_club(
    as_member: TestClient, db: Session, seeded: dict, tracking: None
) -> None:
    body = {
        "session_id": SESSION,
        "events": [
            {"name": "page.view", "path": "/a/:slug/clases/:lessonId", "academy_slug": "upiixia"},
            {
                "name": "video.play",
                "subject_type": "lesson",
                "subject_id": 7,
                "academy_slug": "no-existe",
                "properties": {"position_s": 12, "rate": 1.5},
            },
            {"name": "search.performed", "subject_type": "lesson", "properties": {"query_length": 4}},
        ],
    }
    response = as_member.post("/api/analytics/events", json=body)
    assert response.status_code == 202
    assert response.json() == {"accepted": 3}
    view, play, search = _events(db)
    assert {e.user_id for e in (view, play, search)} == {seeded["member_id"]}
    assert {e.source for e in (view, play, search)} == {"web"}
    assert {e.session_id for e in (view, play, search)} == {SESSION}
    assert view.name == "page.view" and view.academy_id == seeded["academy_id"]
    assert view.properties == {"path": "/a/:slug/clases/:lessonId"}
    assert (play.subject_type, play.subject_id, play.academy_id) == ("lesson", 7, None)
    assert play.properties == {"position_s": 12, "rate": 1.5}
    assert (search.subject_type, search.subject_id) == (None, None)  # a type without an id is dropped


@pytest.mark.parametrize(
    "event",
    [
        {"name": "lesson.completed"},  # server-only name
        {"name": "hack"},
        {"name": "page.view", "path": "https://evil.example/x"},
        {"name": "page.view", "properties": {"email": "a@b.c"}},
        {"name": "page.view", "properties": {"Boleta": "2026000001"}},
        {"name": "page.view", "properties": {"blob": "x" * 2100}},
        {"name": "page.view", "properties": {"nested": {"a": 1}}},
        {"name": "page.view", "subject_type": "user", "subject_id": 1},
        {"name": "page.view", "user_id": 1},
    ],
)
def test_invalid_events_are_422(as_member: TestClient, db: Session, tracking: None, event: dict) -> None:
    response = as_member.post("/api/analytics/events", json={"session_id": SESSION, "events": [event]})
    assert response.status_code == 422
    assert _events(db) == []


def test_batch_limits(as_member: TestClient, tracking: None) -> None:
    def post(events: list[dict], session_id: str = SESSION) -> int:
        return as_member.post(
            "/api/analytics/events", json={"session_id": session_id, "events": events}
        ).status_code

    assert post([{"name": "page.view"}] * 50) == 202
    assert post([{"name": "page.view"}] * 51) == 422
    assert post([]) == 422
    assert post([{"name": "page.view"}], session_id="x") == 422
    assert post([{"name": "page.view"}], session_id="bad session id!") == 422
    near_limit = {"name": "page.view", "properties": {"blob": "x" * 2000}}
    assert post([near_limit]) == 202


def test_occurred_at_is_clamped_to_now(as_member: TestClient, db: Session, tracking: None) -> None:
    now = utcnow()
    events = [
        {"name": "page.view", "occurred_at": (now - timedelta(days=3)).isoformat()},
        {"name": "page.view", "occurred_at": (now + timedelta(days=3)).isoformat()},
        {"name": "page.view", "occurred_at": (now - timedelta(minutes=1)).replace(tzinfo=None).isoformat()},
        {"name": "page.view"},
    ]
    assert (
        as_member.post("/api/analytics/events", json={"session_id": SESSION, "events": events}).status_code
        == 202
    )
    old, future, naive, missing = (e.occurred_at for e in _events(db))
    skew = service.CLOCK_SKEW + timedelta(seconds=5)
    assert now - skew <= old <= now - service.CLOCK_SKEW + timedelta(seconds=5)
    assert now + service.CLOCK_SKEW - timedelta(seconds=5) <= future <= now + skew
    assert abs(naive - (now - timedelta(minutes=1))) < timedelta(seconds=5)
    assert abs(missing - now) < timedelta(seconds=5)


def test_clamp_helper() -> None:
    now = datetime(2026, 10, 8, 12, tzinfo=UTC)
    assert service.clamp(None, now) == now
    assert service.clamp(datetime(2026, 10, 8, 12, 2), now) == datetime(2026, 10, 8, 12, 2, tzinfo=UTC)
    assert service.clamp(datetime(2020, 1, 1, tzinfo=UTC), now) == now - service.CLOCK_SKEW


def test_disabled_endpoint_accepts_and_drops(
    as_member: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        service, "get_analytics_settings", lambda: service.AnalyticsSettings(analytics_enabled=False)
    )
    response = as_member.post(
        "/api/analytics/events", json={"session_id": SESSION, "events": [{"name": "page.view"}]}
    )
    assert response.status_code == 202 and response.json() == {"accepted": 0}
    assert _events(db) == []


def test_events_are_rate_limited_per_user(
    db: Session, seeded: dict, tracking: None, client: TestClient
) -> None:
    member = db.get(User, seeded["member_id"])
    admin = db.get(User, seeded["admin_ia_id"])
    body = {"session_id": SESSION, "events": [{"name": "page.view"}]}
    codes = [
        client.post("/api/analytics/events", json=body, headers=auth_headers(member)).status_code
        for _ in range(31)
    ]
    assert codes[:30] == [202] * 30 and codes[30] == 429
    assert client.post("/api/analytics/events", json=body, headers=auth_headers(admin)).status_code == 202


# ── Server capture (middleware) ─────────────────────────────


def test_lesson_progress_is_captured_with_club(
    as_member: TestClient, db: Session, seeded: dict, tracking: None
) -> None:
    lesson = _lesson(db, seeded["academy_id"])
    assert as_member.get(f"/api/lessons/{lesson.id}").status_code == 200
    assert as_member.post(f"/api/lessons/{lesson.id}/complete").status_code == 200
    assert as_member.delete(f"/api/lessons/{lesson.id}/complete").status_code == 200
    route_id = db.scalar(select(Module.route_id).where(Module.id == lesson.module_id))
    assert as_member.get(f"/api/routes/{route_id}").status_code == 200
    events = _events(db)
    assert [e.name for e in events] == [
        "lesson.viewed",
        "lesson.completed",
        "lesson.uncompleted",
        "route.viewed",
    ]
    for event in events:
        assert event.user_id == seeded["member_id"]
        assert event.academy_id == seeded["academy_id"]
        assert event.source == "server" and event.session_id is None
    assert [(e.subject_type, e.subject_id) for e in events[:3]] == [("lesson", lesson.id)] * 3
    assert (events[3].subject_type, events[3].subject_id) == ("route", route_id)


def test_community_actions_are_captured(
    as_member: TestClient, db: Session, seeded: dict, tracking: None
) -> None:
    channel_id = seeded["channel_id"]
    post = _post(db)
    assert as_member.post(f"/api/channels/{channel_id}/posts", data={"body": "Hola"}).status_code == 201
    assert as_member.post(f"/api/posts/{post.id}/comments", json={"body": "Bien"}).status_code == 201
    assert as_member.put(f"/api/posts/{post.id}/reactions/fire").status_code == 200
    assert as_member.delete(f"/api/posts/{post.id}/reactions/fire").status_code == 200
    created, comment, added, removed = _events(db)
    channel = db.get(Channel, channel_id)
    assert (created.name, created.subject_type, created.subject_id) == ("post.created", "channel", channel_id)
    assert created.academy_id == channel.academy_id
    assert (comment.name, comment.subject_type, comment.subject_id) == ("comment.created", "post", post.id)
    assert (added.name, added.properties) == ("reaction.added", {"kind": "fire"})
    assert (removed.name, removed.properties) == ("reaction.removed", {"kind": "fire"})
    assert comment.academy_id == db.scalar(select(Channel.academy_id).where(Channel.id == post.channel_id))


def test_club_events_resolve_the_slug(
    as_member: TestClient, db: Session, seeded: dict, tracking: None
) -> None:
    assert as_member.get("/api/academies/upiixia/home").status_code == 200
    assert as_member.delete("/api/academies/upiixia/enroll").status_code == 200
    assert as_member.post("/api/academies/upiixia/enroll").status_code == 200
    events = _events(db)
    assert [e.name for e in events] == ["club.viewed", "club.left", "club.joined"]
    assert {(e.subject_type, e.subject_id, e.academy_id) for e in events} == {
        ("academy", seeded["academy_id"], seeded["academy_id"])
    }


def test_login_and_register_name_the_new_user(
    client: TestClient, db: Session, seeded: dict, tracking: None
) -> None:
    login = client.post("/api/auth/login", json={"email": "alumno.demo@upiixsol.dev", "password": "admin123"})
    assert login.status_code == 200
    register = client.post(
        "/api/auth/register",
        json={
            "full_name": "Ana López Pérez",
            "boleta": "2026123456",
            "email": "ana.lopez@alumno.ipn.mx",
            "password": "segura-123",
            "accept_privacy": True,
        },
    )
    assert register.status_code == 201
    logged, registered = _events(db)
    assert (logged.name, logged.user_id) == ("auth.login", seeded["member_id"])
    new_user = db.scalar(select(User.id).where(User.email == "ana.lopez@alumno.ipn.mx"))
    assert (registered.name, registered.user_id) == ("auth.registered", new_user)
    assert logged.properties == {} and registered.properties == {}


def test_failed_and_unmapped_requests_write_nothing(
    as_member: TestClient, client: TestClient, db: Session, seeded: dict, tracking: None
) -> None:
    assert as_member.post("/api/lessons/999999/complete").status_code == 404
    assert as_member.post("/api/academies/no-existe/enroll").status_code == 404
    assert (
        client.post(
            "/api/auth/login", json={"email": "alumno.demo@upiixsol.dev", "password": "mala"}
        ).status_code
        == 401
    )
    assert as_member.put(f"/api/posts/{_post(db).id}/reactions/nope").status_code == 422
    assert as_member.get("/api/health").status_code == 200
    assert as_member.get("/api/academies").status_code == 200
    assert as_member.get("/api/no-existe").status_code == 404
    assert _events(db) == []


def test_disabled_flag_skips_capture(
    as_member: TestClient, db: Session, seeded: dict, monkeypatch: pytest.MonkeyPatch, engine: Engine
) -> None:
    monkeypatch.setattr(service, "session_factory", sessionmaker(bind=engine))
    monkeypatch.setattr(
        service, "get_analytics_settings", lambda: service.AnalyticsSettings(analytics_enabled=False)
    )
    assert as_member.post("/api/academies/upiixia/enroll").status_code == 200
    assert _events(db) == []


def test_writer_failure_never_breaks_the_response(
    as_member: TestClient,
    db: Session,
    seeded: dict,
    tracking: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def broken() -> Session:
        raise RuntimeError("database down")

    monkeypatch.setattr(service, "session_factory", broken)
    with caplog.at_level(logging.ERROR, logger="app.analytics"):
        response = as_member.post("/api/academies/upiixia/enroll")
    assert response.status_code == 200 and response.json()["enrolled"] is True
    assert "could not record club.joined" in caplog.text
    assert _events(db) == []


def test_capture_failure_never_breaks_the_response(
    as_member: TestClient,
    db: Session,
    seeded: dict,
    tracking: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def explode(*_args: object) -> None:
        raise RuntimeError("bug")

    monkeypatch.setattr(service, "attach", explode)
    with caplog.at_level(logging.ERROR, logger="app.analytics"):
        response = as_member.post("/api/academies/upiixia/enroll")
    assert response.status_code == 200
    assert "could not schedule POST /api/academies/upiixia/enroll" in caplog.text


# ── Helpers ─────────────────────────────────────────────────


def test_attach_runs_after_existing_background() -> None:
    calls: list[str] = []
    response = JSONResponse({}, background=BackgroundTask(calls.append, "first"))
    service.attach(response, BackgroundTask(calls.append, "second"))
    anyio.run(response.background)
    assert calls == ["first", "second"]


def test_refresh_cookie_parsing() -> None:
    response = JSONResponse({})
    assert service._refresh_cookie(response) is None
    response.raw_headers.append((b"set-cookie", b'bad"cookie=\x00;;'))
    response.set_cookie("other", "1")
    response.set_cookie(service.REFRESH_COOKIE, "abc")
    assert service._refresh_cookie(response) == "abc"


def test_server_row_edge_cases(db: Session, seeded: dict) -> None:
    spec = service.SERVER_EVENTS[("GET", "/api/lessons/{lesson_id}")]
    for raw in ("abc", str(2**40)):
        row = service._server_row(db, service.PendingEvent(spec, utcnow(), None, {"lesson_id": raw}))
        assert (row.subject_type, row.subject_id, row.academy_id) == (None, None, None)
    login = service.SERVER_EVENTS[("POST", "/api/auth/login")]
    row = service._server_row(db, service.PendingEvent(login, utcnow(), None, {}, refresh_token="unknown"))
    assert row.user_id is None


def test_academy_of_every_subject(db: Session, seeded: dict) -> None:
    academy_id = seeded["academy_id"]
    lesson = _lesson(db, academy_id)
    resource = db.scalar(select(Resource).where(Resource.academy_id == academy_id))
    channel = db.scalar(select(Channel).where(Channel.academy_id == academy_id))
    post = Post(channel_id=channel.id, author_id=seeded["member_id"], body="x")
    db.add(post)
    db.flush()
    route_id = db.scalar(select(Module.route_id).where(Module.id == lesson.module_id))
    assert service.academy_of(db, "lesson", lesson.id) == academy_id
    assert service.academy_of(db, "route", route_id) == academy_id
    assert service.academy_of(db, "resource", resource.id) == academy_id
    assert service.academy_of(db, "channel", channel.id) == academy_id
    assert service.academy_of(db, "post", post.id) == academy_id
    assert service.academy_of(db, "academy", academy_id) == academy_id
    assert service.academy_of(db, "project", 1) is None
    assert service.academy_of(db, None, 1) is None
    assert service.academy_of(db, "lesson", None) is None


def test_events_survive_deleting_the_user_and_club(db: Session, seeded: dict) -> None:
    academy = db.get(Academy, seeded["academy_id"])
    user = db.get(User, seeded["member_id"])
    db.add(
        ActivityEvent(name="page.view", user_id=user.id, academy_id=academy.id, source="web", properties={})
    )
    db.flush()
    db.delete(user)
    db.delete(academy)
    db.flush()
    event = _events(db)[0]
    assert (event.user_id, event.academy_id, event.name) == (None, None, "page.view")
    assert event.id >= 1 and event.occurred_at.tzinfo is not None
