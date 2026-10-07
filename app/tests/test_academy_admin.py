import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Academy, Enrollment, LearningRoute, Lesson, LessonLink, LessonProgress, Module, Role
from app.tests.conftest import auth_headers, make_academy, make_user

VIDEO = "https://youtu.be/dQw4w9WgXcQ"


@pytest.fixture
def ia(seeded: dict, db: Session) -> Academy:
    return db.get(Academy, seeded["academy_id"])


@pytest.fixture
def route(ia: Academy, db: Session) -> LearningRoute:
    return db.scalar(select(LearningRoute).where(LearningRoute.academy_id == ia.id))


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


# ── Scope ────────────────────────────────────────────────────


def test_admin_ia_cannot_patch_other_academy_403(as_admin_ia: TestClient, db: Session) -> None:
    other = make_academy(db, "robotica", "UpiixRobótica")
    robo_route = LearningRoute(academy_id=other.id, title="Robots")
    db.add(robo_route)
    db.flush()
    module = Module(route_id=robo_route.id, title="M")
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="L", youtube_url=VIDEO, youtube_video_id="dQw4w9WgXcQ")
    db.add(lesson)
    db.flush()
    attempts = [
        as_admin_ia.patch(f"/api/academies/{other.id}/branding", json={"color_accent": "#000000"}),
        as_admin_ia.get(f"/api/academies/{other.id}/content"),
        as_admin_ia.post(f"/api/academies/{other.id}/routes", json={"title": "x"}),
        as_admin_ia.patch(f"/api/routes/{robo_route.id}", json={"title": "x"}),
        as_admin_ia.delete(f"/api/routes/{robo_route.id}"),
        as_admin_ia.post(f"/api/academies/{other.id}/routes/{robo_route.id}/modules", json={"title": "x"}),
        as_admin_ia.patch(f"/api/modules/{module.id}", json={"title": "x"}),
        as_admin_ia.post(f"/api/modules/{module.id}/lessons", json={"title": "x", "youtube_url": VIDEO}),
        as_admin_ia.patch(f"/api/lessons/{lesson.id}", json={"title": "x"}),
        as_admin_ia.delete(f"/api/lessons/{lesson.id}"),
        as_admin_ia.put(f"/api/modules/{module.id}/lessons/order", json={"ids": [lesson.id]}),
        as_admin_ia.get(f"/api/academies/{other.id}/enrollments"),
        as_admin_ia.post(f"/api/academies/{other.id}/logo", files={"file": ("l.png", _png(), "image/png")}),
    ]
    assert [r.status_code for r in attempts] == [403] * len(attempts)
    assert db.get(LearningRoute, robo_route.id).title == "Robots"


def test_members_and_anonymous_cannot_manage(as_member: TestClient, client: TestClient, ia: Academy) -> None:
    assert (
        as_member.patch(f"/api/academies/{ia.id}/branding", json={"color_accent": "#000000"}).status_code
        == 403
    )
    assert as_member.get(f"/api/academies/{ia.id}/content").status_code == 403
    assert client.get(f"/api/academies/{ia.id}/content").status_code == 401


def test_superadmin_can_manage_any_academy(as_superadmin: TestClient, ia: Academy) -> None:
    assert (
        as_superadmin.patch(f"/api/academies/{ia.id}/branding", json={"color_accent": "#123456"}).status_code
        == 200
    )


def test_unknown_ids_are_404(as_admin_ia: TestClient) -> None:
    assert as_admin_ia.get("/api/academies/9999/content").status_code == 404
    assert as_admin_ia.patch("/api/routes/9999", json={"title": "x"}).status_code == 404
    assert as_admin_ia.patch("/api/modules/9999", json={"title": "x"}).status_code == 404
    assert as_admin_ia.patch("/api/lessons/9999", json={"title": "x"}).status_code == 404


# ── Branding ─────────────────────────────────────────────────


def test_branding_updates_colors_and_texts(as_admin_ia: TestClient, ia: Academy) -> None:
    response = as_admin_ia.patch(
        f"/api/academies/{ia.id}/branding",
        json={"color_accent": "#f28034", "welcome_text": "Hola <script>alert(1)</script>**IA**"},
    )
    body = response.json()
    assert response.status_code == 200 and body["color_accent"] == "#F28034"
    assert "<script" not in body["welcome_text"] and "**IA**" in body["welcome_text"]
    assert body["color_primary"] == "#00BF63"  # untouched
    assert (
        as_admin_ia.patch(f"/api/academies/{ia.id}/branding", json={"color_accent": "naranja"}).status_code
        == 422
    )
    assert as_admin_ia.patch(f"/api/academies/{ia.id}/branding", json={"name": "Otro"}).status_code == 422


def test_logo_and_mascot_upload(as_admin_ia: TestClient, ia: Academy) -> None:
    logo = as_admin_ia.post(f"/api/academies/{ia.id}/logo", files={"file": ("logo.png", _png(), "image/png")})
    assert logo.status_code == 200 and logo.json()["logo_url"].startswith("/media/logo/")
    mascot = as_admin_ia.post(
        f"/api/academies/{ia.id}/mascot", files={"file": ("m.png", _png(), "image/png")}
    )
    assert mascot.json()["mascot_url"].startswith("/media/mascot/")
    bad = as_admin_ia.post(f"/api/academies/{ia.id}/logo", files={"file": ("x.png", b"nope", "image/png")})
    assert bad.status_code == 422


# ── Content tree ─────────────────────────────────────────────


def test_content_tree_includes_drafts_and_links(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    lesson = db.scalars(select(Lesson)).first()
    lesson.is_published = False
    db.flush()
    tree = as_admin_ia.get(f"/api/academies/{ia.id}/content").json()
    route = tree["routes"][0]
    assert route["title"] == "Fundamentos de IA con Python"
    lessons = [item for m in route["modules"] for item in m["lessons"]]
    assert len(lessons) == 4 and any(not item["is_published"] for item in lessons)
    assert lessons[0]["youtube_url"].startswith("https://www.youtube.com/") and "links" in lessons[0]


def test_step5_add_module_and_lesson_appears_in_player(
    as_admin_ia: TestClient, as_member: TestClient, ia: Academy, route: LearningRoute
) -> None:
    module = as_admin_ia.post(
        f"/api/academies/{ia.id}/routes/{route.id}/modules", json={"title": "Proyecto final"}
    )
    assert module.status_code == 201 and module.json()["position"] == 2
    lesson = as_admin_ia.post(
        f"/api/modules/{module.json()['id']}/lessons",
        json={
            "title": "Tu primer modelo",
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s",
            "description": "Entrena un modelo. <img src=x onerror=alert(1)>",
            "duration_min": 20,
            "is_published": True,
            "links": [
                {"label": "Notebook", "url": "https://colab.research.google.com"},
                {"label": "Dataset", "url": "https://scikit-learn.org"},
            ],
        },
    )
    assert lesson.status_code == 201
    body = lesson.json()
    assert body["youtube_video_id"] == "dQw4w9WgXcQ" and len(body["links"]) == 2
    assert "onerror" not in body["description"]

    detail = as_member.get(f"/api/routes/{route.id}").json()
    assert detail["modules"][-1]["title"] == "Proyecto final"
    assert detail["modules"][-1]["lessons"][0]["title"] == "Tu primer modelo"
    assert detail["progress"]["total"] == 5


def test_invalid_youtube_url_is_422(as_admin_ia: TestClient, route: LearningRoute, db: Session) -> None:
    module = db.scalars(select(Module).where(Module.route_id == route.id)).first()
    response = as_admin_ia.post(
        f"/api/modules/{module.id}/lessons", json={"title": "x", "youtube_url": "https://vimeo.com/1"}
    )
    assert response.status_code == 422 and "YouTube" in response.json()["error"]["message"]
    lesson = db.scalars(select(Lesson)).first()
    assert (
        as_admin_ia.patch(
            f"/api/lessons/{lesson.id}", json={"youtube_url": "javascript:alert(1)"}
        ).status_code
        == 422
    )
    bad_link = as_admin_ia.patch(
        f"/api/lessons/{lesson.id}", json={"links": [{"label": "x", "url": "ftp://x"}]}
    )
    assert bad_link.status_code == 422


def test_update_lesson_replaces_links_and_video(as_admin_ia: TestClient, db: Session) -> None:
    lesson = db.scalars(select(Lesson)).first()
    body = as_admin_ia.patch(
        f"/api/lessons/{lesson.id}",
        json={
            "youtube_url": "https://youtu.be/aircAruvnKk",
            "links": [{"label": "Solo uno", "url": "https://a.mx"}],
            "is_published": False,
            "title": "Nuevo título",
            "description": "**hola**",
            "duration_min": 12,
        },
    ).json()
    assert body["youtube_video_id"] == "aircAruvnKk" and [link["label"] for link in body["links"]] == [
        "Solo uno"
    ]
    assert body["is_published"] is False and body["title"] == "Nuevo título" and body["duration_min"] == 12
    assert (
        db.scalar(
            select(LessonLink).where(
                LessonLink.label == "Tutorial oficial de Python", LessonLink.lesson_id == lesson.id
            )
        )
        is None
    )


def test_routes_crud_and_publish(as_admin_ia: TestClient, ia: Academy, as_member: TestClient) -> None:
    created = as_admin_ia.post(f"/api/academies/{ia.id}/routes", json={"title": "Visión por computadora"})
    assert (
        created.status_code == 201
        and created.json()["is_published"] is False
        and created.json()["position"] == 1
    )
    rid = created.json()["id"]
    assert as_member.get(f"/api/routes/{rid}").status_code == 404
    patched = as_admin_ia.patch(f"/api/routes/{rid}", json={"is_published": True, "description": "Imágenes"})
    assert patched.json()["is_published"] is True and patched.json()["description"] == "Imágenes"
    assert as_member.get(f"/api/routes/{rid}").status_code == 200
    assert as_admin_ia.delete(f"/api/routes/{rid}").status_code == 204
    assert as_member.get(f"/api/routes/{rid}").status_code == 404


def test_module_rename_and_delete_cascades(
    as_admin_ia: TestClient, route: LearningRoute, db: Session, seeded: dict
) -> None:
    module = db.scalars(select(Module).where(Module.route_id == route.id).order_by(Module.position)).first()
    assert (
        as_admin_ia.patch(f"/api/modules/{module.id}", json={"title": "Python básico"}).json()["title"]
        == "Python básico"
    )
    lesson_ids = [lesson.id for lesson in db.scalars(select(Lesson).where(Lesson.module_id == module.id))]
    assert as_admin_ia.delete(f"/api/modules/{module.id}").status_code == 204
    db.expire_all()
    assert db.scalar(select(Lesson).where(Lesson.id.in_(lesson_ids))) is None
    assert db.get(LessonProgress, (seeded["member_id"], lesson_ids[0])) is None


def test_delete_lesson(as_admin_ia: TestClient, db: Session) -> None:
    lesson = db.scalars(select(Lesson)).first()
    assert as_admin_ia.delete(f"/api/lessons/{lesson.id}").status_code == 204
    db.expire_all()
    assert db.get(Lesson, lesson.id) is None


def test_reorder_routes_modules_and_lessons(
    as_admin_ia: TestClient, ia: Academy, route: LearningRoute, db: Session
) -> None:
    modules = list(db.scalars(select(Module).where(Module.route_id == route.id).order_by(Module.position)))
    reversed_ids = [m.id for m in reversed(modules)]
    assert (
        as_admin_ia.put(f"/api/routes/{route.id}/modules/order", json={"ids": reversed_ids}).status_code
        == 200
    )
    db.expire_all()
    assert [
        m.id for m in db.scalars(select(Module).where(Module.route_id == route.id).order_by(Module.position))
    ] == reversed_ids

    lessons = list(
        db.scalars(select(Lesson).where(Lesson.module_id == modules[0].id).order_by(Lesson.position))
    )
    new_order = [lessons[1].id, lessons[0].id]
    assert (
        as_admin_ia.put(f"/api/modules/{modules[0].id}/lessons/order", json={"ids": new_order}).status_code
        == 200
    )
    db.expire_all()
    assert [
        lesson.id
        for lesson in db.scalars(
            select(Lesson).where(Lesson.module_id == modules[0].id).order_by(Lesson.position)
        )
    ] == new_order

    other = as_admin_ia.post(f"/api/academies/{ia.id}/routes", json={"title": "Otra"}).json()["id"]
    assert (
        as_admin_ia.put(f"/api/academies/{ia.id}/routes/order", json={"ids": [other, route.id]}).status_code
        == 200
    )
    # ids must be exactly the siblings (no foreign or missing ids)
    assert (
        as_admin_ia.put(f"/api/routes/{route.id}/modules/order", json={"ids": [reversed_ids[0]]}).status_code
        == 422
    )
    assert (
        as_admin_ia.put(
            f"/api/modules/{modules[0].id}/lessons/order", json={"ids": [*new_order, 9999]}
        ).status_code
        == 422
    )


def test_module_must_belong_to_route_of_academy(
    as_admin_ia: TestClient, as_superadmin: TestClient, ia: Academy, db: Session
) -> None:
    other = make_academy(db, "robotica", "UpiixRobótica")
    foreign = LearningRoute(academy_id=other.id, title="Robots")
    db.add(foreign)
    db.flush()
    path = f"/api/academies/{ia.id}/routes/{foreign.id}/modules"
    # The admin of IA cannot reach another academy's route through IA's URL (scope check on the route).
    assert as_admin_ia.post(path, json={"title": "x"}).status_code == 403
    # A superadmin passes the scope, but the route is not IA's: 404, never a cross-academy write.
    assert as_superadmin.post(path, json={"title": "x"}).status_code == 404


# ── Enrollments ──────────────────────────────────────────────


def test_enrollments_list_enroll_by_boleta_and_remove(
    as_admin_ia: TestClient, ia: Academy, db: Session
) -> None:
    page = as_admin_ia.get(f"/api/academies/{ia.id}/enrollments").json()
    assert [e["email"] for e in page["items"]] == ["alumno.demo@upiixsol.dev"]
    assert page["items"][0]["boleta"] == "2026000001"  # admins see boleta of their enrollees

    newcomer = make_user(db, email="nuevo@ipn.mx", boleta="2026000555")
    added = as_admin_ia.post(f"/api/academies/{ia.id}/enrollments", json={"boleta": "2026000555"})
    assert added.status_code == 201 and added.json()["user_id"] == newcomer.id
    assert (
        as_admin_ia.post(f"/api/academies/{ia.id}/enrollments", json={"boleta": "2026000555"}).status_code
        == 201
    )
    assert (
        as_admin_ia.post(f"/api/academies/{ia.id}/enrollments", json={"boleta": "2026999999"}).status_code
        == 404
    )
    assert as_admin_ia.delete(f"/api/academies/{ia.id}/enrollments/{newcomer.id}").status_code == 204
    assert db.get(Enrollment, (newcomer.id, ia.id)) is None
    assert as_admin_ia.delete(f"/api/academies/{ia.id}/enrollments/{newcomer.id}").status_code == 204


def test_enrollments_paginate(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    for i in range(3):
        user = make_user(db, email=f"m{i}@ipn.mx", boleta=f"20260011{i:02d}")
        db.add(Enrollment(user_id=user.id, academy_id=ia.id))
    db.flush()
    first = as_admin_ia.get(f"/api/academies/{ia.id}/enrollments?limit=2").json()
    second = as_admin_ia.get(
        f"/api/academies/{ia.id}/enrollments?limit=2&cursor={first['next_cursor']}"
    ).json()
    assert len(first["items"]) == 2 and len(second["items"]) == 2 and second["next_cursor"] is None


def test_admin_cannot_enroll_staff(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    make_user(db, role=Role.academy_admin, email="otro.admin@ipn.mx", boleta="2026000444")
    assert (
        as_admin_ia.post(f"/api/academies/{ia.id}/enrollments", json={"boleta": "2026000444"}).status_code
        == 404
    )


def test_superadmin_sees_inactive_academy_content(
    as_superadmin: TestClient, ia: Academy, db: Session
) -> None:
    ia.is_active = False
    db.flush()
    assert as_superadmin.get(f"/api/academies/{ia.id}/content").status_code == 200


def test_admin_headers_helper_unused_guard(client: TestClient, db: Session, ia: Academy) -> None:
    """An academy_admin without academy (data error) can't manage anything."""
    orphan = make_user(db, role=Role.academy_admin, email="huerfano@upiixsol.dev")
    assert client.get(f"/api/academies/{ia.id}/content", headers=auth_headers(orphan)).status_code == 403


def test_partial_updates_keep_untouched_fields(
    as_admin_ia: TestClient, ia: Academy, route: LearningRoute, db: Session
) -> None:
    ia.color_accent_2 = "#B4422F"
    db.flush()
    body = as_admin_ia.patch(
        f"/api/academies/{ia.id}/branding", json={"color_primary": None, "color_accent_2": None}
    ).json()
    assert body["color_primary"] == "#00BF63"  # null on a required color is ignored
    assert body["color_accent_2"] is None  # the optional accent can be cleared

    renamed = as_admin_ia.patch(f"/api/routes/{route.id}", json={"title": "Fundamentos de IA"}).json()
    assert renamed["title"] == "Fundamentos de IA" and renamed["description"].startswith("Ruta de inicio")

    lesson = db.scalars(select(Lesson)).first()
    before = (lesson.youtube_video_id, lesson.description)
    updated = as_admin_ia.patch(
        f"/api/lessons/{lesson.id}", json={"title": "Solo título", "duration_min": None, "description": None}
    ).json()
    assert updated["title"] == "Solo título" and updated["duration_min"] is None
    assert updated["youtube_video_id"] == before[0] and updated["description"] == before[1]
    assert len(updated["links"]) == 1  # links untouched when not sent
