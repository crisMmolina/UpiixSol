"""Public `.ics` of an email's event card (UPS-087, spec 004): the per-campaign token is the credential."""

from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import User
from app.models.mail import MailCampaign
from app.services import mail_ics
from app.services.mail_blocks import EventBlock

router = APIRouter(prefix="/api/mail", tags=["mail"])
_TOKEN_MAX = 43


def _event_block(content: Any) -> EventBlock | None:
    for item in content if isinstance(content, list) else []:
        if isinstance(item, dict) and item.get("kind") == "event":
            return EventBlock.model_validate(item)
    return None


@router.get("/ics/{token}.ics", include_in_schema=False)
def campaign_ics(token: str, db: Session = Depends(get_db)) -> Response:
    # Unknown, malformed or event-less: the same bare 404, nothing about other campaigns.
    campaign = None
    if len(token) <= _TOKEN_MAX:
        campaign = db.scalar(select(MailCampaign).where(MailCampaign.ics_token == token))
    block = _event_block(campaign.content) if campaign else None
    sender = db.get(User, campaign.sender_id) if campaign and campaign.sender_id else None
    if campaign is None or block is None or sender is None:
        raise AppError(404)
    try:
        event = mail_ics.resolve_event(db, sender, block)
    except AppError:
        raise AppError(404) from None
    return Response(
        mail_ics.build_ics(event, mail_ics.ics_uid(token)),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="evento.ics"'},
    )
