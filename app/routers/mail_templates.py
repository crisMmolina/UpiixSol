"""Mail templates (UPS-101, spec 005): built-ins + UpiixSol + own club; save, rename and delete in scope.

Senders are superadmins and academy_admins (members 403, anonymous 401). The template id is a string so
a built-in id (`builtin:<slug>`) reaches the service and gets its 405 instead of a validation error.
The list is a plain array (plan §Contracts): built-ins plus a handful of saved templates per scope.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import require_role
from app.services import mail_templates as service
from app.services.mail_templates import TemplateIn, TemplateOut, TemplateRename

router = APIRouter(prefix="/api/mail/templates", tags=["mail"])
Sender = Annotated[User, Depends(require_role(Role.superadmin, Role.academy_admin))]


@router.get("", response_model=list[TemplateOut])
def list_templates(user: Sender, db: Session = Depends(get_db)) -> list[TemplateOut]:
    return service.list_templates(db, user)


@router.post("", status_code=201, response_model=TemplateOut)
def save_template(data: TemplateIn, user: Sender, db: Session = Depends(get_db)) -> TemplateOut:
    return service.save_template(db, user, data)


@router.patch("/{template_id}", response_model=TemplateOut)
def rename_template(
    template_id: str, data: TemplateRename, user: Sender, db: Session = Depends(get_db)
) -> TemplateOut:
    return service.rename_template(db, user, template_id, data)


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: str, user: Sender, db: Session = Depends(get_db)) -> Response:
    service.delete_template(db, user, template_id)
    return Response(status_code=204)
