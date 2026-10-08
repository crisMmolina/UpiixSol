"""Superadmin panel (flow step 6): academies, users and the campus home page."""

import secrets

from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Academy, Channel, ChannelType, HomeContent, Role, User
from app.sanitize import clean_markdown
from app.schemas.academies import AcademyCreateIn, AcademyOut, AcademyUpdateIn, HomeContentIn, HomeContentOut
from app.schemas.users import AdminUserCreateIn, AdminUserUpdateIn, PasswordResetOut, UserAdminOut
from app.security import hash_password
from app.services.auth import default_nickname, revoke_all_for_user

RESERVED_SLUGS = {"feed", "general"}  # community channel slugs share the namespace


def _conflict(message: str) -> AppError:
    return AppError(409, message, code="conflict")


def _invalid(message: str) -> AppError:
    return AppError(422, message, code="invalid")


# ── Academies ────────────────────────────────────────────────


def _slug_taken(db: Session, slug: str) -> bool:
    return slug in RESERVED_SLUGS or bool(
        db.scalar(select(Academy.id).where(Academy.slug == slug))
        or db.scalar(select(Channel.id).where(Channel.slug == slug))
    )


def create_academy(db: Session, data: AcademyCreateIn) -> AcademyOut:
    message = "Ese identificador (slug) ya está en uso."
    if _slug_taken(db, data.slug):
        raise _conflict(message)
    values = data.model_dump()
    values["welcome_text"] = clean_markdown(values["welcome_text"])
    academy = Academy(**values)
    try:
        # Savepoint: a concurrent create with the same slug is a 409, not a 500 (security review UPS-009).
        with db.begin_nested():
            db.add(academy)
            db.flush()
            # Same transaction: every academy has its community channel (IDEA §6).
            db.add(
                Channel(type=ChannelType.academy, academy_id=academy.id, name=academy.name, slug=academy.slug)
            )
            db.flush()
    except IntegrityError as exc:
        raise _conflict(message) from exc
    return AcademyOut.model_validate(academy)


def update_academy(db: Session, academy_id: int, data: AcademyUpdateIn) -> AcademyOut:
    academy = db.get(Academy, academy_id)
    if academy is None:
        raise AppError(404, "No encontramos ese club.")
    values = data.model_dump(exclude_unset=True)
    if values.get("welcome_text") is not None:
        values["welcome_text"] = clean_markdown(values["welcome_text"])
    for field, value in values.items():
        if value is None and field != "color_accent_2":
            continue
        setattr(academy, field, value)
    if "name" in values and values["name"]:
        channel = db.scalar(select(Channel).where(Channel.academy_id == academy.id))
        if channel is not None:
            channel.name = values["name"]
    db.flush()
    return AcademyOut.model_validate(academy)


def academies_stmt() -> Select:
    return select(Academy)


# ── Users ────────────────────────────────────────────────────


def users_stmt(role: Role | None, academy_id: int | None, q: str | None) -> Select:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if academy_id is not None:
        stmt = stmt.where(User.academy_id == academy_id)
    if q and q.strip():
        # LIKE wildcards in the search are literal characters (security review UPS-009).
        escaped = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        needle = f"%{escaped}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(needle, escape="\\"),
                User.full_name.ilike(needle, escape="\\"),
                User.nickname.ilike(needle, escape="\\"),
                User.boleta.like(needle, escape="\\"),
            )
        )
    return stmt


def _check_academy(db: Session, academy_id: int | None) -> None:
    academy = db.get(Academy, academy_id) if academy_id is not None else None
    if academy is None or not academy.is_active:
        raise _invalid("Elige un club activo para el admin.")


def _user_exists(db: Session, email: str, boleta: str | None) -> bool:
    clauses = [User.email == email]
    if boleta:
        clauses.append(User.boleta == boleta)
    return bool(db.scalar(select(User.id).where(or_(*clauses)).limit(1)))


def create_user(db: Session, data: AdminUserCreateIn) -> UserAdminOut:
    message = "Ya existe un usuario con ese correo o esa boleta."
    if data.role == Role.academy_admin:
        _check_academy(db, data.academy_id)
    if _user_exists(db, data.email, data.boleta):
        raise _conflict(message)
    user = User(
        role=data.role,
        email=data.email,
        full_name=data.full_name,
        nickname=data.nickname or default_nickname(data.full_name),
        boleta=data.boleta,
        academy_id=data.academy_id if data.role == Role.academy_admin else None,
        password_hash=hash_password(data.password),
        must_change_password=True,
    )
    try:
        with db.begin_nested():  # concurrent duplicate → 409, not 500
            db.add(user)
            db.flush()
    except IntegrityError as exc:
        raise _conflict(message) from exc
    return UserAdminOut.model_validate(user)


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "No encontramos ese usuario.")
    return user


def update_user(db: Session, actor: User, user_id: int, data: AdminUserUpdateIn) -> UserAdminOut:
    user = _get_user(db, user_id)
    values = data.model_dump(exclude_unset=True)
    if values.get("is_active") is False and user.id == actor.id:
        raise _invalid("No puedes desactivar tu propia cuenta.")
    if "academy_id" in values:
        if user.role != Role.academy_admin:
            raise _invalid("Solo los admins de club tienen un club asignado.")
        _check_academy(db, values["academy_id"])
    for field, value in values.items():
        if value is not None:
            setattr(user, field, value)
    if values.get("is_active") is False:
        revoke_all_for_user(db, user.id)
    db.flush()
    return UserAdminOut.model_validate(user)


def reset_password(db: Session, user_id: int) -> PasswordResetOut:
    """No email in v1 (IDEA §7): the superadmin hands the temporary password to the person."""
    user = _get_user(db, user_id)
    temporary = secrets.token_urlsafe(9)  # 12 chars
    user.password_hash = hash_password(temporary)
    user.must_change_password = True
    revoke_all_for_user(db, user.id)
    db.flush()
    return PasswordResetOut(temporary_password=temporary)


# ── Home content ─────────────────────────────────────────────


def _home(db: Session) -> HomeContent:
    content = db.get(HomeContent, 1)
    if content is None:
        content = HomeContent(id=1, hero_title="UpiixSol Campus", hero_text="")
        db.add(content)
        db.flush()
    return content


def get_home(db: Session) -> HomeContentOut:
    return HomeContentOut.model_validate(_home(db))


def put_home(db: Session, data: HomeContentIn) -> HomeContentOut:
    content = _home(db)
    content.hero_title = data.hero_title
    content.hero_text = clean_markdown(data.hero_text)
    content.highlighted_academy_ids = data.highlighted_academy_ids
    content.featured_project_ids = data.featured_project_ids
    db.flush()
    return HomeContentOut.model_validate(content)
