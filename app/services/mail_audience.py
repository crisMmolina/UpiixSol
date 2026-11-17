"""Mail audience (UPS-074, spec 003 §Audiences and permissions): who a campaign reaches, before sending.

    check_scope(db, sender, audience)              # 403 unless the sender may mail that audience
    resolve_audience(db, sender, audience)         # → list[ResolvedRecipient]: one per deliverable address
    preview(db, sender, audience)                  # → PreviewOut: count and what was excluded, from the DB
    search_recipients(db, sender, q, cursor, limit)  # picker for `individual`; email only for superadmins
    mail_status(db)                                # daily quota, counted in mail_recipients

The club scope of an academy_admin is always `sender.academy_id` and `enrollments` (DB rows), never the
request body. Every audience drops inactive users, non-deliverable domains (`MAIL_BLOCKED_DOMAINS`) and
suppressed addresses, and counts each normalized address once. Its Pydantic contracts live here.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from sqlalchemy import Select, and_, false, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError
from app.models import Enrollment, Role, User
from app.models.common import utcnow
from app.models.mail import MailRecipient, MailSuppression
from app.pagination import paginate
from app.schemas.common import InModel, Page
from app.schemas.users import Email
from app.services.mailer import normalize_email

MAX_ENTRIES = 50
MAX_OUTSIDE = 20
_IN_CHUNK = 900  # keeps every IN (...) under SQLite's bound-parameter limit


# ── Contracts ───────────────────────────────────────────────


class AllAudience(InModel):
    kind: Literal["all"]


class AcademyAudience(InModel):
    kind: Literal["academy"]
    academy_id: int


class RoleAudience(InModel):
    kind: Literal["role"]
    role: Role


class IndividualAudience(InModel):
    kind: Literal["individual"]
    user_ids: list[int] = Field(default_factory=list, max_length=MAX_ENTRIES)
    emails: list[Email] = Field(default_factory=list, max_length=MAX_OUTSIDE)

    @model_validator(mode="after")
    def _size(self) -> "IndividualAudience":
        total = len(self.user_ids) + len(self.emails)
        if total == 0:
            raise ValueError("Elige al menos una persona o un correo.")
        if total > MAX_ENTRIES:
            raise ValueError(f"Como máximo {MAX_ENTRIES} destinatarios en total.")
        return self


Audience = Annotated[
    AllAudience | AcademyAudience | RoleAudience | IndividualAudience, Field(discriminator="kind")
]


class ExcludedOut(BaseModel):
    inactive: int = 0
    suppressed: int = 0
    blocked_domain: int = 0


class PreviewOut(BaseModel):
    count: int
    excluded: ExcludedOut


class RecipientOut(BaseModel):
    """A campus user in the picker. `email` is filled (and serialized) only for superadmins."""

    id: int
    full_name: str
    nickname: str
    avatar_url: str | None = None
    email: str | None = None

    @model_serializer(mode="wrap")
    def _drop_hidden_email(self, handler: SerializerFunctionWrapHandler, _info: SerializationInfo) -> dict:
        data = handler(self)
        if data.get("email") is None:
            data.pop("email", None)
        return data


class MailStatusOut(BaseModel):
    enabled: bool
    daily_limit: int
    sent_today: int
    remaining: int


@dataclass(frozen=True)
class ResolvedRecipient:
    """One deliverable address of an audience; `user_id` is None for an outside address."""

    user_id: int | None
    email: str = field(repr=False)  # repr=False: a stray "%r" in a log must not leak the address
    name: str = field(repr=False)


# ── Scope ───────────────────────────────────────────────────


def check_scope(db: Session, sender: User, audience: Audience) -> None:
    """Superadmin: any audience. academy_admin: their club, or its enrollees and co-admins plus outside
    addresses (co-admins: human decision, victor 2026-11-17)."""
    if sender.role == Role.superadmin:
        return
    club = sender.academy_id if sender.role == Role.academy_admin else None
    if club is None:
        raise AppError(403)
    if isinstance(audience, AcademyAudience) and audience.academy_id == club:
        return
    if isinstance(audience, IndividualAudience):
        wanted = set(audience.user_ids)
        if wanted <= _pickable(db, club, wanted):
            return
    raise AppError(403)


def _club_members(academy_id: int | None):
    """Who an academy_admin may pick: the club's enrollees and its co-admins (a SQL condition on User)."""
    if academy_id is None:  # `== None` would compile to IS NULL and match every club-less admin
        return false()
    enrolled = select(Enrollment.user_id).where(Enrollment.academy_id == academy_id)
    return or_(User.id.in_(enrolled), and_(User.role == Role.academy_admin, User.academy_id == academy_id))


def _pickable(db: Session, academy_id: int, user_ids: set[int]) -> set[int]:
    found: set[int] = set()
    for chunk in _chunks(sorted(user_ids)):
        found.update(db.scalars(select(User.id).where(User.id.in_(chunk), _club_members(academy_id))))
    return found


# ── Audience ────────────────────────────────────────────────


def resolve_audience(db: Session, sender: User, audience: Audience) -> list[ResolvedRecipient]:
    check_scope(db, sender, audience)
    return _compute(db, audience)[0]


def preview(db: Session, sender: User, audience: Audience) -> PreviewOut:
    check_scope(db, sender, audience)
    recipients, excluded = _compute(db, audience, blind_typed=sender.role != Role.superadmin)
    return PreviewOut(count=len(recipients), excluded=excluded)


def _users_stmt(audience: Audience) -> Select | None:
    stmt = select(User.id, User.email, User.full_name, User.is_active).order_by(User.id)
    if isinstance(audience, AllAudience):
        return stmt
    if isinstance(audience, AcademyAudience):
        enrolled = select(Enrollment.user_id).where(Enrollment.academy_id == audience.academy_id)
        admins = and_(User.role == Role.academy_admin, User.academy_id == audience.academy_id)
        return stmt.where(or_(User.id.in_(enrolled), admins))
    if isinstance(audience, RoleAudience):
        return stmt.where(User.role == audience.role)
    return stmt.where(User.id.in_(audience.user_ids)) if audience.user_ids else None


def _compute(
    db: Session, audience: Audience, *, blind_typed: bool = False
) -> tuple[list[ResolvedRecipient], ExcludedOut]:
    """Deliverable recipients and the exclusions. Campus users come first, so a typed address that is also
    one of them is sent once, as that user; typed addresses are never looked up among other users.

    `blind_typed` (preview for a non-superadmin): typed addresses are deduplicated only among themselves
    and not checked against suppressions, so the count never confirms whose address a guess is or that it
    unsubscribed (security review UPS-074). The list that is actually sent always applies both.
    """
    stmt = _users_stmt(audience)
    # (user_id, email, name, is_active, typed)
    candidates: list[tuple[int | None, str, str, bool, bool]] = [
        (row.id, normalize_email(row.email), row.full_name, row.is_active, False)
        for row in (db.execute(stmt) if stmt is not None else ())
    ]
    if isinstance(audience, IndividualAudience):
        candidates += [
            (None, email, email.partition("@")[0], True, True)
            for email in map(normalize_email, audience.emails)
        ]
    suppressed = _suppressed(
        db, {email for _, email, _, _, typed in candidates if not (blind_typed and typed)}
    )
    blocked = get_settings().mail_blocked_domains
    excluded = ExcludedOut()
    seen: set[tuple[str, bool]] = set()
    kept: list[ResolvedRecipient] = []
    for user_id, email, name, is_active, typed in candidates:
        key = (email, typed and blind_typed)
        if key in seen:
            continue
        seen.add(key)
        if not is_active:
            excluded.inactive += 1
        elif _is_blocked(email, blocked):
            excluded.blocked_domain += 1
        elif email in suppressed:
            excluded.suppressed += 1
        else:
            kept.append(ResolvedRecipient(user_id=user_id, email=email, name=name))
    return kept, excluded


def _suppressed(db: Session, emails: set[str]) -> set[str]:
    found: set[str] = set()
    for chunk in _chunks(sorted(emails)):
        found.update(db.scalars(select(MailSuppression.email).where(MailSuppression.email.in_(chunk))))
    return found


def _is_blocked(email: str, domains: Iterable[str]) -> bool:
    domain = email.rpartition("@")[2]
    return any(domain == blocked or domain.endswith(f".{blocked}") for blocked in domains)


def _chunks[T](items: list[T]) -> Iterable[list[T]]:
    for start in range(0, len(items), _IN_CHUNK):
        yield items[start : start + _IN_CHUNK]


# ── Recipient search and status ─────────────────────────────


def search_recipients(
    db: Session, sender: User, q: str | None, cursor: str | None, limit: int
) -> Page[RecipientOut]:
    """Active users the sender may pick: everyone for a superadmin, the club's enrollees
    and co-admins otherwise.

    Only a superadmin's search matches (and returns) addresses; the others match name and nickname, so
    the search cannot be used to find out whether an address belongs to someone.
    """
    is_super = sender.role == Role.superadmin
    # The sender is left out: mailing yourself is the test send (POST /api/mail/test), not a recipient.
    stmt = select(User).where(User.is_active.is_(True), User.id != sender.id)
    if not is_super:
        stmt = stmt.where(_club_members(sender.academy_id))
    if q and q.strip():
        # LIKE wildcards in the search are literal characters (as app/services/admin.py does).
        escaped = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        needle = f"%{escaped}%"
        fields = [User.full_name, User.nickname] + ([User.email] if is_super else [])
        stmt = stmt.where(or_(*(column.ilike(needle, escape="\\") for column in fields)))
    return paginate(
        db,
        stmt,
        [User.full_name, User.id],
        cursor=cursor,
        limit=limit,
        descending=False,
        transform=lambda user: RecipientOut(
            id=user.id,
            full_name=user.full_name,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            email=user.email if is_super else None,
        ),
    )


def mail_status(db: Session) -> MailStatusOut:
    """Quota used today (UTC) = recipients that left `pending` today: a DB count, never an estimate."""
    settings = get_settings()
    midnight = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = db.scalar(
        select(func.count())
        .select_from(MailRecipient)
        .where(MailRecipient.status != "pending", MailRecipient.updated_at >= midnight)
    )
    return MailStatusOut(
        enabled=settings.mail_enabled,
        daily_limit=settings.mail_daily_limit,
        sent_today=sent_today,
        remaining=max(0, settings.mail_daily_limit - sent_today),
    )
