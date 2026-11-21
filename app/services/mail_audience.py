"""Mail audience (UPS-074, spec 003 §Audiences and permissions): who a campaign reaches, before sending.

    check_scope(db, sender, audience)              # 403 unless the sender may mail that audience
    resolve_audience(db, sender, audience)         # → list[ResolvedRecipient]: one per deliverable address
    preview(db, sender, audience)                  # → PreviewOut: count and what was excluded, from the DB
    list_audience(db, sender, data)                # → Page[AudienceMember]: who it reaches, by state
    search_recipients(db, sender, q, cursor, limit)  # picker: people in scope, with address
    mail_status(db)                                # monthly quota, counted in mail_recipients

The club scope of an academy_admin is always `sender.academy_id` and `enrollments` (DB rows), never the
request body. Every audience drops inactive users, non-deliverable domains (`MAIL_BLOCKED_DOMAINS`) and
suppressed addresses, and counts each normalized address once. Its Pydantic contracts live here.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SerializerFunctionWrapHandler, model_serializer, model_validator
from sqlalchemy import and_, false, func, or_, select, true
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError
from app.models import Enrollment, Role, User
from app.models.common import utcnow
from app.models.mail import MailRecipient, MailSuppression
from app.pagination import decode_cursor, encode_cursor, paginate
from app.schemas.common import InModel, Page
from app.schemas.users import Email
from app.services.mailer import normalize_email

MAX_ENTRIES = 50  # campus users picked one by one; outside addresses have no per-campaign cap (UPS-097)
MAX_SOURCES = 10  # `mix` caps (plan 006 §STRIDE · Tampering)
MAX_MIX_USERS = 1000
MAX_MIX_EXCLUDED = 5000
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
    emails: list[Email] = Field(default_factory=list)  # only the monthly quota limits them (_check_outside)

    @model_validator(mode="after")
    def _size(self) -> "IndividualAudience":
        if not self.user_ids and not self.emails:
            raise ValueError("Elige al menos una persona o un correo.")
        return self


Source = Annotated[AllAudience | AcademyAudience | RoleAudience, Field(discriminator="kind")]


class MixAudience(InModel):
    """Spec 006: sources stay symbolic (re-resolved on the server at send time); the client only sends the
    people it added, the ones it unchecked and the outside addresses."""

    kind: Literal["mix"]
    sources: list[Source] = Field(default_factory=list, max_length=MAX_SOURCES)
    user_ids: list[int] = Field(default_factory=list, max_length=MAX_MIX_USERS)
    exclude_user_ids: list[int] = Field(default_factory=list, max_length=MAX_MIX_EXCLUDED)
    emails: list[Email] = Field(default_factory=list)  # bounded by the monthly quota (_check_outside)

    @model_validator(mode="after")
    def _size(self) -> "MixAudience":
        if not self.sources and not self.user_ids and not self.emails:
            raise ValueError("Agrega al menos una fuente, una persona o un correo.")
        return self


Audience = Annotated[
    AllAudience | AcademyAudience | RoleAudience | IndividualAudience | MixAudience,
    Field(discriminator="kind"),
]


class ExcludedOut(BaseModel):
    inactive: int = 0
    suppressed: int = 0
    blocked_domain: int = 0


class PreviewOut(BaseModel):
    count: int
    # People a source includes that the sender unchecked; `mix` only, so the old kinds answer as before.
    removed: int | None = None
    excluded: ExcludedOut

    @model_serializer(mode="wrap")
    def _drop_unset_removed(self, handler: SerializerFunctionWrapHandler) -> dict:
        data = handler(self)
        if data.get("removed") is None:
            data.pop("removed", None)
        return data


class RecipientOut(BaseModel):
    """A campus user in the picker, always someone the sender may pick (spec 006: with the address)."""

    id: int
    full_name: str
    nickname: str
    avatar_url: str | None = None
    email: str


MemberState = Literal["receives", "removed", "cannot"]
CannotReason = Literal["inactive", "suppressed", "blocked_domain"]


class AudienceListIn(InModel):
    audience: Audience
    q: Annotated[str | None, Field(max_length=100)] = None
    state: MemberState | None = None
    cursor: Annotated[str | None, Field(max_length=500)] = None
    limit: Annotated[int, Field(ge=1, le=50)] = 50


class AudienceMember(BaseModel):
    """One row of the audience list. `origins`: `all`, `academy:<id>`, `role:<role>`, `picked`, `outside`.
    `user_id` is None for a typed outside address; `reason` only when `state` is `cannot`."""

    user_id: int | None
    name: str
    nickname: str | None
    email: str
    avatar_url: str | None
    origins: list[str]
    state: MemberState
    reason: CannotReason | None = None


class MailStatusOut(BaseModel):
    enabled: bool
    monthly_limit: int
    sent_this_period: int
    remaining: int
    period_start: datetime
    period_end: datetime


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
        if wanted <= pickable(db, club, wanted):
            return
    if isinstance(audience, MixAudience):
        # Per source and per id; exclusions are not checked: removing someone is always safe.
        own_club = all(
            isinstance(source, AcademyAudience) and source.academy_id == club for source in audience.sources
        )
        wanted = set(audience.user_ids)
        if own_club and wanted <= pickable(db, club, wanted):
            return
    raise AppError(403)


def _club_members(academy_id: int | None):
    """Who an academy_admin may pick: the club's enrollees and its co-admins (a SQL condition on User)."""
    if academy_id is None:  # `== None` would compile to IS NULL and match every club-less admin
        return false()
    enrolled = select(Enrollment.user_id).where(Enrollment.academy_id == academy_id)
    return or_(User.id.in_(enrolled), and_(User.role == Role.academy_admin, User.academy_id == academy_id))


def pickable(db: Session, academy_id: int, user_ids: set[int]) -> set[int]:
    """Which of `user_ids` are the club's enrollees or co-admins."""
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
    _check_typed(db, audience)
    rows = _resolve(db, audience, blind_typed=sender.role != Role.superadmin)
    excluded = _excluded(rows)
    return PreviewOut(
        count=sum(row.state == "receives" for row in rows),
        removed=sum(row.state == "removed" for row in rows) if isinstance(audience, MixAudience) else None,
        excluded=excluded,
    )


def list_audience(db: Session, sender: User, data: AudienceListIn) -> Page[AudienceMember]:
    """Everyone the audience reaches, from the same resolution as the preview and the send, one row per
    person, ordered by name then address. A non-superadmin only ever gets people they may pick (checked
    again here before serializing) and typed addresses back as typed: never a state that reveals them."""
    check_scope(db, sender, data.audience)
    _check_typed(db, data.audience)
    is_super = sender.role == Role.superadmin
    rows = _resolve(db, data.audience, blind_typed=not is_super)
    if not is_super:
        campus = {row.user_id for row in rows if row.user_id is not None}
        allowed = pickable(db, sender.academy_id, campus) if sender.academy_id is not None else set()
        rows = [row for row in rows if row.user_id is None or row.user_id in allowed]
    if data.state is not None:
        rows = [row for row in rows if row.state == data.state]
    if data.q and data.q.strip():
        needle = data.q.strip().lower()
        rows = [row for row in rows if any(needle in (field or "").lower() for field in row.searchable)]
    rows.sort(key=_sort_key)
    if data.cursor:
        after = tuple(decode_cursor(data.cursor, [User.full_name, User.email]))
        rows = [row for row in rows if _sort_key(row) > after]
    page = rows[: data.limit]
    more = len(rows) > data.limit
    return Page(
        items=[row.member() for row in page],
        next_cursor=encode_cursor(list(_sort_key(page[-1]))) if more else None,
    )


def _check_typed(db: Session, audience: Audience) -> None:
    if isinstance(audience, IndividualAudience | MixAudience):
        _check_outside(db, len({normalize_email(email) for email in audience.emails}))


@dataclass
class _Row:
    """One person or typed address of an audience while it is resolved (never logged: holds addresses)."""

    user_id: int | None
    email: str = field(repr=False)
    name: str = field(repr=False)
    nickname: str | None = field(default=None, repr=False)
    avatar_url: str | None = None
    is_active: bool = True
    typed: bool = False
    origins: list[str] = field(default_factory=list)
    state: MemberState = "receives"
    reason: CannotReason | None = None

    @property
    def searchable(self) -> tuple[str | None, ...]:
        return (self.name, self.nickname, self.email)

    def member(self) -> AudienceMember:
        return AudienceMember(
            user_id=self.user_id,
            name=self.name,
            nickname=self.nickname,
            email=self.email,
            avatar_url=self.avatar_url,
            origins=list(self.origins),
            state=self.state,
            reason=self.reason,
        )


def _sort_key(row: _Row) -> tuple[str, str]:
    return (row.name.lower(), row.email)


def _source_condition(source: AllAudience | AcademyAudience | RoleAudience):
    if isinstance(source, AllAudience):
        return true()
    if isinstance(source, AcademyAudience):
        enrolled = select(Enrollment.user_id).where(Enrollment.academy_id == source.academy_id)
        admins = and_(User.role == Role.academy_admin, User.academy_id == source.academy_id)
        return or_(User.id.in_(enrolled), admins)
    return User.role == source.role


def _origin(source: AllAudience | AcademyAudience | RoleAudience) -> str:
    if isinstance(source, AcademyAudience):
        return f"academy:{source.academy_id}"
    if isinstance(source, RoleAudience):
        return f"role:{source.role.value}"
    return "all"


def _campus(db: Session, audience: Audience) -> list[_Row]:
    """Campus users of the audience, each once (by user id), with every source that brought them in."""
    if isinstance(audience, MixAudience):
        sources, picked = list(audience.sources), audience.user_ids
    elif isinstance(audience, IndividualAudience):
        sources, picked = [], audience.user_ids
    else:
        sources, picked = [audience], []
    columns = (User.id, User.email, User.full_name, User.nickname, User.avatar_url, User.is_active)
    found: dict[int, _Row] = {}

    def add(rows: Iterable, origin: str) -> None:
        for row in rows:
            entry = found.get(row.id)
            if entry is None:
                entry = found[row.id] = _Row(
                    user_id=row.id,
                    email=normalize_email(row.email),
                    name=row.full_name,
                    nickname=row.nickname,
                    avatar_url=row.avatar_url,
                    is_active=row.is_active,
                )
            entry.origins.append(origin)  # origins are distinct per call, and each row comes once per query

    for origin, source in {_origin(source): source for source in sources}.items():  # repeats: one query
        add(db.execute(select(*columns).where(_source_condition(source))), origin)
    for chunk in _chunks(sorted(set(picked))):
        add(db.execute(select(*columns).where(User.id.in_(chunk))), "picked")
    return [found[user_id] for user_id in sorted(found)]


def _resolve(db: Session, audience: Audience, *, blind_typed: bool = False) -> list[_Row]:
    """Every person and typed address of the audience with its state: `receives`, `removed` (a `mix`
    exclusion) or `cannot` (inactive, blocked domain, suppressed; it wins over `removed`, since those rows
    have no checkbox). A typed address equal to a campus user of the audience is that user.

    `blind_typed` (preview and list for a non-superadmin): typed addresses are deduplicated only among
    themselves and not checked against suppressions, so nothing confirms whose address a guess is or that
    it unsubscribed (security review UPS-074). The list that is actually sent always applies both.
    """
    rows = _campus(db, audience)
    by_email = {row.email: row for row in rows}
    emails = audience.emails if isinstance(audience, IndividualAudience | MixAudience) else []
    for email in dict.fromkeys(map(normalize_email, emails)):
        existing = None if blind_typed else by_email.get(email)
        if existing is not None:
            existing.origins.append("outside")  # typed addresses are already deduplicated
            continue
        rows.append(
            _Row(user_id=None, email=email, name=email.partition("@")[0], typed=True, origins=["outside"])
        )
    suppressed = _suppressed(db, {row.email for row in rows if not (blind_typed and row.typed)})
    blocked = get_settings().mail_blocked_domains
    excluded_ids = set(audience.exclude_user_ids) if isinstance(audience, MixAudience) else set()
    for row in rows:
        if not row.is_active:
            row.state, row.reason = "cannot", "inactive"
        elif _is_blocked(row.email, blocked):
            row.state, row.reason = "cannot", "blocked_domain"
        elif row.email in suppressed:
            row.state, row.reason = "cannot", "suppressed"
        elif row.user_id is not None and row.user_id in excluded_ids:
            row.state = "removed"
    return rows


def _excluded(rows: list[_Row]) -> ExcludedOut:
    excluded = ExcludedOut()
    for row in rows:
        if row.reason is not None:
            setattr(excluded, row.reason, getattr(excluded, row.reason) + 1)
    return excluded


def _compute(
    db: Session, audience: Audience, *, blind_typed: bool = False
) -> tuple[list[ResolvedRecipient], ExcludedOut]:
    """Deliverable recipients (campus users first, then typed addresses) and the exclusions."""
    rows = _resolve(db, audience, blind_typed=blind_typed)
    kept = [
        ResolvedRecipient(user_id=row.user_id, email=row.email, name=row.name)
        for row in rows
        if row.state == "receives"
    ]
    return kept, _excluded(rows)


def _check_outside(db: Session, count: int) -> None:
    """Typed addresses have no per-campaign cap: only the month's remaining quota (UPS-097). Previewed here;
    sending re-checks the whole campaign (`mail_campaigns._check_quota`)."""
    remaining = mail_status(db).remaining
    if count > remaining:
        raise AppError(
            422,
            f"Este periodo quedan {remaining} envíos y escribiste {count} correos de fuera; "
            "quita algunos o espera a que se renueve la cuota.",
            code="quota_exceeded",
            details={"remaining": remaining},
        )


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

    Every sender sees (and searches by) the address of the people they may pick (spec 006, victor
    2026-11-20); people outside the scope are filtered out in SQL, before anything is serialized.
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
        fields = [User.full_name, User.nickname, User.email]
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
            email=user.email,
        ),
    )


def billing_period(now: datetime, start_day: int) -> tuple[datetime, datetime]:
    """Mailgun billing period (UTC) containing `now`: [start, end), starting on `start_day` (1–28)."""
    year, month = (now.year, now.month) if now.day >= start_day else _shift_month(now.year, now.month, -1)
    end_year, end_month = _shift_month(year, month, 1)
    return (
        datetime(year, month, start_day, tzinfo=UTC),
        datetime(end_year, end_month, start_day, tzinfo=UTC),
    )


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def mail_status(db: Session) -> MailStatusOut:
    """Quota used in the current Mailgun billing period (UTC): DB count of recipients that left `pending`."""
    settings = get_settings()
    period_start, period_end = billing_period(utcnow(), settings.mail_period_start_day)
    sent = db.scalar(
        select(func.count())
        .select_from(MailRecipient)
        .where(MailRecipient.status != "pending", MailRecipient.updated_at >= period_start)
    )
    return MailStatusOut(
        enabled=settings.mail_enabled,
        monthly_limit=settings.mail_monthly_limit,
        sent_this_period=sent,
        remaining=max(0, settings.mail_monthly_limit - sent),
        period_start=period_start,
        period_end=period_end,
    )
