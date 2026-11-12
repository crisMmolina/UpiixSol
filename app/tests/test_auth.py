import os
import threading
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.errors import AppError
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
    assert response.json()["error"]["message"] == "Boleta, correo o contraseña incorrectos."


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
    used, current = sorted(db.scalars(select(RefreshToken)), key=lambda t: t.id)
    assert used.revoked_at is not None  # the used token retires…
    assert current.revoked_at is None  # …and the family stays


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


def test_new_token_after_password_change_works_in_a_fresh_session(client: TestClient, db: Session) -> None:
    """Each request normally gets its own session: the token issued by the change must carry the new stamp."""
    user = make_user(db, email="m@ipn.mx")
    db.commit()
    old = {"Authorization": f"Bearer {create_access_token(user)}"}
    change = {"current_password": "password123", "new_password": "nueva-123", "confirm_password": "nueva-123"}
    changed = client.post("/api/account/password", headers=old, json=change)
    assert changed.status_code == 200
    db.expire_all()  # what a new request would see: the row as stored
    new = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new).status_code == 200
    assert client.get("/api/auth/me", headers=old).status_code == 401


# ── Session lifetime and replays (UPS-020, security review) ──


def test_a_second_late_reuse_of_a_token_revokes_the_family(client: TestClient, db: Session) -> None:
    """One concurrent tab is tolerated; a second request with the same used token is a stolen cookie."""
    old_raw = client.post("/api/auth/register", json=REGISTER).cookies[REFRESH_COOKIE]
    new_raw = client.post("/api/auth/refresh").cookies[REFRESH_COOKIE]
    client.cookies.set(REFRESH_COOKIE, old_raw, path="/api/auth")
    assert client.post("/api/auth/refresh").json()["error"]["code"] == "refresh_race"
    client.cookies.set(REFRESH_COOKIE, old_raw, path="/api/auth")
    again = client.post("/api/auth/refresh")
    assert again.status_code == 401 and again.json()["error"]["code"] == "invalid_refresh"
    assert all(t.revoked_at is not None for t in db.scalars(select(RefreshToken)))
    client.cookies.set(REFRESH_COOKIE, new_raw, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401  # the thief's rotation died with the family


def test_rotation_keeps_the_family_expiry_from_the_login(client: TestClient, db: Session) -> None:
    """A family lives jwt_refresh_days from the login: rotating it never pushes that date forward."""
    client.post("/api/auth/register", json=REGISTER)
    login_expiry = db.scalar(select(RefreshToken.expires_at))
    for _ in range(3):
        assert client.post("/api/auth/refresh").status_code == 200
    tokens = list(db.scalars(select(RefreshToken)))
    assert len(tokens) == 4 and {t.expires_at for t in tokens} == {login_expiry}

    current = max(tokens, key=lambda t: t.id)
    current.expires_at = utcnow() - timedelta(seconds=1)  # the 7 days since the login are over
    db.flush()
    assert client.post("/api/auth/refresh").json()["error"]["code"] == "invalid_refresh"
    assert _login(client).status_code == 200  # a new login starts a new family with the full lifetime
    newest = db.scalar(select(RefreshToken).order_by(RefreshToken.id.desc()).limit(1))
    assert newest.expires_at > utcnow() + timedelta(days=get_settings().jwt_refresh_days - 1)


def test_refresh_and_password_change_lock_the_user_row(client: TestClient, db: Session) -> None:
    """Both take SELECT … FOR UPDATE on the user before touching tokens (rendered on Postgres only)."""
    locks: list[str] = []

    @event.listens_for(db, "do_orm_execute")
    def _capture(state) -> None:
        sql = str(state.statement.compile(dialect=postgresql.dialect()))
        if "FOR UPDATE" in sql and "FROM users" in sql:
            locks.append(sql)

    client.post("/api/auth/register", json=REGISTER)
    assert client.post("/api/auth/refresh").status_code == 200
    assert len(locks) == 1
    user = db.scalar(select(User))
    auth_service.revoke_all_for_user(db, user.id)
    assert len(locks) == 2


PG_URL = os.environ.get("DATABASE_URL", "")


@pytest.mark.skipif(not PG_URL.startswith("postgresql"), reason="row locks need Postgres (backend-postgres)")
@pytest.mark.parametrize("refresh_first", [True, False], ids=["refresh-first", "change-first"])
def test_refresh_racing_a_password_change_leaves_no_live_token(refresh_first: bool) -> None:
    """Two real connections: whichever commits first, the password change ends every session."""
    engine = create_engine(PG_URL)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with sessions() as setup:
        user = make_user(setup, email=f"race-{refresh_first}@upiixsol.dev".lower())
        _, raw = auth_service.issue_session(setup, user)
        setup.commit()
        user_id = user.id
    refresher, changer = sessions(), sessions()
    outcome: dict[str, str] = {}

    def refresh() -> None:
        try:
            auth_service.rotate_refresh(refresher, raw)
            refresher.commit()
            outcome["refresh"] = "ok"
        except AppError as error:
            refresher.rollback()
            outcome["refresh"] = error.code

    def change() -> None:
        auth_service.revoke_all_for_user(changer, user_id)
        changer.commit()

    second, holder = (change, refresher) if refresh_first else (refresh, changer)
    try:
        if refresh_first:
            auth_service.rotate_refresh(refresher, raw)  # holds the lock, new token not committed yet
        else:
            auth_service.revoke_all_for_user(changer, user_id)
        waiter = threading.Thread(target=second)
        waiter.start()
        waiter.join(0.5)
        assert waiter.is_alive()  # blocked on the user's row lock
        holder.commit()
        waiter.join(10)
        assert not waiter.is_alive()
        if not refresh_first:
            assert outcome["refresh"] == "invalid_refresh"
        with sessions() as check:
            live = select(RefreshToken).filter_by(user_id=user_id, revoked_at=None)
            assert check.scalars(live).all() == []
    finally:
        refresher.close()
        changer.close()
        with sessions() as cleanup:
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()
        engine.dispose()


# ── Sign in with boleta or email (UPS-044) ────────────────────


def _login_as(client: TestClient, identifier: str, password: str = "password123"):  # noqa: S107
    return client.post("/api/auth/login", json={"identifier": identifier, "password": password})


def test_login_with_boleta(client: TestClient, db: Session) -> None:
    make_user(db, email="ana@ipn.mx", boleta="2026000123")
    response = _login_as(client, "2026000123")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "ana@ipn.mx"


def test_login_with_email_in_the_identifier_field(client: TestClient, db: Session) -> None:
    """Superadmins and club admins have no boleta: they keep signing in with their email."""
    make_user(db, role=Role.superadmin, email="root@upiixsol.dev")
    response = _login_as(client, "  ROOT@upiixsol.dev ")
    assert response.status_code == 200 and response.json()["user"]["role"] == "superadmin"


def test_login_legacy_email_key_still_works(client: TestClient, db: Session) -> None:
    make_user(db, email="m@ipn.mx")
    assert _login(client, "m@ipn.mx", "password123").status_code == 200


@pytest.mark.parametrize(
    ("identifier", "password"),
    [
        ("2026999999", "password123"),
        ("2026000123", "incorrecta"),
        ("nadie@ipn.mx", "password123"),
        ("abc", "x"),
    ],
)
def test_login_boleta_and_email_errors_are_identical(
    client: TestClient, db: Session, identifier: str, password: str
) -> None:
    make_user(db, email="ana@ipn.mx", boleta="2026000123")
    response = _login_as(client, identifier, password)
    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "invalid_credentials",
        "message": "Boleta, correo o contraseña incorrectos.",
        "details": None,
    }


@pytest.mark.parametrize("body", [{"password": "x"}, {"identifier": "   ", "password": "x"}])
def test_login_requires_an_identifier(client: TestClient, body: dict) -> None:
    assert client.post("/api/auth/login", json=body).status_code == 422


def test_login_is_rate_limited_per_boleta_across_ips(client: TestClient, db: Session) -> None:
    from app.db import get_db
    from app.main import app

    make_user(db, email="ana@ipn.mx", boleta="2026000123")
    app.dependency_overrides[get_db] = lambda: db
    statuses = []
    for n in range(6):
        with TestClient(app, headers={"X-Requested-With": "fetch"}, client=(f"10.0.1.{n}", 1)) as other_ip:
            response = other_ip.post("/api/auth/login", json={"identifier": " 2026000123", "password": "mal"})
            statuses.append(response.status_code)
    assert statuses == [401] * 5 + [429]


def test_login_with_boleta_follows_the_provisional_password_rule(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "require_password_change", True)
    user = make_user(db, email="nuevo@ipn.mx", boleta="2026000777")
    user.must_change_password = True
    db.flush()
    response = _login_as(client, "2026000777")
    assert response.status_code == 200 and response.json()["user"]["must_change_password"] is True


def test_register_duplicate_boleta_with_another_email_is_generic_409(client: TestClient, db: Session) -> None:
    make_user(db, email="primera@ipn.mx", boleta=REGISTER["boleta"])
    response = client.post("/api/auth/register", json={**REGISTER, "email": "segunda@ipn.mx"})
    assert response.status_code == 409 and response.json()["error"]["code"] == "account_exists"
    assert db.scalar(select(User).filter_by(email="segunda@ipn.mx")) is None


def test_concurrent_register_with_the_same_boleta_creates_one_account(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both requests pass the existence check; the unique boleta index rejects the second insert."""
    make_user(db, email="primera@ipn.mx", boleta=REGISTER["boleta"])
    monkeypatch.setattr(db, "scalar", lambda *args, **kwargs: None)  # the check ran before the other insert
    response = client.post("/api/auth/register", json={**REGISTER, "email": "segunda@ipn.mx"})
    monkeypatch.undo()
    assert response.status_code == 409 and response.json()["error"]["code"] == "account_exists"
    assert len(db.scalars(select(User).filter_by(boleta=REGISTER["boleta"])).all()) == 1


def test_superadmin_cannot_create_a_user_with_a_taken_boleta(as_superadmin: TestClient, seeded: dict) -> None:
    response = as_superadmin.post(
        "/api/admin/users",
        json={
            "full_name": "Otra Persona",
            "email": "otra.persona@upiixsol.dev",
            "boleta": "2026000001",  # alumno.demo's
            "role": "member",
            "password": "temporal-123",
        },
    )
    assert response.status_code == 409

