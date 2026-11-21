"""Mail campaigns (UPS-075, UPS-089, UPS-106): preview, draft, confirm/resume (sent in the background),
history and delivery detail.

Senders are superadmins and academy_admins (members 403, anonymous 401). The audience scope, the
campaign's sender and the club of the history are checked in the service from DB rows.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.pagination import CursorParam, LimitParam
from app.schemas.common import Page
from app.security import require_role
from app.services import mail_campaigns as service
from app.services import mail_delivery
from app.services.mail_campaigns import CampaignDetail, CampaignIn, CampaignOut, PreviewIn, PreviewOut
from app.services.mail_delivery import DeliveryRow, DeliveryStatus
from app.services.mailer import MailTransport, get_mail_transport

router = APIRouter(prefix="/api/mail", tags=["mail"])
Sender = Annotated[User, Depends(require_role(Role.superadmin, Role.academy_admin))]
Transport = Annotated[MailTransport, Depends(get_mail_transport)]


@router.post("/preview", response_model=PreviewOut)
def preview(data: PreviewIn, user: Sender, db: Session = Depends(get_db)) -> PreviewOut:
    return service.preview(db, user, data)


@router.post("/campaigns", status_code=201, response_model=CampaignOut)
def create_campaign(data: CampaignIn, user: Sender, db: Session = Depends(get_db)) -> CampaignOut:
    return service.create_campaign(db, user, data)


@router.post("/campaigns/{campaign_id}/send", status_code=202, response_model=CampaignOut)
def send_campaign(
    campaign_id: int,
    user: Sender,
    transport: Transport,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> CampaignOut:
    campaign, start = service.confirm(db, user, campaign_id)
    if start:
        tasks.add_task(service.send_pending, campaign.id, transport)
    return service.campaign_out(db, campaign)


@router.post("/campaigns/{campaign_id}/resume", status_code=202, response_model=CampaignOut)
def resume_campaign(
    campaign_id: int,
    user: Sender,
    transport: Transport,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> CampaignOut:
    campaign, start = service.resume(db, user, campaign_id)
    if start:
        tasks.add_task(service.send_pending, campaign.id, transport)
    return service.campaign_out(db, campaign)


@router.get("/campaigns", response_model=Page[CampaignOut])
def list_campaigns(
    user: Sender, cursor: CursorParam = None, limit: LimitParam = 20, db: Session = Depends(get_db)
) -> Page[CampaignOut]:
    return service.list_campaigns(db, user, cursor, limit)


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetail)
def get_campaign(campaign_id: int, user: Sender, db: Session = Depends(get_db)) -> CampaignDetail:
    return service.get_campaign(db, user, campaign_id)


@router.get("/campaigns/{campaign_id}/recipients", response_model=Page[DeliveryRow])
def list_delivery(
    campaign_id: int,
    user: Sender,
    status: DeliveryStatus | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    cursor: CursorParam = None,
    limit: LimitParam = 50,
    db: Session = Depends(get_db),
) -> Page[DeliveryRow]:
    """Who got the email, by status, with the bounce or failure reason (UPS-106); same scope as the detail."""
    return mail_delivery.list_recipients(
        db, user, campaign_id, status=status, q=q, cursor=cursor, limit=limit
    )
