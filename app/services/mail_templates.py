"""Mail templates (UPS-101, spec 005 §Templates): list, save, rename and delete, scoped from the DB user.

A superadmin saves UpiixSol templates (`site`) and manages every template; an academy_admin saves and
manages only their own club's (`academy`, club from `users.academy_id`, never the body). Built-ins live
in code (`builtin:<slug>`) and are read-only. A template stores subject, preheader and blocks only:
never the audience, the sender or the Reply-To.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import MailTemplate, Role, User
from app.schemas.common import InModel
from app.services.mail_blocks import Blocks
from app.services.mail_campaigns import one_line
from app.services.mail_templates_builtin import BUILTIN_TEMPLATES, builtin_by_id

DUPLICATE = "Ya existe una plantilla con ese nombre."
READ_ONLY = "Las plantillas incluidas no se pueden cambiar."

Name = Annotated[str, Field(min_length=1, max_length=60)]
Description = Annotated[str | None, Field(max_length=140)]


class TemplateIn(InModel):
    name: Name
    description: Description = None
    subject: Annotated[str, Field(min_length=1, max_length=150)]
    preheader: Annotated[str | None, Field(min_length=1, max_length=140)] = None
    blocks: Blocks

    @field_validator("name", "description", "subject", "preheader")
    @classmethod
    def _one_line(cls, value: str | None) -> str | None:
        return None if value is None else one_line(value)


class TemplateRename(InModel):
    name: Name
    description: Description = None

    @field_validator("name", "description")
    @classmethod
    def _one_line(cls, value: str | None) -> str | None:
        return None if value is None else one_line(value)


class TemplateOut(BaseModel):
    id: str | int
    kind: Literal["builtin", "saved"]
    scope: Literal["site", "academy"]
    name: str
    description: str | None
    subject: str
    preheader: str | None
    blocks: list[dict[str, Any]]


def _out(row: MailTemplate) -> TemplateOut:
    return TemplateOut(
        id=row.id,
        kind="saved",
        scope=row.scope,  # type: ignore[arg-type]
        name=row.name,
        description=row.description,
        subject=row.subject,
        preheader=row.preheader,
        blocks=row.content,
    )


def _scope(user: User) -> tuple[str, int | None]:
    """Where this user's templates go: UpiixSol for a superadmin, own club (from the DB row) otherwise."""
    if user.role == Role.superadmin:
        return "site", None
    if user.academy_id is None:
        raise AppError(403)
    return "academy", user.academy_id


def list_templates(db: Session, user: User) -> list[TemplateOut]:
    """Built-ins, then UpiixSol templates, then club templates (all for a superadmin, own club otherwise)."""
    query = select(MailTemplate)
    if user.role != Role.superadmin:
        _, club = _scope(user)
        query = query.where((MailTemplate.scope == "site") | (MailTemplate.academy_id == club))
    rows = db.scalars(
        query.order_by(
            MailTemplate.scope.desc(),  # "site" before "academy"
            MailTemplate.academy_id,
            func.lower(MailTemplate.name),
            MailTemplate.id,
        )
    ).all()
    builtins = [
        TemplateOut(
            id=t.id,
            kind="builtin",
            scope="site",
            name=t.name,
            description=t.description,
            subject=t.subject,
            preheader=t.preheader,
            blocks=t.blocks,
        )
        for t in BUILTIN_TEMPLATES
    ]
    return builtins + [_out(row) for row in rows]


def _check_unique(db: Session, scope: str, club: int | None, name: str, exclude: int | None = None) -> None:
    query = select(MailTemplate.id).where(
        MailTemplate.scope == scope,
        func.coalesce(MailTemplate.academy_id, 0) == (club or 0),
        func.lower(MailTemplate.name) == name.lower(),
    )
    if exclude is not None:
        query = query.where(MailTemplate.id != exclude)
    if db.scalar(query.limit(1)) is not None:
        raise AppError(409, DUPLICATE)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:  # a concurrent save with the same name
        db.rollback()
        raise AppError(409, DUPLICATE) from exc


def save_template(db: Session, user: User, data: TemplateIn) -> TemplateOut:
    scope, club = _scope(user)
    _check_unique(db, scope, club, data.name)
    row = MailTemplate(
        scope=scope,
        academy_id=club,
        name=data.name,
        description=data.description,
        subject=data.subject,
        preheader=data.preheader,
        content=[block.model_dump(mode="json") for block in data.blocks.root],
        created_by=user.id,
    )
    db.add(row)
    _commit(db)
    return _out(row)


def _load(db: Session, user: User, template_id: str) -> MailTemplate:
    """A saved template the user may change: 405 for a built-in, 404 if missing, 403 outside their scope."""
    if builtin_by_id(template_id) is not None:
        raise AppError(405, READ_ONLY)
    row = (
        db.get(MailTemplate, int(template_id)) if template_id.isascii() and template_id.isdecimal() else None
    )
    if row is None:
        raise AppError(404)
    if user.role != Role.superadmin and (row.scope != "academy" or row.academy_id != _scope(user)[1]):
        raise AppError(403)
    return row


def rename_template(db: Session, user: User, template_id: str, data: TemplateRename) -> TemplateOut:
    row = _load(db, user, template_id)
    _check_unique(db, row.scope, row.academy_id, data.name, exclude=row.id)
    row.name = data.name
    if "description" in data.model_fields_set:
        row.description = data.description
    _commit(db)
    return _out(row)


def delete_template(db: Session, user: User, template_id: str) -> None:
    row = _load(db, user, template_id)
    db.delete(row)
    db.commit()
