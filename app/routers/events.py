"""Events and calendar (month view + list, academy filter)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Role, User
from app.pagination import CursorParam, LimitParam
from app.schemas.common import Page, UTCDatetime
from app.schemas.content import EventIn, EventOut
from app.security import current_user, require_role
from app.services import events as service
from app.services import media

router = APIRouter(prefix="/api/events", tags=["events"])
DbId = Annotated[int, Path(ge=1, le=2**31 - 1)]  # out-of-range ids are a 422, never a DB overflow 500
Manager = Annotated[User, Depends(require_role(Role.superadmin, Role.academy_admin))]


@router.get("", response_model=Page[EventOut])
def list_events(
    start: Annotated[UTCDatetime | None, Query(alias="from")] = None,
    end: Annotated[UTCDatetime | None, Query(alias="to")] = None,
    academy: Annotated[str | None, Query(max_length=60)] = None,
    include_global: bool = True,
    cursor: CursorParam = None,
    limit: LimitParam = 50,
    _user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Page[EventOut]:
    if start is not None and end is not None and end < start:
        raise AppError(422, "El rango de fechas es inválido.", code="invalid_range")
    academy_id = service.academy_by_slug(db, academy).id if academy else None
    return service.list_events(db, service.events_stmt(start, end, academy_id, include_global), cursor, limit)


@router.post("", response_model=EventOut, status_code=201)
def create_event(data: EventIn, user: Manager, db: Session = Depends(get_db)) -> EventOut:
    result = service.create_event(db, user, data)
    db.commit()
    return result


@router.patch("/{event_id}", response_model=EventOut)
def update_event(event_id: int, data: EventIn, user: Manager, db: Session = Depends(get_db)) -> EventOut:
    result = service.update_event(db, user, event_id, data)
    db.commit()
    return result


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, user: Manager, db: Session = Depends(get_db)) -> Response:
    cover = service.delete_event(db, user, event_id)
    db.commit()
    media.delete_media(cover)  # only after the commit: a failed delete keeps the photo
    return Response(status_code=204)


@router.post("/{event_id}/cover", response_model=EventOut)
async def upload_cover(
    event_id: DbId, user: Manager, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> EventOut:
    return await service.replace_cover(db, user, event_id, file)


@router.delete("/{event_id}/cover", response_model=EventOut)
def delete_cover(event_id: DbId, user: Manager, db: Session = Depends(get_db)) -> EventOut:
    return service.remove_cover(db, user, event_id)
