"""Mail composer defaults (UPS-091): the Reply-To the composer prefills, from MAIL_REPLY_TO."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings
from app.models import Role, User
from app.security import require_role

router = APIRouter(prefix="/api/mail", tags=["mail"])


class ReplyToOut(BaseModel):
    reply_to: str | None


@router.get("/reply-to", response_model=ReplyToOut)
def default_reply_to(_user: User = Depends(require_role(Role.superadmin, Role.academy_admin))) -> ReplyToOut:
    return ReplyToOut(reply_to=get_settings().mail_reply_to.strip() or None)
