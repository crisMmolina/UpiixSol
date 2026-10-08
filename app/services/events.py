"""Events and calendar. Global events (academy_id NULL) are superadmin-only; academy events follow the
academy scope (an academy_admin manages only their own academy's events)."""

from datetime import datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Academy, Event, User
from app.pagination import paginate
from app.sanitize import clean_markdown
from app.schemas.common import Page
from app.schemas.content import EventIn, EventOut
from app.security import ensure_academy_scope


def _out(row) -> EventOut:
    return EventOut.model_validate(row)


def events_stmt(
    start: datetime | None, end: datetime | None, academy_id: int | None, include_global: bool
) -> Select:
    stmt = (
        select(Event)
        .outerjoin(Academy, Academy.id == Event.academy_id)
        .where(or_(Event.academy_id.is_(None), Academy.is_active.is_(True)))
    )
    if start is not None:
        stmt = stmt.where(Event.ends_at >= start)
    if end is not None:
        stmt = stmt.where(Event.starts_at < end)
    if academy_id is not None:
        stmt = stmt.where(
            or_(Event.academy_id == academy_id, Event.academy_id.is_(None))
            if include_global
            else Event.academy_id == academy_id
        )
    return stmt


def list_events(db: Session, stmt: Select, cursor: str | None, limit: int) -> Page[EventOut]:
    page = paginate(db, stmt, [Event.starts_at, Event.id], cursor=cursor, limit=limit, descending=False)
    slugs = dict(
        db.execute(
            select(Academy.id, Academy.slug).where(Academy.id.in_({e.academy_id for e in page.items}))
        ).all()
    )
    return Page[EventOut](
        items=[_out(e).model_copy(update={"academy_slug": slugs.get(e.academy_id)}) for e in page.items],
        next_cursor=page.next_cursor,
    )


def academy_by_slug(db: Session, slug: str) -> Academy:
    academy = db.scalar(select(Academy).where(Academy.slug == slug, Academy.is_active.is_(True)))
    if academy is None:
        raise AppError(404, "No encontramos ese club.")
    return academy


def _check_target(db: Session, user: User, academy_id: int | None) -> str | None:
    """Scope for the academy an event belongs to (None = global → superadmin only). Returns its slug."""
    if academy_id is not None and db.get(Academy, academy_id) is None:
        raise AppError(404, "No encontramos ese club.")
    ensure_academy_scope(user, academy_id)
    return db.scalar(select(Academy.slug).where(Academy.id == academy_id)) if academy_id else None


def _apply(event: Event, data: EventIn) -> None:
    event.academy_id = data.academy_id
    event.title = data.title
    event.description = clean_markdown(data.description)
    event.location = data.location
    event.link = data.link
    event.starts_at = data.starts_at
    event.ends_at = data.ends_at


def create_event(db: Session, user: User, data: EventIn) -> EventOut:
    slug = _check_target(db, user, data.academy_id)
    event = Event(created_by_id=user.id)
    _apply(event, data)
    db.add(event)
    db.flush()
    return _out(event).model_copy(update={"academy_slug": slug})


def _get_event(db: Session, event_id: int, user: User) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise AppError(404, "No encontramos ese evento.")
    ensure_academy_scope(user, event.academy_id)  # current owner
    return event


def update_event(db: Session, user: User, event_id: int, data: EventIn) -> EventOut:
    event = _get_event(db, event_id, user)
    slug = _check_target(db, user, data.academy_id)  # and the new owner, if it moves
    _apply(event, data)
    db.flush()
    return _out(event).model_copy(update={"academy_slug": slug})


def delete_event(db: Session, user: User, event_id: int) -> None:
    db.delete(_get_event(db, event_id, user))
    db.flush()
