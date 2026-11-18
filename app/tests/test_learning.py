from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Academy, LearningRoute, Lesson, LessonProgress, Module, Role
from app.tests.conftest import auth_headers, make_academy, make_user


def _route(db: Session) -> LearningRoute:
    return db.scalar(select(LearningRoute).where(LearningRoute.title == "Fundamentos de IA con Python"))


def _lessons(db: Session) -> list[Lesson]:
    return list(db.scalars(select(Lesson).join(Module).order_by(Module.position, Lesson.position)))


def test_routes_of_academy_with_progress(as_member: TestClient) -> None:
    page = as_member.get("/api/academies/upiixia/routes").json()
    assert [r["title"] for r in page["items"]] == ["Fundamentos de IA con Python"]
    assert page["items"][0]["progress"]["percent"] == 50 and page["next_cursor"] is None
    assert as_member.get("/api/academies/no-existe/routes").status_code == 404


def test_route_detail_has_modules_counts_and_completion(as_member: TestClient, db: Session) -> None:
    body = as_member.get(f"/api/routes/{_route(db).id}").json()
    assert body["progress"] == {
        "completed": 2,
        "total": 4,
        "percent": 50,
        "next_lesson_id": _lessons(db)[2].id,
    }
    assert [(m["title"], m["completed"], m["total"]) for m in body["modules"]] == [
        ("Python para IA", 2, 2),
        ("Redes neuronales", 0, 2),
    ]
    first = body["modules"][0]["lessons"][0]
    assert first["completed"] is True and first["title"] == "Python desde cero"


def test_lesson_detail_embed_links_prev_next_and_marks_viewed(
    as_member: TestClient, db: Session, seeded: dict
) -> None:
    lessons = _lessons(db)
    third = lessons[2]
    body = as_member.get(f"/api/lessons/{third.id}").json()
    assert body["embed_url"] == "https://www.youtube-nocookie.com/embed/aircAruvnKk"
    assert body["thumbnail_url"] == "https://img.youtube.com/vi/aircAruvnKk/hqdefault.jpg"
    assert (body["prev_lesson_id"], body["next_lesson_id"]) == (lessons[1].id, lessons[3].id)
    assert body["academy_slug"] == "upiixia" and body["route_id"] == _route(db).id
    assert len(body["links"]) == 2 and body["completed"] is False
    assert "<script" not in body["description"]
    row = db.get(LessonProgress, (seeded["member_id"], third.id))
    assert row is not None and row.last_viewed_at is not None and row.completed_at is None

    edges = [as_member.get(f"/api/lessons/{lesson.id}").json() for lesson in (lessons[0], lessons[-1])]
    assert edges[0]["prev_lesson_id"] is None and edges[1]["next_lesson_id"] is None


def test_complete_lesson_moves_progress_50_to_75(as_member: TestClient, db: Session) -> None:
    third = _lessons(db)[2]
    response = as_member.post(f"/api/lessons/{third.id}/complete")
    assert response.status_code == 200
    assert response.json()["progress"]["percent"] == 75 and response.json()["completed"] is True
    # Persisted: a fresh read (like a page reload) still says 75 %.
    assert as_member.get(f"/api/routes/{_route(db).id}").json()["progress"]["percent"] == 75
    assert as_member.get("/api/academies/upiixia/home").json()["continue"]["lesson_number"] == 4
    # Idempotent, and there is no undo (UPS-062): it stays at 75 %.
    assert as_member.post(f"/api/lessons/{third.id}/complete").json()["progress"]["percent"] == 75
    assert as_member.delete(f"/api/lessons/{third.id}/complete").status_code == 405
    assert as_member.get(f"/api/routes/{_route(db).id}").json()["progress"]["percent"] == 75


def test_unpublished_content_is_404_for_members_but_visible_to_its_admin(
    as_member: TestClient, client: TestClient, db: Session, seeded: dict
) -> None:
    lesson = _lessons(db)[3]
    lesson.is_published = False
    db.flush()
    assert as_member.get(f"/api/lessons/{lesson.id}").status_code == 404
    assert as_member.post(f"/api/lessons/{lesson.id}/complete").status_code == 404
    detail = as_member.get(f"/api/routes/{_route(db).id}").json()
    assert detail["progress"]["total"] == 3
    assert lesson.id not in [item["id"] for m in detail["modules"] for item in m["lessons"]]
    # prev/next skip unpublished lessons
    assert as_member.get(f"/api/lessons/{_lessons(db)[2].id}").json()["next_lesson_id"] is None

    admin_user = make_user(
        db, role=Role.academy_admin, email="otro.admin@upiixsol.dev", academy_id=seeded["academy_id"]
    )
    preview = client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(admin_user))
    assert preview.status_code == 200 and preview.json()["is_published"] is False


def test_unpublished_route_and_inactive_academy_are_404(
    as_member: TestClient, db: Session, seeded: dict
) -> None:
    route = _route(db)
    route.is_published = False
    db.flush()
    assert as_member.get(f"/api/routes/{route.id}").status_code == 404
    assert as_member.get("/api/academies/upiixia/routes").json()["items"] == []
    route.is_published = True
    db.get(Academy, seeded["academy_id"]).is_active = False
    db.flush()
    assert as_member.get(f"/api/routes/{route.id}").status_code == 404
    assert as_member.get(f"/api/lessons/{_lessons(db)[0].id}").status_code == 404


def test_admin_of_other_academy_cannot_preview_unpublished(
    client: TestClient, db: Session, seeded: dict
) -> None:
    other = make_academy(db, "robotica", "UpiixRobótica")
    stranger = make_user(db, role=Role.academy_admin, email="robo@upiixsol.dev", academy_id=other.id)
    lesson = _lessons(db)[0]
    lesson.is_published = False
    db.flush()
    assert client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(stranger)).status_code == 404


def test_learning_requires_login_and_unknown_ids_are_404(client: TestClient, as_member: TestClient) -> None:
    assert client.get("/api/routes/1").status_code == 401
    assert client.get("/api/lessons/1").status_code == 401
    assert client.post("/api/lessons/1/complete").status_code == 401
    assert as_member.get("/api/routes/999").status_code == 404
    assert as_member.get("/api/lessons/999").status_code == 404
    assert as_member.post("/api/lessons/999/complete").status_code == 404


def test_admin_sees_draft_routes_of_own_academy(as_admin_ia: TestClient, db: Session, seeded: dict) -> None:
    db.add(LearningRoute(academy_id=seeded["academy_id"], title="Borrador", is_published=False, position=5))
    db.flush()
    titles = [r["title"] for r in as_admin_ia.get("/api/academies/upiixia/routes").json()["items"]]
    assert titles == ["Fundamentos de IA con Python", "Borrador"]


def test_lesson_out_exposes_segment(as_member: TestClient, db: Session) -> None:
    """UPS-045: the player gets the segment and an embed that starts and ends there."""
    lesson = _lessons(db)[0]
    plain = as_member.get(f"/api/lessons/{lesson.id}").json()
    assert (plain["start_s"], plain["end_s"]) == (None, None)
    assert "?" not in plain["embed_url"]
    lesson.start_s, lesson.end_s = 850, 1500
    db.flush()
    body = as_member.get(f"/api/lessons/{lesson.id}").json()
    assert (body["start_s"], body["end_s"]) == (850, 1500)
    assert (
        body["embed_url"]
        == f"https://www.youtube-nocookie.com/embed/{lesson.youtube_video_id}?start=850&end=1500"
    )


# ── UPS-062: a completed lesson stays completed ──────────────


def test_uncomplete_endpoint_is_gone(as_member: TestClient, db: Session) -> None:
    third = _lessons(db)[2]
    assert as_member.post(f"/api/lessons/{third.id}/complete").status_code == 200
    assert as_member.delete(f"/api/lessons/{third.id}/complete").status_code == 405
    assert as_member.get(f"/api/lessons/{third.id}").json()["completed"] is True


def test_completed_lesson_stays_completed(as_member: TestClient, db: Session) -> None:
    third = _lessons(db)[2]
    first = as_member.post(f"/api/lessons/{third.id}/complete").json()
    second = as_member.post(f"/api/lessons/{third.id}/complete").json()  # completing twice changes nothing
    assert first == second and second["completed"] is True
    for method in ("DELETE", "PATCH", "PUT"):
        assert as_member.request(method, f"/api/lessons/{third.id}/complete").status_code == 405
    body = as_member.get(f"/api/lessons/{third.id}").json()
    assert body["completed"] is True and body["completed_at"] is not None


def test_progress_never_goes_down(as_member: TestClient, db: Session) -> None:
    route_id = _route(db).id
    seen = [as_member.get(f"/api/routes/{route_id}").json()["progress"]["percent"]]
    for lesson in _lessons(db):
        as_member.post(f"/api/lessons/{lesson.id}/complete")
        as_member.delete(f"/api/lessons/{lesson.id}/complete")  # no way back: 405
        seen.append(as_member.get(f"/api/routes/{route_id}").json()["progress"]["percent"])
    assert seen == sorted(seen) and seen[-1] == 100
