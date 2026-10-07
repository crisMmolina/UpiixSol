from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import Academy, Enrollment, Event, LessonProgress, Post, User
from app.models.common import utcnow
from app.tests.conftest import auth_headers, make_academy, make_user


@pytest.fixture
def ids(seeded: dict) -> dict:
    return seeded


def test_home_requires_login(client: TestClient) -> None:
    assert client.get("/api/home").status_code == 401


def test_home_returns_hero_academies_events_projects_and_activity(as_member: TestClient) -> None:
    body = as_member.get("/api/home").json()
    assert body["hero"]["hero_title"] == "Tu club, tus academias, un solo campus"
    assert [a["slug"] for a in body["academies"]] == ["upiixia"]
    assert body["academies"][0]["is_enrolled"] is True
    assert len(body["upcoming_events"]) == 2
    assert all(e["starts_at"] >= body["upcoming_events"][0]["starts_at"] for e in body["upcoming_events"])
    assert len(body["featured_projects"]) == 2
    activity = body["recent_activity"]
    assert len(activity) == 5 and activity[0]["created_at"] >= activity[-1]["created_at"]
    assert set(activity[0]["author"]) == {"id", "nickname", "avatar_url"}  # never email/boleta
    assert activity[0]["channel_slug"] == "upiixia"


def test_home_hides_inactive_academies_hidden_posts_and_past_events(
    as_member: TestClient, db: Session
) -> None:
    make_academy(db, "inactiva", "Inactiva").is_active = False
    db.scalars(select(Post)).first().is_hidden = True
    db.add(
        Event(title="Pasado", starts_at=utcnow() - timedelta(days=2), ends_at=utcnow() - timedelta(days=1))
    )
    db.flush()
    body = as_member.get("/api/home").json()
    assert [a["slug"] for a in body["academies"]] == ["upiixia"]
    assert len(body["recent_activity"]) == 4
    assert "Pasado" not in [e["title"] for e in body["upcoming_events"]]


def test_list_academies_is_paginated(as_member: TestClient, db: Session) -> None:
    for i in range(3):
        make_academy(db, f"extra-{i}", f"Extra {i}").position = i + 1
    db.flush()
    first = as_member.get("/api/academies?limit=2").json()
    assert [a["slug"] for a in first["items"]] == ["upiixia", "extra-0"] and first["next_cursor"]
    second = as_member.get(f"/api/academies?limit=2&cursor={first['next_cursor']}").json()
    assert [a["slug"] for a in second["items"]] == ["extra-1", "extra-2"] and second["next_cursor"] is None
    assert as_member.get("/api/academies?limit=51").status_code == 422


def test_branding_is_public_and_inactive_is_404(client: TestClient, db: Session, ids: dict) -> None:
    body = client.get("/api/academies/upiixia").json()
    assert body["color_accent"] == "#7ED957" and body["logo_url"] == "/brand/upiixia/wordmark.png"
    assert body["is_enrolled"] is False
    db.get(Academy, ids["academy_id"]).is_active = False
    db.flush()
    assert client.get("/api/academies/upiixia").status_code == 404
    assert client.get("/api/academies/no-existe").status_code == 404


def test_superadmin_can_still_see_inactive_academy(as_superadmin: TestClient, db: Session, ids: dict) -> None:
    db.get(Academy, ids["academy_id"]).is_active = False
    db.flush()
    assert as_superadmin.get("/api/academies/upiixia").status_code == 200
    assert as_superadmin.get("/api/academies/upiixia/home").status_code == 200


def test_academy_home_continue_shows_lesson3_50pct(as_member: TestClient) -> None:
    body = as_member.get("/api/academies/upiixia/home").json()
    assert body["academy"]["name"] == "UpiixIA" and body["is_enrolled"] is True
    assert body["continue"]["lesson_number"] == 3 and body["continue"]["percent"] == 50
    assert body["continue"]["lesson_title"] == "¿Qué es una red neuronal?"
    route = body["routes"][0]
    assert route["title"] == "Fundamentos de IA con Python"
    assert route["progress"] == {
        "completed": 2,
        "total": 4,
        "percent": 50,
        "next_lesson_id": body["continue"]["lesson_id"],
    }
    assert len(body["recent_resources"]) == 3
    assert len(body["latest_posts"]) == 5
    assert {e["title"] for e in body["upcoming_events"]} == {
        "Taller: tu primera red neuronal",
        "Noche de proyectos UpiixSol",
    }


def test_academy_home_hides_unpublished_routes_from_members(
    as_member: TestClient, db: Session, ids: dict
) -> None:
    from app.models import LearningRoute

    db.add(LearningRoute(academy_id=ids["academy_id"], title="Borrador", is_published=False))
    db.flush()
    titles = [r["title"] for r in as_member.get("/api/academies/upiixia/home").json()["routes"]]
    assert titles == ["Fundamentos de IA con Python"]


def test_academy_home_for_new_member_starts_at_lesson_1(client: TestClient, db: Session, ids: dict) -> None:
    newcomer = make_user(db, email="nuevo@ipn.mx", boleta="2026000777")
    body = client.get("/api/academies/upiixia/home", headers=auth_headers(newcomer)).json()
    assert body["is_enrolled"] is False
    assert (body["continue"]["lesson_number"], body["continue"]["percent"]) == (1, 0)


def test_academy_home_without_routes(client: TestClient, db: Session) -> None:
    make_academy(db, "vacia", "Vacía")
    user = make_user(db, email="x@ipn.mx")
    body = client.get("/api/academies/vacia/home", headers=auth_headers(user)).json()
    assert body["continue"] is None and body["routes"] == [] and body["latest_posts"] == []


def test_academy_home_requires_login_and_404s(client: TestClient, as_member: TestClient) -> None:
    assert client.get("/api/academies/upiixia/home").status_code == 401
    assert as_member.get("/api/academies/no-existe/home").status_code == 404


def test_enroll_is_idempotent_and_unenroll(client: TestClient, db: Session, ids: dict) -> None:
    user = make_user(db, email="nuevo@ipn.mx")
    headers = auth_headers(user)
    for _ in range(2):
        response = client.post("/api/academies/upiixia/enroll", headers=headers)
        assert response.status_code == 200 and response.json() == {"enrolled": True}
    assert db.get(Enrollment, (user.id, ids["academy_id"])) is not None
    assert client.delete("/api/academies/upiixia/enroll", headers=headers).json() == {"enrolled": False}
    assert client.delete("/api/academies/upiixia/enroll", headers=headers).json() == {"enrolled": False}
    assert client.post("/api/academies/no-existe/enroll", headers=headers).status_code == 404
    assert client.post("/api/academies/upiixia/enroll").status_code == 401


def test_academy_home_has_no_n_plus_one(as_member: TestClient, db: Session, ids: dict) -> None:
    """Adding more posts/routes/resources must not add queries."""
    engine = db.get_bind()
    statements: list[str] = []

    def count(*_args, **_kwargs) -> None:
        statements.append("q")

    event.listen(engine, "before_cursor_execute", count)
    try:
        as_member.get("/api/academies/upiixia/home")
        baseline = len(statements)
        channel_id = ids["channel_id"]
        author = db.get(User, ids["admin_ia_id"])
        for i in range(10):
            db.add(Post(channel_id=channel_id, author_id=author.id, body=f"extra {i}"))
        db.flush()
        statements.clear()
        as_member.get("/api/academies/upiixia/home")
        assert len(statements) == baseline
    finally:
        event.remove(engine, "before_cursor_execute", count)


def test_last_viewed_lesson_drives_continue(as_member: TestClient, db: Session, ids: dict) -> None:
    row = db.scalars(select(LessonProgress).where(LessonProgress.user_id == ids["member_id"])).first()
    row.last_viewed_at = utcnow() + timedelta(minutes=1)
    db.flush()
    assert as_member.get("/api/academies/upiixia/home").json()["continue"]["lesson_number"] == 3


def test_posts_carry_comment_and_reaction_counts(as_member: TestClient, db: Session, ids: dict) -> None:
    from app.models import Comment, Reaction

    post = db.scalars(select(Post).order_by(Post.created_at.desc())).first()
    db.add_all(
        [
            Comment(post_id=post.id, author_id=ids["member_id"], body="¡Bien!"),
            Comment(post_id=post.id, author_id=ids["member_id"], body="oculto", is_hidden=True),
            Reaction(post_id=post.id, user_id=ids["member_id"], kind="like"),
            Reaction(post_id=post.id, user_id=ids["admin_ia_id"], kind="like"),
            Reaction(post_id=post.id, user_id=ids["admin_ia_id"], kind="fire"),
        ]
    )
    db.flush()
    latest = as_member.get("/api/academies/upiixia/home").json()["latest_posts"][0]
    assert latest["id"] == post.id
    assert latest["comment_count"] == 1 and latest["reactions"] == {"like": 2, "fire": 1}


def test_home_without_home_content_or_unpublished_featured(client: TestClient, db: Session) -> None:
    from app.models import HomeContent, Project, ProjectStatus

    make_academy(db)
    draft = Project(title="Borrador", slug="borrador", status=ProjectStatus.draft)
    db.add(draft)
    db.flush()
    user = make_user(db, email="x@ipn.mx")
    body = client.get("/api/home", headers=auth_headers(user)).json()
    assert body["hero"] is None and body["featured_projects"] == [] and body["recent_activity"] == []
    db.add(HomeContent(id=1, hero_title="Hola", featured_project_ids=[draft.id]))
    db.flush()
    assert client.get("/api/home", headers=auth_headers(user)).json()["featured_projects"] == []


def test_api_datetimes_carry_utc_offset(as_member: TestClient) -> None:
    """Regression: SQLite gave naive datetimes; browsers read them as local time ("dentro de 5 horas")."""
    body = as_member.get("/api/home").json()
    stamps = [p["created_at"] for p in body["recent_activity"]] + [
        e["starts_at"] for e in body["upcoming_events"]
    ]
    assert stamps and all(s.endswith(("Z", "+00:00")) for s in stamps)


def test_seeded_events_are_at_club_local_time(as_member: TestClient) -> None:
    from datetime import datetime

    from app.seed import CLUB_TZ

    events = as_member.get("/api/home").json()["upcoming_events"]
    local_hours = {datetime.fromisoformat(e["starts_at"]).astimezone(CLUB_TZ).hour for e in events}
    assert local_hours == {17, 18}
