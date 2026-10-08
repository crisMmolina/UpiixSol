from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import RefreshToken, Role, User
from app.models.common import utcnow
from app.routers.auth import REFRESH_COOKIE
from app.security import create_access_token, decode_access_token, hash_token
from app.services import auth as auth_service
from app.services.auth import REFRESH_GRACE
from app.tests.conftest import make_academy, make_user


@pytest.fixture
def client(db: Session):
    """HTTPS client: the refresh cookie is `Secure`, so it only travels over https (as in production)."""
    from app.db import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, base_url="https://testserver", headers={"X-Requested-With": "fetch"}) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


REGISTER = {
    "full_name": "Ana López Pérez",
    "boleta": "2026123456",
    "email": "Ana.Lopez@alumno.ipn.mx",
    "password": "segura-123",
    "accept_privacy": True,
}


def _login(client: TestClient, email: str = "ana.lopez@alumno.ipn.mx", password: str = "segura-123"):  # noqa: S107
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ── Register ─────────────────────────────────────────────────


def test_register_creates_member_and_session(client: TestClient, db: Session) -> None:
    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 15 * 60
    assert body["user"]["role"] == "member"
    assert body["user"]["email"] == "ana.lopez@alumno.ipn.mx"
    assert body["user"]["nickname"] == "ana"
    assert body["user"]["must_change_password"] is False
    assert decode_access_token(body["access_token"])["sub"] == str(body["user"]["id"])

    cookie = response.headers["set-cookie"]
    assert f"{REFRESH_COOKIE}=" in cookie and "HttpOnly" in cookie and "Path=/api/auth" in cookie
    assert "samesite=lax" in cookie.lower()

    user = db.scalar(select(User).filter_by(email="ana.lopez@alumno.ipn.mx"))
    assert user is not None and user.boleta == "2026123456" and user.password_hash.startswith("$argon2id$")


def test_register_uses_given_nickname(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={**REGISTER, "nickname": "anita"})
    assert response.json()["user"]["nickname"] == "anita"


@pytest.mark.parametrize("field", ["boleta", "email"])
def test_register_duplicate_is_generic_409(client: TestClient, db: Session, field: str) -> None:
    make_user(
        db,
        email="otro@ipn.mx" if field == "boleta" else REGISTER["email"].lower(),
        boleta=REGISTER["boleta"] if field == "boleta" else "2026000099",
    )
    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 409
    message = response.json()["error"]["message"]
    assert "boleta" not in message.lower() or "correo" in message.lower()  # never says which one exists


def test_register_rejects_role_and_bad_input(client: TestClient) -> None:
    assert client.post("/api/auth/register", json={**REGISTER, "role": "superadmin"}).status_code == 422
    assert client.post("/api/auth/register", json={**REGISTER, "boleta": "12345"}).status_code == 422
    assert client.post("/api/auth/register", json={**REGISTER, "password": "corta"}).status_code == 422
    assert client.post("/api/auth/register", json={**REGISTER, "accept_privacy": False}).status_code == 422


# ── Login ────────────────────────────────────────────────────


def test_login_returns_session_for_each_role(client: TestClient, db: Session) -> None:
    academy = make_academy(db)
    make_user(db, role=Role.academy_admin, email="admin.ia@upiixsol.dev", academy_id=academy.id)
    response = _login(client, "ADMIN.IA@upiixsol.dev", "password123")
    assert response.status_code == 200
    user = response.json()["user"]
    assert (user["role"], user["academy_id"], user["academy_slug"]) == (
        "academy_admin",
        academy.id,
        "upiixia",
    )


@pytest.mark.parametrize(("email", "password"), [("nadie@ipn.mx", "password123"), ("m@ipn.mx", "incorrecta")])
def test_login_wrong_credentials_are_generic_401(
    client: TestClient, db: Session, email: str, password: str
) -> None:
    make_user(db, email="m@ipn.mx")
    response = _login(client, email, password)
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Correo o contraseña incorrectos."


def test_inactive_user_cannot_login(client: TestClient, db: Session) -> None:
    make_user(db, email="off@ipn.mx", is_active=False)
    assert _login(client, "off@ipn.mx", "password123").status_code == 401


def test_login_rehashes_outdated_password(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = make_user(db, email="m@ipn.mx")
    old_hash = user.password_hash
    monkeypatch.setattr("app.services.auth.password_needs_rehash", lambda _hash: True)
    assert _login(client, "m@ipn.mx", "password123").status_code == 200
    db.refresh(user)
    assert user.password_hash != old_hash


def test_login_and_register_are_rate_limited(client: TestClient, db: Session) -> None:
    make_user(db, email="m@ipn.mx")
    statuses = [_login(client, "m@ipn.mx", "mal").status_code for _ in range(6)]
    assert statuses[:5] == [401] * 5 and statuses[5] == 429
    assert client.post("/api/auth/register", json=REGISTER).status_code == 201  # separate limit per endpoint


# ── Refresh, logout, me ──────────────────────────────────────


def test_refresh_rotates_and_reuse_revokes_the_family(client: TestClient, db: Session) -> None:
    first = client.post("/api/auth/register", json=REGISTER)
    old_raw = first.cookies[REFRESH_COOKIE]

    rotated = client.post("/api/auth/refresh")
    assert rotated.status_code == 200
    new_raw = rotated.cookies[REFRESH_COOKIE]
    assert new_raw != old_raw and rotated.json()["user"]["email"] == "ana.lopez@alumno.ipn.mx"

    # Replaying the old token (stolen cookie) after the grace window revokes every token of the family.
    used = db.scalar(select(RefreshToken).filter_by(token_hash=hash_token(old_raw)))
    used.used_at = utcnow() - REFRESH_GRACE - timedelta(seconds=1)
    db.flush()
    client.cookies.set(REFRESH_COOKIE, old_raw, path="/api/auth")
    replay = client.post("/api/auth/refresh")
    assert replay.status_code == 401
    assert REFRESH_COOKIE in replay.headers.get("set-cookie", "")  # cleared
    current = db.scalar(select(RefreshToken).filter_by(token_hash=hash_token(new_raw)))
    assert current is not None and current.revoked_at is not None

    client.cookies.set(REFRESH_COOKIE, new_raw, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401


def test_refresh_without_or_with_unknown_cookie_is_401(client: TestClient) -> None:
    assert client.post("/api/auth/refresh").status_code == 401
    client.cookies.set(REFRESH_COOKIE, "desconocido", path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401


def test_refresh_rejects_expired_token_and_inactive_user(client: TestClient, db: Session) -> None:
    client.post("/api/auth/register", json=REGISTER)
    token = db.scalar(select(RefreshToken))
    token.expires_at = utcnow() - timedelta(seconds=1)
    db.flush()
    assert client.post("/api/auth/refresh").status_code == 401

    client.cookies.clear()
    _login(client)
    db.scalar(select(User).filter_by(email="ana.lopez@alumno.ipn.mx")).is_active = False
    db.flush()
    assert client.post("/api/auth/refresh").status_code == 401


def test_logout_revokes_refresh_and_clears_cookie(client: TestClient, db: Session) -> None:
    client.post("/api/auth/register", json=REGISTER)
    raw = client.cookies[REFRESH_COOKIE]
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    assert 'upx_refresh=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]
    assert db.scalar(select(RefreshToken).filter_by(token_hash=hash_token(raw))).revoked_at is not None
    client.cookies.set(REFRESH_COOKIE, raw, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401
    assert client.post("/api/auth/logout").status_code == 204  # idempotent, even without a valid cookie


def test_me_requires_auth_and_hides_nothing_of_own_data(client: TestClient, as_member: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401
    me = as_member.get("/api/auth/me").json()
    assert me["email"] == "alumno.demo@upiixsol.dev" and me["boleta"] == "2026000001"
    assert me["must_change_password"] is True and me["academy_slug"] is None


def test_seeded_accounts_can_log_in(client: TestClient, seeded: dict) -> None:
    for email, role in [
        ("superadmin1@upiixsol.dev", "superadmin"),
        ("admin.ia@upiixsol.dev", "academy_admin"),
        ("alumno.demo@upiixsol.dev", "member"),
    ]:
        response = _login(client, email, "admin123")
        assert response.status_code == 200, email
        assert response.json()["user"]["role"] == role


def test_cookie_endpoints_require_fetch_header(client: TestClient) -> None:
    """CSRF guard: a cross-site form post (no custom header) cannot rotate or revoke the session."""
    client.post("/api/auth/register", json=REGISTER)
    for path in ("/api/auth/refresh", "/api/auth/logout"):
        response = client.post(path, headers={"X-Requested-With": ""})
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "csrf"
    assert client.post("/api/auth/refresh").status_code == 200  # the session was not touched


def test_logout_without_cookie_and_unknown_cookie(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set(REFRESH_COOKIE, "desconocido", path="/api/auth")
    assert client.post("/api/auth/logout").status_code == 204


def test_revoke_all_for_user_kills_every_session(client: TestClient, db: Session) -> None:
    from app.services.auth import revoke_all_for_user

    client.post("/api/auth/register", json=REGISTER)
    _login(client)
    user = db.scalar(select(User).filter_by(email="ana.lopez@alumno.ipn.mx"))
    revoke_all_for_user(db, user.id)
    tokens = list(db.scalars(select(RefreshToken).filter_by(user_id=user.id)))
    assert len(tokens) == 2 and all(t.revoked_at is not None for t in tokens)
    assert client.post("/api/auth/refresh").status_code == 401


def test_default_nickname_handles_accents_and_short_names() -> None:
    from app.services.auth import default_nickname

    assert default_nickname("Íñigo Pérez") == "inigo"
    assert default_nickname("A B") == "miembro"
    assert default_nickname("   ") == "miembro"


# ── Hardening (UPS-020) ──────────────────────────────────────


def test_concurrent_refresh_only_one_wins(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two refreshes read the same unused token; the other one claims it before this one does."""
    raw = client.post("/api/auth/register", json=REGISTER).cookies[REFRESH_COOKIE]
    real_aware = auth_service._aware
    winners = []

    def other_request_first(moment):
        monkeypatch.setattr(auth_service, "_aware", real_aware)
        winners.append(auth_service.rotate_refresh(db, raw))  # the concurrent refresh, between read and claim
        return real_aware(moment)

    monkeypatch.setattr(auth_service, "_aware", other_request_first)
    loser = client.post("/api/auth/refresh")
    assert len(winners) == 1
    assert loser.status_code == 401 and loser.json()["error"]["code"] == "refresh_race"
    assert "set-cookie" not in loser.headers  # the winner's new cookie must survive
    family = list(db.scalars(select(RefreshToken)))
    assert len(family) == 2 and all(t.revoked_at is None for t in family)  # the family is kept


def test_two_tabs_refreshing_at_once_keep_the_session(client: TestClient, db: Session) -> None:
    raw = client.post("/api/auth/register", json=REGISTER).cookies[REFRESH_COOKIE]
    first = client.post("/api/auth/refresh")
    assert first.status_code == 200
    new_raw = first.cookies[REFRESH_COOKIE]
    client.cookies.set(REFRESH_COOKIE, raw, path="/api/auth")  # the other tab still sends the old one
    second = client.post("/api/auth/refresh")
    assert second.status_code == 401 and second.json()["error"]["code"] == "refresh_race"
    client.cookies.set(REFRESH_COOKIE, new_raw, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 200  # nothing was revoked


def test_concurrent_register_is_409(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both requests pass the existence check; the unique index rejects the second insert."""
    make_user(db, email=REGISTER["email"].lower(), boleta="2026000099")
    monkeypatch.setattr(db, "scalar", lambda *args, **kwargs: None)  # the check ran before the other insert
    response = client.post("/api/auth/register", json=REGISTER)
    monkeypatch.undo()
    assert response.status_code == 409 and response.json()["error"]["code"] == "account_exists"
    assert db.scalar(select(User).filter_by(email=REGISTER["email"].lower())) is not None  # session usable


def test_password_change_invalidates_issued_access_tokens(client: TestClient, db: Session) -> None:
    old_token = client.post("/api/auth/register", json=REGISTER).json()["access_token"]
    old = {"Authorization": f"Bearer {old_token}"}
    assert client.get("/api/auth/me", headers=old).status_code == 200
    changed = client.post(
        "/api/account/password",
        headers=old,
        json={"current_password": "segura-123", "new_password": "nueva-123", "confirm_password": "nueva-123"},
    )
    assert changed.status_code == 200
    response = client.get("/api/auth/me", headers=old)
    assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_token"
    new = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new).status_code == 200


def test_password_reset_invalidates_issued_access_tokens(
    as_superadmin: TestClient, client: TestClient, db: Session, seeded: dict
) -> None:
    member = db.get(User, seeded["member_id"])
    token = {"Authorization": f"Bearer {create_access_token(member)}"}
    assert client.get("/api/auth/me", headers=token).status_code == 200
    assert as_superadmin.post(f"/api/admin/users/{member.id}/reset-password").status_code == 200
    assert client.get("/api/auth/me", headers=token).status_code == 401


def test_login_is_rate_limited_per_email_across_ips(client: TestClient, db: Session) -> None:
    from app.db import get_db
    from app.main import app

    make_user(db, email="m@ipn.mx")
    app.dependency_overrides[get_db] = lambda: db
    statuses = []
    for n, email in enumerate(["m@ipn.mx", "M@ipn.mx", "m@IPN.mx", "m@ipn.mx", "M@IPN.MX", "m@ipn.mx"]):
        with TestClient(app, headers={"X-Requested-With": "fetch"}, client=(f"10.0.0.{n}", 1)) as other_ip:
            response = other_ip.post("/api/auth/login", json={"email": email, "password": "mal"})
            statuses.append(response.status_code)
    assert statuses == [401] * 5 + [429]
    assert _login(client, "otra@ipn.mx", "x").status_code == 401  # other accounts are not affected


def test_login_and_register_require_fetch_header(client: TestClient, db: Session) -> None:
    make_user(db, email="m@ipn.mx")
    no_header = {"X-Requested-With": ""}
    credentials = {"email": "m@ipn.mx", "password": "password123"}
    login = client.post("/api/auth/login", json=credentials, headers=no_header)
    register = client.post("/api/auth/register", json=REGISTER, headers=no_header)
    assert (login.status_code, register.status_code) == (403, 403)
    assert login.json()["error"]["code"] == register.json()["error"]["code"] == "csrf"


@pytest.fixture
def password_change_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "require_password_change", True)


@pytest.mark.usefixtures("password_change_required")
def test_provisional_password_must_be_changed_first(client: TestClient, db: Session, seeded: dict) -> None:
    token = _login(client, "alumno.demo@upiixsol.dev", "admin123").json()["access_token"]
    member = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=member).json()["must_change_password"] is True
    blocked = (("GET", "/api/channels"), ("PATCH", "/api/account/profile"), ("GET", "/api/academies/upiixia"))
    for method, path in blocked:
        response = client.request(method, path, headers=member, json={})
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "password_change_required"
    assert client.get("/api/academies/upiixia").status_code == 200  # anonymous pages are not affected
    changed = client.post(
        "/api/account/password",
        headers=member,
        json={"current_password": "admin123", "new_password": "propia-123", "confirm_password": "propia-123"},
    )
    assert changed.status_code == 200 and changed.json()["user"]["must_change_password"] is False
    fresh = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert client.get("/api/channels", headers=fresh).status_code == 200
    assert client.post("/api/auth/refresh").status_code == 200  # refresh and logout stay open
    assert client.post("/api/auth/logout").status_code == 204


def test_demo_mode_skips_the_required_change(as_member: TestClient) -> None:
    assert get_settings().require_password_change is False  # conftest: REQUIRE_PASSWORD_CHANGE=false
    assert as_member.get("/api/channels").status_code == 200
