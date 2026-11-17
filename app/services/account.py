"""My account (IDEA §2.3): profile, avatar, email and password. Email and password changes require the
current password; a password change revokes every refresh session and clears must_change_password."""

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import User
from app.schemas.users import EmailChangeIn, PasswordChangeIn, ProfileUpdateIn, TokenOut, UserMe
from app.security import hash_password, verify_password
from app.services import media
from app.services.auth import issue_session, revoke_all_for_user, user_me
from app.services.nicknames import ensure_available

EMAIL_TAKEN = "Ese correo ya está registrado."


def _field_error(code: str, field: str, message: str) -> AppError:
    """Same details shape as validation errors, so the form shows it under the field."""
    return AppError(422, message, code=code, details=[{"loc": ["body", field], "msg": message}])


def _check_current(user: User, password: str) -> None:
    if not verify_password(user.password_hash, password):
        raise _field_error("wrong_password", "current_password", "La contraseña actual no es correcta.")


def update_profile(db: Session, user: User, data: ProfileUpdateIn) -> UserMe:
    if data.nickname:
        ensure_available(db, data.nickname, user_id=user.id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    db.flush()
    return user_me(db, user)


async def upload_avatar(db: Session, user: User, file: UploadFile) -> UserMe:
    url = await media.save_upload(file, "avatar")
    previous = user.avatar_url
    try:
        user.avatar_url = url
        db.commit()
    except Exception:
        db.rollback()
        media.delete_media(url)
        raise
    media.delete_media(previous)
    return user_me(db, user)


def change_email(db: Session, user: User, data: EmailChangeIn) -> UserMe:
    _check_current(user, data.current_password)
    if data.new_email == user.email:
        return user_me(db, user)
    if db.scalar(select(User.id).where(User.email == data.new_email)):
        raise AppError(409, EMAIL_TAKEN, code="email_taken")
    try:
        with db.begin_nested():  # a concurrent change to the same email is a 409, not a 500
            user.email = data.new_email
            db.flush()
    except IntegrityError as exc:
        raise AppError(409, EMAIL_TAKEN, code="email_taken") from exc
    return user_me(db, user)


def change_password(db: Session, user: User, data: PasswordChangeIn) -> tuple[TokenOut, str]:
    """Returns a fresh session for this device: every other session (refresh token) is revoked."""
    _check_current(user, data.current_password)
    if data.new_password != data.confirm_password:
        raise _field_error("password_mismatch", "confirm_password", "Las contraseñas no coinciden.")
    if verify_password(user.password_hash, data.new_password):
        raise _field_error("same_password", "new_password", "Usa una contraseña distinta de la actual.")
    user.password_hash = hash_password(data.new_password)
    user.must_change_password = False
    revoke_all_for_user(db, user.id)
    return issue_session(db, user)
