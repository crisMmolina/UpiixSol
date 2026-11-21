"""Mail audience (UPS-074): quota status, audience preview and recipient search for email senders.

Senders are superadmins and academy_admins; members get 403, anonymous callers 401. What an
academy_admin may reach (their club, its enrollees, outside addresses) is checked in the service.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.pagination import CursorParam, LimitParam
from app.schemas.common import Page
from app.security import require_role
from app.services import mail_audience as service
from app.services.mail_audience import (
    Audience,
    AudienceListIn,
    AudienceMember,
    MailStatusOut,
    PreviewOut,
    RecipientOut,
)

router = APIRouter(prefix="/api/mail", tags=["mail"])
Sender = Annotated[User, Depends(require_role(Role.superadmin, Role.academy_admin))]


@router.get("/status", response_model=MailStatusOut)
def get_status(_user: Sender, db: Session = Depends(get_db)) -> MailStatusOut:
    return service.mail_status(db)


@router.post("/audience/preview", response_model=PreviewOut)
def preview_audience(audience: Audience, user: Sender, db: Session = Depends(get_db)) -> PreviewOut:
    return service.preview(db, user, audience)


@router.post("/audience/list", response_model=Page[AudienceMember])
def list_audience(data: AudienceListIn, user: Sender, db: Session = Depends(get_db)) -> Page[AudienceMember]:
    """Who a `mix` (or any) audience reaches, by state, ≤ 50 per page (spec 006)."""
    return service.list_audience(db, user, data)


@router.get("/recipients", response_model=Page[RecipientOut])
def search_recipients(
    user: Sender,
    q: Annotated[str | None, Query(max_length=100)] = None,
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    db: Session = Depends(get_db),
) -> Page[RecipientOut]:
    return service.search_recipients(db, user, q, cursor, limit)
