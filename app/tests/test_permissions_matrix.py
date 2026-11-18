"""Permission matrix (IDEA §2.1): every write endpoint × every role, checked against the backend.

Each write endpoint of the app must appear in MATRIX (test_every_write_endpoint_is_in_the_matrix), so
a new endpoint cannot ship without a declared rule. Roles:

- anon: no token → 401 on everything except the public auth endpoints.
- member: seeded student (alumno.demo), enrolled in UpiixIA.
- admin_own: admin of UpiixIA, the academy that owns every target resource.
- admin_other: admin of another academy (Robótica).
- superadmin.

Rules: ANY (any signed-in user), OWN (admin of the target's academy or superadmin), SUPER (superadmin
only), PUBLIC (no session needed). "Allowed" means not 401/403 (and not 5xx); denied means exactly 403.
Denied roles run first; allowed calls may mutate (e.g. delete), so a later allowed role can get 404.
`docs/permissions-matrix.md` is regenerated from this table by `python -m app.tests.test_permissions_matrix`.
"""

import io
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import get_db
from app.main import app
from app.models import Academy, Channel, Comment, Event, LearningRoute, Lesson, Module, Post, Role, User
from app.models.common import utcnow
from app.tests.conftest import auth_headers, make_user

ROLES = ("anon", "member", "admin_own", "admin_other", "superadmin")
ANY = {"member", "admin_own", "admin_other", "superadmin"}
OWN = {"admin_own", "superadmin"}
SUPER = {"superadmin"}
PUBLIC = set(ROLES)
CLUB = {"member", "admin_own", "superadmin"}  # UPS-035: the club's members (enrolled) and admins
AUTHOR = {"member"}  # UPS-035: only the author (the seeded member wrote the target post and comment)
SENDERS = {"admin_own", "admin_other", "superadmin"}  # UPS-074: email senders, each within their own scope


@dataclass
class World:
    academy_id: int
    other_academy_id: int
    channel_id: int
    route_id: int
    module_id: int
    lesson_id: int
    post_id: int
    comment_id: int
    event_id: int
    member_id: int
    member_boleta: str
    ids: dict[str, list[int]] = field(default_factory=dict)


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def _event(w: World) -> dict:
    start = (utcnow() + timedelta(days=3)).replace(microsecond=0)
    return {
        "academy_id": w.academy_id,
        "title": "Taller",
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=1)).isoformat(),
    }


Request = Callable[[World], dict[str, Any]]


@dataclass(frozen=True)
class Rule:
    method: str
    path: str  # OpenAPI template, e.g. /api/routes/{route_id}
    allowed: set[str]
    request: Request = lambda _w: {}  # noqa: E731 (kwargs for TestClient.request)
    note: str = ""


def _json(body: Callable[[World], Any]) -> Request:
    return lambda w: {"json": body(w)}


def _file() -> Request:
    return lambda _w: {"files": {"file": ("x.png", _png(), "image/png")}}


MATRIX: list[Rule] = [
    # ── Auth (public) and enrollment ─────────────────────────
    Rule("POST", "/api/auth/register", PUBLIC, note="rate-limited per IP"),
    Rule("POST", "/api/auth/login", PUBLIC, note="rate-limited per IP"),
    Rule("POST", "/api/auth/refresh", PUBLIC, note="refresh cookie + X-Requested-With"),
    Rule("POST", "/api/auth/logout", PUBLIC, note="refresh cookie + X-Requested-With"),
    Rule("POST", "/api/academies/{slug}/enroll", ANY),
    Rule("DELETE", "/api/academies/{slug}/enroll", ANY),
    # ── Academy identity and content (admin of that academy) ─
    Rule(
        "PATCH", "/api/academies/{academy_id}/branding", OWN, _json(lambda _w: {"color_primary": "#00BF63"})
    ),
    Rule("POST", "/api/academies/{academy_id}/logo", OWN, _file()),
    Rule("POST", "/api/academies/{academy_id}/mascot", OWN, _file()),
    Rule("POST", "/api/academies/{academy_id}/routes", OWN, _json(lambda _w: {"title": "Ruta nueva"})),
    Rule("PUT", "/api/academies/{academy_id}/routes/order", OWN, _json(lambda w: {"ids": w.ids["routes"]})),
    Rule("PATCH", "/api/routes/{route_id}", OWN, _json(lambda _w: {"title": "Ruta editada"})),
    Rule("DELETE", "/api/routes/{route_id}", OWN),
    Rule(
        "POST",
        "/api/academies/{academy_id}/routes/{route_id}/modules",
        OWN,
        _json(lambda _w: {"title": "Módulo nuevo"}),
    ),
    Rule("PUT", "/api/routes/{route_id}/modules/order", OWN, _json(lambda w: {"ids": w.ids["modules"]})),
    Rule("PATCH", "/api/modules/{module_id}", OWN, _json(lambda _w: {"title": "Módulo editado"})),
    Rule("DELETE", "/api/modules/{module_id}", OWN),
    Rule(
        "POST",
        "/api/modules/{module_id}/lessons",
        OWN,
        _json(lambda _w: {"title": "Clase", "youtube_url": "https://youtu.be/rfscVS0vtbw"}),
    ),
    Rule("PUT", "/api/modules/{module_id}/lessons/order", OWN, _json(lambda w: {"ids": w.ids["lessons"]})),
    Rule("PATCH", "/api/lessons/{lesson_id}", OWN, _json(lambda _w: {"title": "Clase editada"})),
    Rule("DELETE", "/api/lessons/{lesson_id}", OWN),
    Rule(
        "POST", "/api/academies/{academy_id}/enrollments", OWN, _json(lambda w: {"boleta": w.member_boleta})
    ),
    Rule("DELETE", "/api/academies/{academy_id}/enrollments/{user_id}", OWN),
    # ── Superadmin panel ─────────────────────────────────────
    Rule("POST", "/api/admin/academies", SUPER, _json(lambda _w: {"slug": "nueva", "name": "Nueva"})),
    Rule("PATCH", "/api/admin/academies/{academy_id}", SUPER, _json(lambda _w: {"short_description": "x"})),
    Rule(
        "POST",
        "/api/admin/users",
        SUPER,
        _json(
            lambda _w: {
                "role": "member",
                "email": "nuevo@upiixsol.dev",
                "full_name": "Persona Nueva",
                "password": "temporal-123",
            }
        ),
    ),
    Rule("PATCH", "/api/admin/users/{user_id}", SUPER, _json(lambda _w: {"nickname": "nuevo"})),
    Rule("PUT", "/api/admin/users/{user_id}/role", SUPER, _json(lambda _w: {"role": "member"})),  # UPS-093
    Rule("POST", "/api/admin/users/{user_id}/reset-password", SUPER),
    Rule("PUT", "/api/admin/home", SUPER, _json(lambda _w: {"hero_title": "UpiixSol Campus"})),
    # ── Site brand (UPS-041); its read, GET /api/site, is public ──
    Rule(
        "PUT",
        "/api/admin/site",
        SUPER,
        _json(
            lambda _w: {
                "name": "UpiixSol",
                "color_primary": "#00BF63",
                "color_secondary": "#04944F",
                "color_accent": "#F28034",
            }
        ),
    ),
    Rule("POST", "/api/admin/site/logo", SUPER, _file()),
    Rule("POST", "/api/admin/site/mascot", SUPER, _file()),
    Rule("DELETE", "/api/admin/site/logo", SUPER, note="no logo → the name as a three-color wordmark"),
    Rule("DELETE", "/api/admin/site/mascot", SUPER, note="no mascot anywhere"),
    # ── Community ────────────────────────────────────────────
    Rule(
        "POST",
        "/api/channels/{channel_id}/posts",
        CLUB,
        lambda _w: {"data": {"body": "Hola"}},
        note="club channel: its members and admins (UPS-035); General: anyone",
    ),
    Rule("POST", "/api/posts/{post_id}/comments", ANY, _json(lambda _w: {"body": "Comentario"})),
    Rule("POST", "/api/posts/{post_id}/hide", OWN, note="moderation: academy channel"),
    Rule("POST", "/api/comments/{comment_id}/hide", OWN, note="moderation: academy channel"),
    Rule("PUT", "/api/posts/{post_id}/reactions/{kind}", ANY, note="idempotent, 60/min per user (UPS-018)"),
    Rule("DELETE", "/api/posts/{post_id}/reactions/{kind}", ANY, note="idempotent (UPS-018)"),
    # ── Events ───────────────────────────────────────────────
    Rule("POST", "/api/events", OWN, _json(_event)),
    Rule("PATCH", "/api/events/{event_id}", OWN, _json(_event)),
    Rule("DELETE", "/api/events/{event_id}", OWN),
    Rule("POST", "/api/events/{event_id}/cover", OWN, _file()),
    Rule("DELETE", "/api/events/{event_id}/cover", OWN),
    # ── Learning progress ────────────────────────────────────
    Rule(
        "POST",
        "/api/lessons/{lesson_id}/complete",
        ANY,
        note="any signed-in user (enrolls on first progress)",
    ),
    # ── Gallery and blog (UPS-017) ───────────────────────────
    Rule("POST", "/api/projects", SUPER, _json(lambda _w: {"title": "Proyecto", "slug": "proyecto-matriz"})),
    Rule(
        "PUT", "/api/projects/{project_id}", SUPER, _json(lambda _w: {"title": "Editado", "slug": "editado"})
    ),
    Rule("DELETE", "/api/projects/{project_id}", SUPER),
    Rule("POST", "/api/projects/{project_id}/cover", SUPER, _file()),
    Rule("POST", "/api/blog", SUPER, _json(lambda _w: {"title": "Entrada", "slug": "entrada-matriz"})),
    Rule("PUT", "/api/blog/{blog_id}", SUPER, _json(lambda _w: {"title": "Editada", "slug": "editada-b"})),
    Rule("DELETE", "/api/blog/{blog_id}", SUPER),
    Rule("POST", "/api/blog/{blog_id}/cover", SUPER, _file()),
    # ── Resources (UPS-012) ──────────────────────────────────
    Rule(
        "POST",
        "/api/academies/{academy_id}/resources",
        OWN,
        lambda _w: {"data": {"type": "link", "title": "Recurso", "url": "https://upiixsol.dev"}},
    ),
    Rule("PATCH", "/api/resources/{resource_id}", OWN, _json(lambda _w: {"title": "Recurso editado"})),
    Rule("DELETE", "/api/resources/{resource_id}", OWN),
    Rule("POST", "/api/resources/{resource_id}/file", OWN, _file()),
    # ── My account (UPS-014): always the caller's own data ───
    Rule("PATCH", "/api/account/profile", ANY, _json(lambda _w: {"nickname": "yo-mismo"})),
    Rule("POST", "/api/account/avatar", ANY, _file()),
    Rule(
        "POST",
        "/api/account/email",
        ANY,
        _json(lambda _w: {"new_email": "otro@upiixsol.dev", "current_password": "x"}),
        note="also requires the current password",
    ),
    Rule(
        "POST",
        "/api/account/password",
        ANY,
        _json(
            lambda _w: {
                "current_password": "x",
                "new_password": "nueva-1234",
                "confirm_password": "nueva-1234",
            }
        ),
        note="also requires the current password",
    ),
    # ── Usage analytics (UPS-037): the caller's own events ───
    Rule(
        "POST",
        "/api/analytics/events",
        ANY,
        _json(lambda _w: {"session_id": "matrix-0001", "events": [{"name": "page.view"}]}),
        note="usage analytics, 30/min per user (UPS-037)",
    ),
    # ── Community: authors delete their own (UPS-035) ────────
    Rule("DELETE", "/api/posts/{post_id}", AUTHOR, note="author only; moderators hide instead"),
    Rule(
        "DELETE",
        "/api/comments/{comment_id}",
        {"member", "admin_own", "superadmin"},
        note="author, or the moderators of its channel (UPS-070)",
    ),
    # ── Email (UPS-074): audience of the club; all/role/individual 403s in test_mail_audience.py ──
    Rule(
        "POST",
        "/api/mail/audience/preview",
        OWN,
        _json(lambda w: {"kind": "academy", "academy_id": w.academy_id}),
        note="superadmin: any audience; academy_admin: own club, its enrollees and outside addresses",
    ),
    # ── Email campaigns (UPS-075): payload and sender 403s in test_mail_campaigns.py ──
    Rule(
        "POST",
        "/api/mail/campaigns",
        OWN,
        _json(
            lambda w: {
                "subject": "Aviso",
                "body": "Hola",
                "audience": {"kind": "academy", "academy_id": w.academy_id},
            }
        ),
        note="draft; same audience scope as the preview",
    ),
    Rule(
        "POST",
        "/api/mail/preview",
        OWN,
        _json(
            lambda w: {
                "subject": "Aviso",
                "blocks": [{"kind": "paragraph", "text": "Hola"}],
                "audience": {"kind": "academy", "academy_id": w.academy_id},
            }
        ),
        note="UPS-089: {html, text} of the email; same audience scope as create",
    ),
    Rule(
        "POST",
        "/api/mail/images",
        SENDERS,
        _file(),
        note="UPS-088: email image (PNG/JPEG copy under /media/mail); rate-limited per user",
    ),
    Rule("GET", "/api/mail/reply-to", SENDERS, note="UPS-091: default Reply-To the composer prefills"),
    Rule("POST", "/api/mail/campaigns/{campaign_id}/send", OWN, note="the campaign's sender or superadmin"),
    Rule("POST", "/api/mail/campaigns/{campaign_id}/resume", OWN, note="the campaign's sender or superadmin"),
    # ── Email opt-out (UPS-076): real-token tests in test_mail_unsubscribe.py ──
    Rule(
        "POST",
        "/api/mail/unsubscribe",
        PUBLIC,
        note="token in ?t=, same 200 for unknown tokens; rate-limited per IP",
    ),
    Rule(
        "POST",
        "/api/mail/webhooks/mailgun",
        PUBLIC,
        note="HMAC signature is the credential; really signed payloads in test_mail_webhooks.py",
    ),
    Rule(
        "PUT",
        "/api/mail/preferences",
        ANY,
        _json(lambda _w: {"receive_club_email": True}),
        note="the caller's own address only",
    ),
]

WRITE_METHODS = {"post", "put", "patch", "delete"}


def app_write_endpoints() -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in WRITE_METHODS
    }


def test_every_write_endpoint_is_in_the_matrix() -> None:
    declared = {(rule.method, rule.path) for rule in MATRIX}
    missing = sorted(app_write_endpoints() - declared)
    assert not missing, f"Write endpoints without a rule in MATRIX: {missing}"
    assert len(declared) == len(MATRIX), "duplicated rule"


# ── World: one target of each kind, owned by UpiixIA ────────


@pytest.fixture
def world(db: Session, seeded: dict) -> World:
    robotica = Academy(slug="robotica", name="Robótica")
    db.add(robotica)
    db.flush()
    db.add(Channel(type="academy", academy_id=robotica.id, name="Robótica", slug="robotica"))
    make_user(db, role=Role.academy_admin, email="admin.robotica@upiixsol.dev", academy_id=robotica.id)
    ia = seeded["academy_id"]
    routes = db.scalars(
        select(LearningRoute.id).where(LearningRoute.academy_id == ia).order_by(LearningRoute.position)
    ).all()
    modules = db.scalars(
        select(Module.id).where(Module.route_id == routes[0]).order_by(Module.position)
    ).all()
    lessons = db.scalars(
        select(Lesson.id).where(Lesson.module_id == modules[0]).order_by(Lesson.position)
    ).all()
    member = db.get(User, seeded["member_id"])
    post = Post(channel_id=seeded["channel_id"], author_id=member.id, body="Post de prueba")
    db.add(post)
    db.flush()
    comment = Comment(post_id=post.id, author_id=member.id, body="Comentario de prueba")
    event = Event(academy_id=ia, title="Evento", starts_at=utcnow(), ends_at=utcnow() + timedelta(hours=1))
    db.add_all([comment, event])
    db.flush()
    return World(
        academy_id=ia,
        other_academy_id=robotica.id,
        channel_id=seeded["channel_id"],
        route_id=routes[0],
        module_id=modules[0],
        lesson_id=lessons[0],
        post_id=post.id,
        comment_id=comment.id,
        event_id=event.id,
        member_id=member.id,
        member_boleta=member.boleta,
        ids={"routes": list(routes), "modules": list(modules), "lessons": list(lessons)},
    )


def _fresh(db: Session, model: str) -> int:
    """A new project or blog post per rule, so a DELETE by one role never hides it from the next."""
    from app import models

    row = getattr(models, model)(title="Matriz", slug=f"matriz-{model.lower()}-{utcnow().timestamp()}")
    db.add(row)
    db.flush()
    return row.id


def _resource_id(db: Session, w: World) -> int:
    from app.models import Resource

    resource = Resource(academy_id=w.academy_id, type="link", title="Guía", url="https://upiixsol.dev")
    db.add(resource)
    db.flush()
    return resource.id


def _campaign(db: Session, w: World) -> int:
    """A draft of UpiixIA sent by its admin (UPS-075): its sender and superadmins may send it."""
    from app.models.mail import MailCampaign

    sender = db.scalar(select(User.id).where(User.email == "admin.ia@upiixsol.dev"))
    campaign = MailCampaign(
        sender_id=sender,
        academy_id=w.academy_id,
        audience_kind="academy",
        audience_params={"academy_id": w.academy_id},
        subject="Matriz",
        body="Hola",
    )
    db.add(campaign)
    db.flush()
    return campaign.id


def _path(rule: Rule, w: World, db: Session) -> str:
    values: dict[str, Any] = {
        "slug": "upiixia",
        "academy_id": w.academy_id,
        "route_id": w.route_id,
        "module_id": w.module_id,
        "lesson_id": w.lesson_id,
        "post_id": w.post_id,
        "comment_id": w.comment_id,
        "event_id": w.event_id,
        "channel_id": w.channel_id,
        "user_id": w.member_id,
        "kind": "like",
    }
    if "{resource_id}" in rule.path:
        values["resource_id"] = _resource_id(db, w)
    if "{project_id}" in rule.path:
        values["project_id"] = _fresh(db, "Project")
    if "{blog_id}" in rule.path:
        values["blog_id"] = _fresh(db, "BlogPost")
    if "{campaign_id}" in rule.path:
        values["campaign_id"] = _campaign(db, w)
    return rule.path.format(**values)


@pytest.fixture(autouse=True)
def _mail_on(monkeypatch: pytest.MonkeyPatch, engine: Engine) -> Iterator[None]:
    """Mail on with the console transport, and background sends bound to the test DB (UPS-075)."""
    from app.services import mail_campaigns
    from app.services.mailer import ConsoleTransport, get_mail_transport

    monkeypatch.setattr(get_settings(), "mail_enabled", True)
    monkeypatch.setattr(mail_campaigns, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))
    app.dependency_overrides[get_mail_transport] = ConsoleTransport
    yield
    app.dependency_overrides.pop(get_mail_transport, None)


@pytest.fixture
def clients(db: Session, world: World) -> Iterator[dict[str, TestClient]]:
    emails = {
        "member": "alumno.demo@upiixsol.dev",
        "admin_own": "admin.ia@upiixsol.dev",
        "admin_other": "admin.robotica@upiixsol.dev",
        "superadmin": "superadmin1@upiixsol.dev",
    }
    app.dependency_overrides[get_db] = lambda: db
    built: dict[str, TestClient] = {"anon": TestClient(app)}
    for role, email in emails.items():
        user = db.scalar(select(User).where(User.email == email))
        built[role] = TestClient(app, headers=auth_headers(user))
    yield built
    app.dependency_overrides.pop(get_db, None)


def _order(allowed: set[str]) -> list[str]:
    """Denied roles first (they must not mutate anything), then allowed ones, superadmin last."""
    return [r for r in ROLES if r not in allowed] + [r for r in ROLES if r in allowed]


@pytest.mark.parametrize("rule", MATRIX, ids=lambda r: f"{r.method} {r.path}")
def test_matrix(rule: Rule, clients: dict[str, TestClient], world: World, db: Session) -> None:
    if (rule.method, rule.path) not in app_write_endpoints():
        pytest.skip("endpoint not in this build yet")
    if rule.allowed == PUBLIC:
        return  # covered by test_auth.py (rate limits, CSRF header, cookie rotation)
    url = _path(rule, world, db)
    results = {}
    for role in _order(rule.allowed):
        response = clients[role].request(rule.method, url, **rule.request(world))
        results[role] = response.status_code
    expected = {role: ("allowed" if role in rule.allowed else 403) for role in ROLES}
    expected["anon"] = 401
    actual = {
        role: ("allowed" if code not in (401, 403) and code < 500 else code) for role, code in results.items()
    }
    assert actual == expected, f"{rule.method} {url}: {results}"


# ── Sensitive reads (UPS-036): club content and enrollees ───
# Kept apart from MATRIX (writes): these GETs return drafts and the enrollees' email and boleta, so an
# admin of another club or a member must get 403 like on the writes.

READ_MATRIX: list[Rule] = [
    Rule("GET", "/api/academies/{academy_id}/content", OWN, note="drafts included"),
    Rule("GET", "/api/academies/{academy_id}/enrollments", OWN, note="email and boleta of each enrollee"),
    Rule("GET", "/api/admin/academies", SUPER, note="inactive clubs included"),
    Rule("GET", "/api/admin/users", SUPER),
    Rule("GET", "/api/admin/home", SUPER),
    Rule("GET", "/api/mail/status", SENDERS, note="daily quota (UPS-074)"),
    Rule(
        "GET",
        "/api/mail/recipients",
        SENDERS,
        note="own club's enrollees and co-admins; email only for superadmin",
    ),
    Rule(
        "GET",
        "/api/mail/campaigns",
        SENDERS,
        note="history: superadmin all, academy_admin own club (UPS-075)",
    ),
    Rule("GET", "/api/mail/campaigns/{campaign_id}", OWN, note="a campaign of the club (UPS-075)"),
]


def app_read_endpoints() -> set[tuple[str, str]]:
    return {("GET", path) for path, operations in app.openapi()["paths"].items() if "get" in operations}


def test_read_matrix_endpoints_exist() -> None:
    missing = sorted({(rule.method, rule.path) for rule in READ_MATRIX} - app_read_endpoints())
    assert not missing, f"READ_MATRIX rules without an endpoint: {missing}"


@pytest.mark.parametrize("rule", READ_MATRIX, ids=lambda r: f"{r.method} {r.path}")
def test_read_matrix(rule: Rule, clients: dict[str, TestClient], world: World, db: Session) -> None:
    url = _path(rule, world, db)
    results = {role: clients[role].get(url).status_code for role in ROLES}
    expected = {role: (200 if role in rule.allowed else 403) for role in ROLES}
    expected["anon"] = 401
    assert results == expected, f"GET {url}: {results}"


def render_reads_markdown() -> str:
    lines = [
        "",
        "## Lecturas sensibles",
        "",
        "`READ_MATRIX`: lecturas con borradores o datos personales (correo, boleta), "
        "verificadas igual que las escrituras.",
        "",
        "| Método | Ruta | " + " | ".join(LABELS[r] for r in ROLES) + " | Nota |",
        "|---|---|" + "---|" * len(ROLES) + "---|",
    ]
    for rule in READ_MATRIX:
        cells = ["🔒" if r == "anon" else ("✅" if r in rule.allowed else "❌") for r in ROLES]
        lines.append(f"| {rule.method} | `{rule.path}` | " + " | ".join(cells) + f" | {rule.note} |")
    return "\n".join(lines) + "\n"


# ── docs/permissions-matrix.md ──────────────────────────────

LABELS = {"anon": "Anónimo", "member": "Miembro", "admin_own": "Admin (su club)",
          "admin_other": "Admin (otro club)", "superadmin": "Superadmin"}  # fmt: skip


def render_markdown() -> str:
    endpoints = app_write_endpoints()
    covered = [r for r in MATRIX if (r.method, r.path) in endpoints]
    lines = [
        "# Matriz de permisos (escritura)",
        "",
        "Generado por `uv run python -m app.tests.test_permissions_matrix` desde `MATRIX` en "
        "`app/tests/test_permissions_matrix.py`; el test verifica cada celda contra el backend (IDEA §2.1).",
        "",
        f"Cobertura: **{len(covered)}/{len(endpoints)} endpoints de escritura "
        f"({100 * len(covered) // max(len(endpoints), 1)} %)** × {len(ROLES)} roles.",
        "",
        "✅ permitido · ❌ 403 · 🔒 401 (sin sesión) · 🌐 público",
        "",
        "| Método | Ruta | " + " | ".join(LABELS[r] for r in ROLES) + " | Nota |",
        "|---|---|" + "---|" * len(ROLES) + "---|",
    ]
    for rule in covered:
        if rule.allowed == PUBLIC:
            cells = ["🌐"] * len(ROLES)
        else:
            cells = ["🔒" if r == "anon" else ("✅" if r in rule.allowed else "❌") for r in ROLES]
        lines.append(f"| {rule.method} | `{rule.path}` | " + " | ".join(cells) + f" | {rule.note} |")
    return "\n".join(lines) + "\n" + render_reads_markdown()


DOC = Path(__file__).resolve().parents[2] / "docs" / "permissions-matrix.md"


def test_docs_are_up_to_date() -> None:
    assert DOC.read_text(encoding="utf-8") == render_markdown(), (
        "docs/permissions-matrix.md is stale: run `uv run python -m app.tests.test_permissions_matrix`"
    )


if __name__ == "__main__":  # pragma: no cover
    DOC.write_text(render_markdown(), encoding="utf-8")
