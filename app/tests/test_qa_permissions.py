# ruff: noqa: F811  (pytest fixtures `clients` and `world` are imported, then requested as arguments)
"""QA permissions (UPS-051): docs/PRUEBAS-CAMPUS.md §2 (ROL-01…07) and §14 (SEC-02), through the API.

Builds on the permission matrix (test_permissions_matrix.py: its `world`, `clients`, MATRIX and READ_MATRIX)
and adds what the matrix does not state on its own: every admin/panel endpoint is in a matrix, the superadmin
really gets 2xx on any club, public payloads never carry email or boleta, a role or club change takes effect
on the very next request, and swapping ids (IDOR) never reaches someone else's data.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models import Event, LearningRoute, Post, Role, User
from app.tests.conftest import auth_headers, make_user
from app.tests.test_permissions_matrix import (  # noqa: F401 (fixtures)
    MATRIX,
    OWN,
    READ_MATRIX,
    SUPER,
    World,
    _event,
    _path,
    clients,
    world,
)

PANEL_RULES = [rule for rule in MATRIX + READ_MATRIX if rule.allowed in (OWN, SUPER)]
SUPER_RULES = [rule for rule in MATRIX + READ_MATRIX if rule.allowed == SUPER]


def _call(client: TestClient, rule, world: World, db: Session):
    return client.request(rule.method, _path(rule, world, db), **rule.request(world))


# ── ROL-05: every admin and panel endpoint has a declared rule ─


def test_every_admin_and_panel_endpoint_is_in_a_matrix() -> None:
    declared = {(rule.method, rule.path) for rule in MATRIX + READ_MATRIX}
    panel = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if path.startswith("/api/admin") or path.startswith("/api/academies/{academy_id}")
    }
    assert panel, "no admin or panel endpoints found"
    assert sorted(panel - declared) == []


# ── ROL-01 / ROL-03: members and club admins are refused ─────


@pytest.mark.parametrize("rule", PANEL_RULES, ids=lambda r: f"{r.method} {r.path}")
def test_member_gets_403_on_every_admin_and_panel_endpoint(
    rule, clients: dict[str, TestClient], world: World, db: Session
) -> None:
    assert _call(clients["member"], rule, world, db).status_code == 403


@pytest.mark.parametrize("rule", SUPER_RULES, ids=lambda r: f"{r.method} {r.path}")
def test_club_admin_gets_403_on_every_superadmin_endpoint(
    rule, clients: dict[str, TestClient], world: World, db: Session
) -> None:
    for role in ("admin_own", "admin_other"):
        assert _call(clients[role], rule, world, db).status_code == 403, role


# ── ROL-04: the superadmin manages any club ──────────────────


def test_superadmin_gets_2xx_on_any_club(clients: dict[str, TestClient], world: World) -> None:
    superadmin = clients["superadmin"]
    for academy_id in (world.academy_id, world.other_academy_id):
        assert superadmin.get(f"/api/academies/{academy_id}/content").status_code == 200
        assert superadmin.get(f"/api/academies/{academy_id}/enrollments").status_code == 200
        branding = superadmin.patch(f"/api/academies/{academy_id}/branding", json={"color_accent": "#123456"})
        assert branding.status_code == 200, branding.text
        created = superadmin.post(
            f"/api/academies/{academy_id}/routes", json={"title": f"Ruta QA {academy_id}"}
        )
        assert created.status_code == 201, created.text
    assert superadmin.get("/api/admin/users").status_code == 200


# ── ROL-06: public payloads never carry email or boleta ──────


def _private_keys(payload: Any, where: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        found += [f"{where}.{key}" for key in ("email", "boleta") if key in payload]
        for key, value in payload.items():
            found += _private_keys(value, f"{where}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found += _private_keys(value, f"{where}[{index}]")
    return found


def _first(client: TestClient, path: str, key: str) -> str | None:
    body = client.get(path).json()
    items = body.get("items", body) if isinstance(body, dict) else body
    return str(items[0][key]) if items else None


def test_public_payloads_never_carry_email_or_boleta(clients: dict[str, TestClient], world: World) -> None:
    member = clients["member"]
    # Comments and reactions on the target post, so its authors appear in the payloads.
    assert member.post(f"/api/posts/{world.post_id}/comments", json={"body": "Hola"}).status_code == 201
    paths = [
        "/api/home",
        "/api/academies",
        "/api/academies/upiixia",
        "/api/academies/upiixia/home",
        "/api/academies/upiixia/resources",
        "/api/academies/upiixia/routes",
        f"/api/routes/{world.route_id}",
        f"/api/lessons/{world.lesson_id}",
        "/api/channels",
        f"/api/channels/{world.channel_id}/posts",
        f"/api/posts/{world.post_id}/comments",
        "/api/reactions/mine",
        "/api/events",
        "/api/blog",
        "/api/projects",
        "/api/site",
    ]
    if blog := _first(member, "/api/blog", "slug"):
        paths.append(f"/api/blog/{blog}")
    if project := _first(member, "/api/projects", "slug"):
        paths.append(f"/api/projects/{project}")
    leaks: list[str] = []
    for client_name in ("member", "anon"):
        client = clients[client_name]
        for path in paths:
            response = client.get(path)
            if response.status_code == 200:
                leaks += [f"{client_name} GET {path}: {key}" for key in _private_keys(response.json())]
    assert leaks == []


# ── ROL-07: a role or club change applies on the next request ─


def test_demoted_admin_loses_the_panel_with_the_same_token(
    clients: dict[str, TestClient], world: World, db: Session
) -> None:
    """The role is read from the database on every request, so a token issued before a demotion carries no
    stale permission (stricter than "after the next refresh")."""
    admin = clients["admin_own"]
    content = f"/api/academies/{world.academy_id}/content"
    assert admin.get(content).status_code == 200
    user = db.scalar(select(User).where(User.email == "admin.ia@upiixsol.dev"))
    user.role, user.academy_id = Role.member, None  # no API changes a role yet (see the UPS-051 PR)
    db.flush()
    assert admin.get(content).status_code == 403
    assert admin.post(f"/api/academies/{world.academy_id}/routes", json={"title": "x"}).status_code == 403


def test_moved_admin_follows_the_new_club_with_the_same_token(
    clients: dict[str, TestClient], world: World, db: Session
) -> None:
    admin = clients["admin_own"]
    admin_id = db.scalar(select(User.id).where(User.email == "admin.ia@upiixsol.dev"))
    moved = clients["superadmin"].patch(
        f"/api/admin/users/{admin_id}", json={"academy_id": world.other_academy_id}
    )
    assert moved.status_code == 200, moved.text
    assert admin.get(f"/api/academies/{world.academy_id}/content").status_code == 403
    assert admin.get(f"/api/academies/{world.other_academy_id}/content").status_code == 200


# ── SEC-02: swapping ids (IDOR) ──────────────────────────────


@pytest.fixture
def stranger(db: Session, world: World):
    """Another member of the same club, signed in: the classic IDOR attacker."""
    user = make_user(db, email="otra.persona@ipn.mx", boleta="2026777001")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, headers=auth_headers(user)) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def test_a_member_cannot_touch_another_members_content(
    stranger: TestClient, world: World, db: Session
) -> None:
    assert stranger.delete(f"/api/posts/{world.post_id}").status_code == 403
    assert stranger.delete(f"/api/comments/{world.comment_id}").status_code == 403
    assert db.get(Post, world.post_id) is not None
    assert stranger.patch(f"/api/admin/users/{world.member_id}", json={"nickname": "hack"}).status_code == 403
    # Mass assignment: the account endpoint only edits the caller, and unknown fields are refused.
    swapped = stranger.patch("/api/account/profile", json={"nickname": "yo", "id": world.member_id})
    assert swapped.status_code == 422
    assert db.get(User, world.member_id).nickname != "yo"


def test_a_club_admin_cannot_reach_another_club_by_url(clients: dict[str, TestClient], world: World) -> None:
    admin = clients["admin_own"]
    other = world.other_academy_id
    assert admin.get(f"/api/academies/{other}/content").status_code == 403
    assert admin.get(f"/api/academies/{other}/enrollments").status_code == 403
    assert admin.post(f"/api/academies/{other}/routes", json={"title": "x"}).status_code == 403
    assert (
        admin.patch(f"/api/academies/{other}/branding", json={"color_accent": "#000000"}).status_code == 403
    )


def test_a_club_admin_cannot_reach_another_club_by_body(
    clients: dict[str, TestClient], world: World, db: Session
) -> None:
    admin = clients["admin_own"]
    other = world.other_academy_id
    created = admin.post("/api/events", json={**_event(world), "academy_id": other})
    assert created.status_code == 403, created.text
    moved = admin.patch(f"/api/events/{world.event_id}", json={**_event(world), "academy_id": other})
    assert moved.status_code in (403, 422), moved.text
    db.expire_all()
    assert db.get(Event, world.event_id).academy_id == world.academy_id
    routes_in_other = db.scalars(select(LearningRoute).where(LearningRoute.academy_id == other)).all()
    smuggled = admin.post(
        f"/api/academies/{world.academy_id}/routes", json={"title": "x", "academy_id": other}
    )
    assert smuggled.status_code == 422  # unknown fields are refused, never applied
    assert len(db.scalars(select(LearningRoute).where(LearningRoute.academy_id == other)).all()) == len(
        routes_in_other
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/lessons/999999",
        "/api/routes/999999",
        "/api/posts/999999/comments",
        "/api/academies/999999/content",
        "/api/academies/no-existe/home",
    ],
)
def test_unknown_ids_are_404_never_500(clients: dict[str, TestClient], path: str) -> None:
    for role in ("member", "superadmin"):
        assert clients[role].get(path).status_code in (403, 404), (role, path)
