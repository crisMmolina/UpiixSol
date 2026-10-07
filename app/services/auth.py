"""Registration, login and refresh-token rotation (ADR 0001).

Refresh tokens: random, stored as sha256, rotated on every use. Reusing an already-used token
means it was stolen, so the whole family is revoked (the user must log in again).
"""

import secrets
import unicodedata
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError
from app.models import Academy, RefreshToken, Role, User
from app.models.common import utcnow
from app.schemas.users import LoginIn, RegisterIn, TokenOut, UserMe
from app.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)

INVALID_CREDENTIALS = "Correo o contraseña incorrectos."
DUPLICATE_ACCOUNT = "Ya existe una cuenta con ese correo o esa boleta. Inicia sesión o recupera tu acceso."


def _aware(moment: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def default_nickname(full_name: str) -> str:
    first = full_name.strip().split()[0] if full_name.strip() else "miembro"
    ascii_name = unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode().lower()
    nickname = "".join(c for c in ascii_name if c.isalnum())[:40]
    return nickname if len(nickname) >= 2 else "miembro"


def user_me(db: Session, user: User) -> UserMe:
    slug = db.scalar(select(Academy.slug).where(Academy.id == user.academy_id)) if user.academy_id else None
    return UserMe.model_validate(user).model_copy(update={"academy_slug": slug})


def register_member(db: Session, data: RegisterIn) -> User:
    exists = db.scalar(
        select(User.id).where(or_(User.email == data.email, User.boleta == data.boleta)).limit(1)
    )
    if exists:
        raise AppError(409, DUPLICATE_ACCOUNT, code="account_exists")
    user = User(
        role=Role.member,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        nickname=data.nickname or default_nickname(data.full_name),
        boleta=data.boleta,
    )
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, data: LoginIn) -> User:
    user = db.scalar(select(User).where(User.email == data.email))
    # verify_password runs even for unknown emails (dummy hash) so timing does not reveal accounts.
    if not verify_password(user.password_hash if user else None, data.password) or user is None:
        raise AppError(401, INVALID_CREDENTIALS, code="invalid_credentials")
    if not user.is_active:
        raise AppError(401, INVALID_CREDENTIALS, code="invalid_credentials")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    return user


def _store_refresh(db: Session, user: User, family_id: str) -> str:
    raw, hashed = new_refresh_token()
    expires = utcnow() + timedelta(days=get_settings().jwt_refresh_days)
    db.add(RefreshToken(user_id=user.id, token_hash=hashed, family_id=family_id, expires_at=expires))
    db.flush()
    return raw


def issue_session(db: Session, user: User, family_id: str | None = None) -> tuple[TokenOut, str]:
    """Access token (body) + new refresh token (cookie)."""
    raw = _store_refresh(db, user, family_id or secrets.token_hex(16))
    token = TokenOut(
        access_token=create_access_token(user),
        expires_in=get_settings().jwt_access_minutes * 60,
        user=user_me(db, user),
    )
    return token, raw


def revoke_family(db: Session, family_id: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.flush()


def rotate_refresh(db: Session, raw: str | None) -> tuple[TokenOut, str]:
    """Consume a refresh token and issue the next one of the same family. 401 on any problem."""
    stored = (
        db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))) if raw else None
    )
    if stored is None:
        raise AppError(401, code="invalid_refresh")
    if stored.used_at is not None or stored.revoked_at is not None:
        revoke_family(db, stored.family_id)  # replay of a used token → assume theft
        db.commit()
        raise AppError(401, code="invalid_refresh")
    if _aware(stored.expires_at) <= utcnow():
        raise AppError(401, code="invalid_refresh")
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        revoke_family(db, stored.family_id)
        db.commit()
        raise AppError(401, code="invalid_refresh")
    stored.used_at = utcnow()
    return issue_session(db, user, stored.family_id)


def logout(db: Session, raw: str | None) -> None:
    if not raw:
        return
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if stored is not None:
        revoke_family(db, stored.family_id)


def revoke_all_for_user(db: Session, user_id: int) -> None:
    """Used after a password change (UPS-014)."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.flush()
