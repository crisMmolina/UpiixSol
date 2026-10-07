import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Academy, Channel, ChannelType, HomeContent, RefreshToken, Role, User
from app.security import verify_password
from app.tests.conftest import auth_headers, make_user

NEW_ACADEMY = {
    "slug": "upiixrobotica",
    "name": "UpiixRobótica",
    "short_description": "Robots y electrónica.",
    "color_primary": "#00BF63",
    "color_secondary": "#04944F",
    "color_accent": "#F28034",
    "position": 2,
}


# ── Access ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/admin/academies"),
        ("post", "/api/admin/academies"),
        ("patch", "/api/admin/academies/1"),
        ("get", "/api/admin/users"),
        ("post", "/api/admin/users"),
        ("patch", "/api/admin/users/1"),
        ("post", "/api/admin/users/1/reset-password"),
        ("get", "/api/admin/home"),
        ("put", "/api/admin/home"),
    ],
)
def test_only_superadmin(
    client: TestClient, as_member: TestClient, as_admin_ia: TestClient, method: str, path: str
) -> None:
    assert getattr(client, method)(path).status_code == 401
    assert getattr(as_member, method)(path, **({"json": {}} if method != "get" else {})).status_code == 403
    assert getattr(as_admin_ia, method)(path, **({"json": {}} if method != "get" else {})).status_code == 403


# ── Academies ────────────────────────────────────────────────


def test_create_academy_creates_channel(
    as_superadmin: TestClient, as_member: TestClient, db: Session
) -> None:
    response = as_superadmin.post("/api/admin/academies", json=NEW_ACADEMY)
    assert response.status_code == 201
    academy = response.json()
    assert academy["slug"] == "upiixrobotica" and academy["is_active"] is True
    channel = db.scalar(select(Channel).where(Channel.academy_id == academy["id"]))
    assert channel is not None and channel.slug == "upiixrobotica" and channel.type == ChannelType.academy
    # Appears on the campus home for members right away (flow step 6).
    slugs = [a["slug"] for a in as_member.get("/api/home").json()["academies"]]
    assert slugs == ["upiixia", "upiixrobotica"]


@pytest.mark.parametrize("slug", ["upiixia", "feed", "general"])
def test_create_academy_rejects_taken_or_reserved_slugs(as_superadmin: TestClient, slug: str) -> None:
    assert as_superadmin.post("/api/admin/academies", json={**NEW_ACADEMY, "slug": slug}).status_code == 409


def test_create_academy_validates_input(as_superadmin: TestClient) -> None:
    assert (
        as_superadmin.post("/api/admin/academies", json={**NEW_ACADEMY, "slug": "Con Espacios"}).status_code
        == 422
    )
    assert (
        as_superadmin.post("/api/admin/academies", json={**NEW_ACADEMY, "color_accent": "rojo"}).status_code
        == 422
    )


def test_list_academies_includes_inactive_and_paginates(as_superadmin: TestClient, db: Session) -> None:
    for i in range(3):
        db.add(Academy(slug=f"a{i}", name=f"A{i}", position=i + 1, is_active=i != 1))
    db.flush()
    first = as_superadmin.get("/api/admin/academies?limit=2").json()
    second = as_superadmin.get(f"/api/admin/academies?limit=2&cursor={first['next_cursor']}").json()
    slugs = [a["slug"] for a in first["items"] + second["items"]]
    assert slugs == ["upiixia", "a0", "a1", "a2"] and second["next_cursor"] is None
    assert [a["is_active"] for a in first["items"] + second["items"]] == [True, True, False, True]


def test_update_and_soft_delete_academy(
    as_superadmin: TestClient, as_member: TestClient, seeded: dict, db: Session
) -> None:
    aid = seeded["academy_id"]
    body = as_superadmin.patch(
        f"/api/admin/academies/{aid}", json={"name": "UpiixIA 2026", "is_active": False}
    ).json()
    assert body["name"] == "UpiixIA 2026" and body["is_active"] is False
    assert as_member.get("/api/academies/upiixia").status_code == 404
    assert db.get(Academy, aid) is not None  # soft delete keeps its history
    assert (
        as_superadmin.patch(f"/api/admin/academies/{aid}", json={"is_active": True}).json()["is_active"]
        is True
    )
    assert as_superadmin.patch("/api/admin/academies/9999", json={"name": "x"}).status_code == 404
    assert as_superadmin.patch(f"/api/admin/academies/{aid}", json={"slug": "otro"}).status_code == 422


def test_superadmin_can_upload_logo_through_academy_endpoint(as_superadmin: TestClient, seeded: dict) -> None:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (20, 20)).save(buffer, "PNG")
    response = as_superadmin.post(
        f"/api/academies/{seeded['academy_id']}/logo",
        files={"file": ("l.png", buffer.getvalue(), "image/png")},
    )
    assert response.status_code == 200


# ── Users ────────────────────────────────────────────────────


def test_create_academy_admin_and_member(as_superadmin: TestClient, client: TestClient, seeded: dict) -> None:
    admin = as_superadmin.post(
        "/api/admin/users",
        json={
            "role": "academy_admin",
            "email": "Robo.Admin@upiixsol.dev",
            "full_name": "Admin Robótica",
            "academy_id": seeded["academy_id"],
            "password": "temporal-123",
        },
    )
    assert admin.status_code == 201
    body = admin.json()
    assert body["email"] == "robo.admin@upiixsol.dev" and body["role"] == "academy_admin"
    assert body["must_change_password"] is True and body["nickname"] == "admin"
    login = client.post(
        "/api/auth/login", json={"email": "robo.admin@upiixsol.dev", "password": "temporal-123"}
    )
    assert login.status_code == 200 and login.json()["user"]["academy_slug"] == "upiixia"

    member = as_superadmin.post(
        "/api/admin/users",
        json={
            "role": "member",
            "email": "nuevo@ipn.mx",
            "full_name": "Nuevo Miembro",
            "boleta": "2026000321",
            "password": "temporal-123",
            "nickname": "nuevo",
        },
    )
    assert member.status_code == 201 and member.json()["boleta"] == "2026000321"


def test_create_user_errors(as_superadmin: TestClient, seeded: dict) -> None:
    base = {"email": "x@upiixsol.dev", "full_name": "Equis Persona", "password": "temporal-123"}
    no_academy = as_superadmin.post("/api/admin/users", json={**base, "role": "academy_admin"})
    assert no_academy.status_code == 422
    bad_academy = as_superadmin.post(
        "/api/admin/users", json={**base, "role": "academy_admin", "academy_id": 999}
    )
    assert bad_academy.status_code == 422
    dup = as_superadmin.post(
        "/api/admin/users", json={**base, "role": "member", "email": "alumno.demo@upiixsol.dev"}
    )
    assert dup.status_code == 409
    dup_boleta = as_superadmin.post(
        "/api/admin/users", json={**base, "role": "member", "boleta": "2026000001"}
    )
    assert dup_boleta.status_code == 409
    superadmin = as_superadmin.post("/api/admin/users", json={**base, "role": "superadmin"})
    assert superadmin.status_code == 422


def test_cannot_assign_admin_to_inactive_academy(
    as_superadmin: TestClient, db: Session, seeded: dict
) -> None:
    closed = Academy(slug="cerrada", name="Cerrada", is_active=False)
    db.add(closed)
    db.flush()
    base = {"email": "x@upiixsol.dev", "full_name": "Equis Persona", "password": "temporal-123"}
    created = as_superadmin.post(
        "/api/admin/users", json={**base, "role": "academy_admin", "academy_id": closed.id}
    )
    assert created.status_code == 422
    moved = as_superadmin.patch(f"/api/admin/users/{seeded['admin_ia_id']}", json={"academy_id": closed.id})
    assert moved.status_code == 422


def test_concurrent_duplicates_are_409_not_500(
    as_superadmin: TestClient, monkeypatch: pytest.MonkeyPatch, seeded: dict
) -> None:
    """Simulates the check-then-insert race: the pre-check passes but the unique constraint fires."""
    from app.services import admin as service

    monkeypatch.setattr(service, "_slug_taken", lambda _db, _slug: False)
    monkeypatch.setattr(service, "_user_exists", lambda _db, _email, _boleta: False)
    academy = as_superadmin.post("/api/admin/academies", json={**NEW_ACADEMY, "slug": "upiixia"})
    assert academy.status_code == 409
    user = as_superadmin.post(
        "/api/admin/users",
        json={
            "email": "alumno.demo@upiixsol.dev",
            "full_name": "Duplicado",
            "password": "temporal-123",
            "role": "member",
        },
    )
    assert user.status_code == 409
    # The session is still usable after the rolled-back savepoint.
    assert (
        as_superadmin.get("/api/admin/users?q=alumno").json()["items"][0]["email"]
        == "alumno.demo@upiixsol.dev"
    )


def test_list_users_filters_and_paginates(as_superadmin: TestClient, seeded: dict) -> None:
    all_users = as_superadmin.get("/api/admin/users?limit=50").json()["items"]
    assert len(all_users) == 6 and all("password_hash" not in u for u in all_users)
    supers = as_superadmin.get("/api/admin/users?role=superadmin").json()["items"]
    assert len(supers) == 4
    by_academy = as_superadmin.get(f"/api/admin/users?academy_id={seeded['academy_id']}").json()["items"]
    assert [u["email"] for u in by_academy] == ["admin.ia@upiixsol.dev"]
    search = as_superadmin.get("/api/admin/users?q=ALUMNO").json()["items"]
    assert [u["email"] for u in search] == ["alumno.demo@upiixsol.dev"]
    boleta = as_superadmin.get("/api/admin/users?q=2026000001").json()["items"]
    assert len(boleta) == 1
    # LIKE wildcards are literal, and a blank search is no filter.
    assert as_superadmin.get("/api/admin/users?q=%25").json()["items"] == []
    assert as_superadmin.get("/api/admin/users?q=_").json()["items"] == []
    assert len(as_superadmin.get("/api/admin/users?q=%20").json()["items"]) == 6
    first = as_superadmin.get("/api/admin/users?limit=4").json()
    second = as_superadmin.get(f"/api/admin/users?limit=4&cursor={first['next_cursor']}").json()
    assert len(first["items"]) == 4 and len(second["items"]) == 2


def test_update_user_assign_academy_and_deactivate(
    as_superadmin: TestClient, seeded: dict, db: Session
) -> None:
    member_id = seeded["member_id"]
    body = as_superadmin.patch(
        f"/api/admin/users/{member_id}", json={"is_active": False, "nickname": "alumno"}
    ).json()
    assert body["is_active"] is False and body["nickname"] == "alumno"
    other = Academy(slug="robotica", name="Robótica")
    db.add(other)
    db.flush()
    admin_id = seeded["admin_ia_id"]
    moved = as_superadmin.patch(f"/api/admin/users/{admin_id}", json={"academy_id": other.id}).json()
    assert moved["academy_id"] == other.id
    assert as_superadmin.patch(f"/api/admin/users/{admin_id}", json={"academy_id": 999}).status_code == 422
    # academy_id only applies to academy admins
    assert (
        as_superadmin.patch(f"/api/admin/users/{member_id}", json={"academy_id": other.id}).status_code == 422
    )
    assert as_superadmin.patch("/api/admin/users/9999", json={"nickname": "xx"}).status_code == 404


def test_superadmin_cannot_deactivate_self(as_superadmin: TestClient, seeded: dict) -> None:
    me = seeded["superadmin_id"]
    response = as_superadmin.patch(f"/api/admin/users/{me}", json={"is_active": False})
    assert response.status_code == 422


def test_reset_password(as_superadmin: TestClient, client: TestClient, seeded: dict, db: Session) -> None:
    member_id = seeded["member_id"]
    client.post("/api/auth/login", json={"email": "alumno.demo@upiixsol.dev", "password": "admin123"})
    response = as_superadmin.post(f"/api/admin/users/{member_id}/reset-password")
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    temporary = response.json()["temporary_password"]
    assert len(temporary) >= 12
    user = db.get(User, member_id)
    db.refresh(user)
    assert verify_password(user.password_hash, temporary) and user.must_change_password is True
    assert all(
        t.revoked_at is not None for t in db.scalars(select(RefreshToken).filter_by(user_id=member_id))
    )
    assert as_superadmin.post("/api/admin/users/9999/reset-password").status_code == 404


# ── Home content ─────────────────────────────────────────────


def test_home_content_get_and_put(as_superadmin: TestClient, as_member: TestClient, seeded: dict) -> None:
    assert (
        as_superadmin.get("/api/admin/home").json()["hero_title"] == "Tu club, tus academias, un solo campus"
    )
    body = {
        "hero_title": "Semestre 2026-2",
        "hero_text": "Bienvenidos <script>x</script>",
        "featured_project_ids": [],
    }
    saved = as_superadmin.put("/api/admin/home", json=body).json()
    assert saved["hero_title"] == "Semestre 2026-2" and "<script" not in saved["hero_text"]
    assert as_member.get("/api/home").json()["hero"]["hero_title"] == "Semestre 2026-2"


def test_home_content_created_when_missing(as_superadmin: TestClient, db: Session) -> None:
    db.delete(db.get(HomeContent, 1))
    db.flush()
    assert as_superadmin.get("/api/admin/home").json()["hero_title"] == "UpiixSol Campus"
    assert as_superadmin.put("/api/admin/home", json={"hero_title": "Hola"}).json()["hero_title"] == "Hola"


def test_inactive_superadmin_token_rejected(client: TestClient, db: Session) -> None:
    ghost = make_user(db, role=Role.superadmin, email="off@upiixsol.dev", is_active=False)
    assert client.get("/api/admin/users", headers=auth_headers(ghost)).status_code == 401


def test_update_academy_renames_channel_and_ignores_nulls(
    as_superadmin: TestClient, seeded: dict, db: Session
) -> None:
    aid = seeded["academy_id"]
    body = as_superadmin.patch(
        f"/api/admin/academies/{aid}",
        json={"name": "UpiixIA Pro", "welcome_text": "Hola <script>x</script>", "color_primary": None},
    ).json()
    assert body["color_primary"] == "#00BF63" and "<script" not in body["welcome_text"]
    assert db.scalar(select(Channel).where(Channel.academy_id == aid)).name == "UpiixIA Pro"
    # An academy without a channel (legacy data) can still be renamed.
    legacy = Academy(slug="legacy", name="Legacy")
    db.add(legacy)
    db.flush()
    assert (
        as_superadmin.patch(f"/api/admin/academies/{legacy.id}", json={"name": "Nueva"}).json()["name"]
        == "Nueva"
    )


def test_update_user_ignores_null_fields(as_superadmin: TestClient, seeded: dict) -> None:
    body = as_superadmin.patch(f"/api/admin/users/{seeded['member_id']}", json={"full_name": None}).json()
    assert body["full_name"] == "Alumno Demo"
