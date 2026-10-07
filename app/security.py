"""Passwords, tokens and the authorization dependencies every router uses (owner UPS-002).

    user: User = Depends(current_user)                       # 401 if anonymous/inactive
    user: User = Depends(require_role(Role.superadmin))      # 403 otherwise
    ensure_academy_scope(user, academy_id)                   # 403 unless superadmin or admin of that academy

Always resolve `academy_id` from the database row being changed, never from the request body.
"""

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError
from app.models import Role, User

JWT_ALGORITHM = "HS256"
_hasher = PasswordHasher()  # argon2id with OWASP-aligned defaults
_bearer = HTTPBearer(auto_error=False)
# Verifying against a dummy hash when the user does not exist keeps login timing uniform.
_DUMMY_HASH = _hasher.hash("timing-equalizer-not-a-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(user: User, *, now: datetime | None = None) -> str:
    settings = get_settings()
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "academy_id": user.academy_id,
        "type": "access",
        "iat": issued,
        "exp": issued + timedelta(minutes=settings.jwt_access_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise AppError(401, "Tu sesión expiró. Inicia sesión de nuevo.", code="invalid_token") from exc
    if payload.get("type") != "access":
        raise AppError(401, code="invalid_token")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw token for the cookie, sha256 hash for the DB)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AppError(401, code="invalid_token")
    request.state.user_id = user.id  # for the access log (never email/boleta)
    return user


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise AppError(401)
    return user


def require_role(*roles: Role) -> Callable[..., User]:
    allowed = set(roles)

    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise AppError(403)
        return user

    return dependency


def can_manage_academy(user: User, academy_id: int | None) -> bool:
    if user.role == Role.superadmin:
        return True
    return user.role == Role.academy_admin and academy_id is not None and user.academy_id == academy_id


def ensure_academy_scope(user: User, academy_id: int | None) -> None:
    """403 unless the user is a superadmin or the admin of exactly this academy."""
    if not can_manage_academy(user, academy_id):
        raise AppError(403)


# Name used in the spec/plan.
require_academy_scope = ensure_academy_scope
