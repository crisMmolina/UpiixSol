"""Academy resources (IDEA §9 Recursos): cards filterable by type + admin CRUD.

Members see the resources of any active academy; writes resolve the academy from the database
(the academy row for create, the resource row otherwise) and call ensure_academy_scope.
A resource always keeps an `http(s)` url or an uploaded file (DB check `url_or_file`).
"""

from fastapi import UploadFile
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Academy, Resource, ResourceType, User
from app.sanitize import clean_markdown
from app.schemas.common import HttpUrl, InModel, MarkdownText, Title
from app.schemas.content import ResourceIn, ResourceOut
from app.security import ensure_academy_scope
from app.services import media


class ResourceUpdateIn(InModel):
    """Partial update. Sending `"url": null` removes the link (only if a file remains)."""

    type: ResourceType | None = None
    title: Title | None = None
    description: MarkdownText | None = None
    url: HttpUrl | None = None


def _url_or_file_required() -> AppError:
    return AppError(422, "Agrega un link http(s) o sube un archivo.", code="url_or_file_required")


def list_stmt(academy: Academy, type_: ResourceType | None) -> Select:
    stmt = select(Resource).where(Resource.academy_id == academy.id)
    if type_ is not None:
        stmt = stmt.where(Resource.type == type_)
    return stmt


def resource_for(db: Session, resource_id: int, user: User) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise AppError(404, "No encontramos ese recurso.")
    ensure_academy_scope(user, resource.academy_id)
    return resource


async def _commit_with_file(db: Session, resource: Resource, file: UploadFile) -> str | None:
    """Store the upload, commit, and only then return the previous file for deletion.

    If the commit fails, the new file is removed and the previous one is kept (no orphans, no data loss).
    """
    url = await media.save_upload(file, "resource")
    previous = resource.file_url
    try:
        resource.file_url = url
        db.add(resource)
        db.commit()
    except Exception:
        db.rollback()
        media.delete_media(url)
        raise
    return previous


async def create(db: Session, academy: Academy, data: ResourceIn, file: UploadFile | None) -> ResourceOut:
    if data.url is None and file is None:
        raise _url_or_file_required()
    resource = Resource(
        academy_id=academy.id,
        type=data.type,
        title=data.title,
        description=clean_markdown(data.description),
        url=data.url,
    )
    if file is None:
        db.add(resource)
        db.commit()
    else:
        await _commit_with_file(db, resource, file)
    return ResourceOut.model_validate(resource)


def update(db: Session, resource: Resource, data: ResourceUpdateIn) -> ResourceOut:
    changes = data.model_dump(exclude_unset=True)
    if "url" in changes and changes["url"] is None and resource.file_url is None:
        raise _url_or_file_required()
    for field in ("type", "title"):
        if changes.get(field) is not None:
            setattr(resource, field, changes[field])
    if changes.get("description") is not None:
        resource.description = clean_markdown(changes["description"])
    if "url" in changes:
        resource.url = changes["url"]
    db.commit()
    return ResourceOut.model_validate(resource)


async def replace_file(db: Session, resource: Resource, file: UploadFile) -> ResourceOut:
    previous = await _commit_with_file(db, resource, file)
    media.delete_media(previous)
    return ResourceOut.model_validate(resource)


def delete(db: Session, resource: Resource) -> None:
    file_url = resource.file_url
    db.delete(resource)
    db.commit()
    media.delete_media(file_url)
