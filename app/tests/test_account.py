import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models import RefreshToken, User
from app.security import verify_password
from app.tests.conftest import make_user

PASSWORD = "password123"  # noqa: S105 (test fixture)


@pytest.fixture
def account(db: Session) -> User:
    return make_user(db, email="cuenta@upiixsol.dev", boleta="2026000777", password=PASSWORD)


@pytest.fixture
def session_client(db: Session, account: User) -> Iterator[TestClient]:
    """Logged in through /api/auth/login over https, so the Secure refresh cookie travels."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, base_url="https://testserver", headers={"X-Requested-With": "fetch"}) as client:
        token = client.post("/api/auth/login", json={"email": account.email, "password": PASSWORD}).json()
        client.headers["Authorization"] = f"Bearer {token['access_token']}"
        yield client
    app.dependency_overrides.pop(get_db, None)


def _png(size: int = 600) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (size, size), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def test_requires_login(client: TestClient) -> None:
    assert client.patch("/api/account/profile", json={"nickname": "nuevo"}).status_code == 401
    assert client.post("/api/account/password", json={}).status_code == 401


def test_update_profile(session_client: TestClient) -> None:
    body = session_client.patch(
        "/api/account/profile", json={"nickname": "Cris", "full_name": "Cris Molina"}
    ).json()
    assert body["nickname"] == "Cris" and body["full_name"] == "Cris Molina"
    # null fields are ignored; unknown fields (e.g. role) are rejected
    assert session_client.patch("/api/account/profile", json={"nickname": None}).json()["nickname"] == "Cris"
    assert session_client.patch("/api/account/profile", json={"role": "superadmin"}).status_code == 422
    assert session_client.patch("/api/account/profile", json={"nickname": "x"}).status_code == 422


def test_upload_avatar_resizes_and_replaces(session_client: TestClient, db: Session, account: User) -> None:
    first = session_client.post("/api/account/avatar", files={"file": ("a.png", _png(), "image/png")})
    assert first.status_code == 200
    url = first.json()["avatar_url"]
    assert url.startswith("/media/avatar/") and url.endswith(".webp")
    image = session_client.get(url)
    with Image.open(io.BytesIO(image.content)) as stored:
        assert max(stored.size) <= 256
    second = session_client.post(
        "/api/account/avatar", files={"file": ("b.png", _png(100), "image/png")}
    ).json()
    assert second["avatar_url"] != url
    assert session_client.get(url).status_code == 404  # the previous file was removed
    bad = session_client.post("/api/account/avatar", files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 422


def test_avatar_db_failure_removes_new_file(
    session_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import account as service

    removed: list[str | None] = []
    monkeypatch.setattr(service.media, "delete_media", removed.append)

    def boom() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "commit", boom)
    response = session_client.post("/api/account/avatar", files={"file": ("a.png", _png(), "image/png")})
    assert response.status_code == 500
    assert removed and removed[0].startswith("/media/avatar/")


def test_change_email_requires_current_password(session_client: TestClient, db: Session) -> None:
    wrong = session_client.post(
        "/api/account/email", json={"new_email": "nuevo@upiixsol.dev", "current_password": "incorrecta"}
    )
    assert wrong.status_code == 422 and wrong.json()["error"]["code"] == "wrong_password"
    ok = session_client.post(
        "/api/account/email", json={"new_email": "Nuevo@UpiixSol.dev", "current_password": PASSWORD}
    )
    assert ok.status_code == 200 and ok.json()["email"] == "nuevo@upiixsol.dev"
    same = session_client.post(
        "/api/account/email", json={"new_email": "nuevo@upiixsol.dev", "current_password": PASSWORD}
    )
    assert same.status_code == 200
    make_user(db, email="otra@upiixsol.dev")
    taken = session_client.post(
        "/api/account/email", json={"new_email": "otra@upiixsol.dev", "current_password": PASSWORD}
    )
    assert taken.status_code == 409


def test_change_email_concurrent_duplicate_is_409(
    session_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(db, email="otra@upiixsol.dev")
    original_scalar = db.scalar
    monkeypatch.setattr(
        db,
        "scalar",
        lambda stmt, *a, **k: None if "users.email" in str(stmt) else original_scalar(stmt, *a, **k),
    )
    taken = session_client.post(
        "/api/account/email", json={"new_email": "otra@upiixsol.dev", "current_password": PASSWORD}
    )
    assert taken.status_code == 409


def test_change_password_requires_current(session_client: TestClient) -> None:
    payload = {
        "current_password": "incorrecta",
        "new_password": "nueva-clave-1",
        "confirm_password": "nueva-clave-1",
    }
    response = session_client.post("/api/account/password", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["loc"] == ["body", "current_password"]
    mismatch = {**payload, "current_password": PASSWORD, "confirm_password": "otra-clave-2"}
    assert (
        session_client.post("/api/account/password", json=mismatch).json()["error"]["code"]
        == "password_mismatch"
    )
    same = {"current_password": PASSWORD, "new_password": PASSWORD, "confirm_password": PASSWORD}
    assert session_client.post("/api/account/password", json=same).json()["error"]["code"] == "same_password"
    short = {**payload, "current_password": PASSWORD, "new_password": "corta", "confirm_password": "corta"}
    assert session_client.post("/api/account/password", json=short).status_code == 422


def test_change_password_revokes_sessions_and_clears_flag(
    session_client: TestClient, db: Session, account: User
) -> None:
    account.must_change_password = True
    db.flush()
    old_cookie = session_client.cookies.get("upx_refresh")
    payload = {
        "current_password": PASSWORD,
        "new_password": "nueva-clave-1",
        "confirm_password": "nueva-clave-1",
    }
    response = session_client.post("/api/account/password", json=payload)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["access_token"] and body["user"]["must_change_password"] is False
    new_cookie = session_client.cookies.get("upx_refresh")
    assert new_cookie and new_cookie != old_cookie
    db.refresh(account)
    assert verify_password(account.password_hash, "nueva-clave-1")
    tokens = db.scalars(select(RefreshToken).where(RefreshToken.user_id == account.id)).all()
    assert sum(t.revoked_at is None for t in tokens) == 1  # only this device's new session
    # The old refresh token is dead; this device keeps working with the new one.
    session_client.cookies.clear()
    session_client.cookies.set("upx_refresh", old_cookie, domain="testserver.local", path="/api/auth")
    assert session_client.post("/api/auth/refresh").status_code == 401
    session_client.cookies.clear()
    session_client.cookies.set("upx_refresh", new_cookie, domain="testserver.local", path="/api/auth")
    login = session_client.post("/api/auth/login", json={"email": account.email, "password": "nueva-clave-1"})
    assert login.status_code == 200


def test_password_attempts_are_rate_limited_per_user(session_client: TestClient) -> None:
    payload = {
        "current_password": "incorrecta",
        "new_password": "nueva-clave-1",
        "confirm_password": "nueva-clave-1",
    }
    codes = [session_client.post("/api/account/password", json=payload).status_code for _ in range(6)]
    assert codes[:5] == [422] * 5 and codes[5] == 429


def test_avatar_uploads_are_rate_limited_per_user(session_client: TestClient) -> None:
    codes = [
        session_client.post(
            "/api/account/avatar", files={"file": ("a.png", _png(20), "image/png")}
        ).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [200] * 10 and codes[10] == 429
