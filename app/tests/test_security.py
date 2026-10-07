from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError, register_error_handlers
from app.models import Academy, Role, User
from app.security import (
    JWT_ALGORITHM,
    can_manage_academy,
    create_access_token,
    current_user,
    decode_access_token,
    ensure_academy_scope,
    hash_password,
    hash_token,
    new_refresh_token,
    optional_user,
    password_needs_rehash,
    require_role,
    verify_password,
)
from app.tests.conftest import auth_headers, make_academy, make_user


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("correcto-123")
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "correcto-123")
    assert not verify_password(hashed, "incorrecto")
    assert not verify_password(None, "cualquiera")
    assert not verify_password("not-a-hash", "x")
    assert password_needs_rehash(hashed) is False


def test_access_token_roundtrip_and_expiry(db: Session, member: User) -> None:
    payload = decode_access_token(create_access_token(member))
    assert payload["sub"] == str(member.id) and payload["role"] == "member" and payload["type"] == "access"

    expired = create_access_token(member, now=datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(AppError) as error:
        decode_access_token(expired)
    assert error.value.status == 401


def test_token_with_wrong_type_or_secret_is_rejected(member: User) -> None:
    secret = get_settings().jwt_secret
    now = datetime.now(UTC)
    refresh_like = jwt.encode(
        {"sub": "1", "type": "refresh", "exp": now + timedelta(minutes=5)}, secret, algorithm=JWT_ALGORITHM
    )
    forged = jwt.encode(
        {"sub": "1", "type": "access", "exp": now + timedelta(minutes=5)}, "x" * 40, algorithm=JWT_ALGORITHM
    )
    for token in (refresh_like, forged, "garbage"):
        with pytest.raises(AppError):
            decode_access_token(token)


def test_refresh_tokens_are_random_and_hashed() -> None:
    raw1, hashed1 = new_refresh_token()
    raw2, _ = new_refresh_token()
    assert raw1 != raw2 and len(raw1) >= 60
    assert hashed1 == hash_token(raw1) and raw1 not in hashed1 and len(hashed1) == 64


def test_academy_scope(db: Session) -> None:
    ia = make_academy(db, "upiixia")
    robo = make_academy(db, "robotica", "UpiixRobótica")
    superadmin = make_user(db, role=Role.superadmin, email="s@upiixsol.dev")
    admin_ia = make_user(db, role=Role.academy_admin, email="a@upiixsol.dev", academy_id=ia.id)
    member = make_user(db, email="m@upiixsol.dev")

    assert can_manage_academy(superadmin, robo.id) and can_manage_academy(superadmin, None)
    assert can_manage_academy(admin_ia, ia.id)
    assert not can_manage_academy(admin_ia, robo.id)
    assert not can_manage_academy(admin_ia, None)  # global content is superadmin-only
    assert not can_manage_academy(member, ia.id)
    with pytest.raises(AppError) as error:
        ensure_academy_scope(admin_ia, robo.id)
    assert error.value.status == 403
    ensure_academy_scope(admin_ia, ia.id)


@pytest.fixture
def probe(db: Session) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.dependency_overrides[get_db] = lambda: db

    @app.get("/me")
    def me(user: User = Depends(current_user)) -> dict:
        return {"id": user.id}

    @app.get("/maybe")
    def maybe(user: User | None = Depends(optional_user)) -> dict:
        return {"id": user.id if user else None}

    @app.get("/admin")
    def admin(user: User = Depends(require_role(Role.superadmin))) -> dict:
        return {"id": user.id}

    return TestClient(app)


def test_dependencies_enforce_auth_and_roles(probe: TestClient, db: Session, academy: Academy) -> None:
    member = make_user(db, email="m@upiixsol.dev")
    superadmin = make_user(db, role=Role.superadmin, email="s@upiixsol.dev")
    inactive = make_user(db, email="off@upiixsol.dev", is_active=False)

    assert probe.get("/me").status_code == 401
    assert probe.get("/maybe").json() == {"id": None}
    assert probe.get("/me", headers=auth_headers(member)).json() == {"id": member.id}
    assert probe.get("/maybe", headers=auth_headers(member)).json() == {"id": member.id}
    assert probe.get("/admin", headers=auth_headers(member)).status_code == 403
    assert probe.get("/admin", headers=auth_headers(superadmin)).json() == {"id": superadmin.id}
    assert probe.get("/me", headers=auth_headers(inactive)).status_code == 401
    assert (
        probe.get("/me", headers={"Authorization": "Bearer nope"}).json()["error"]["code"] == "invalid_token"
    )


def test_deleted_user_token_is_rejected(probe: TestClient, db: Session) -> None:
    ghost = make_user(db, email="ghost@upiixsol.dev")
    headers = auth_headers(ghost)
    db.delete(ghost)
    db.flush()
    assert probe.get("/me", headers=headers).status_code == 401
