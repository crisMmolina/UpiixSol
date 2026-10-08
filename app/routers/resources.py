"""Academy resources: cards filterable by type (members) and admin CRUD (academy scope)."""

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Resource, ResourceType, User
from app.pagination import CursorParam, LimitParam, paginate
from app.schemas.common import Page
from app.schemas.content import ResourceIn, ResourceOut
from app.security import current_user
from app.services import academies, academy_admin
from app.services import resources as service

router = APIRouter(prefix="/api", tags=["resources"])


@router.get("/academies/{slug}/resources", response_model=Page[ResourceOut])
def list_resources(
    slug: str,
    type: ResourceType | None = None,  # noqa: A002 (public query param name)
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Page[ResourceOut]:
    academy = academies.get_academy(db, slug, user)
    return paginate(
        db,
        service.list_stmt(academy, type),
        [Resource.created_at, Resource.id],
        cursor=cursor,
        limit=limit,
        transform=ResourceOut.model_validate,
    )


@router.post("/academies/{academy_id}/resources", response_model=ResourceOut, status_code=201)
async def create_resource(
    academy_id: int,
    type: str = Form(...),  # noqa: A002 (form field name)
    title: str = Form(...),
    description: str = Form(default=""),
    url: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ResourceOut:
    academy = academy_admin.academy_for(db, academy_id, user)  # scope check before reading the upload
    try:
        data = ResourceIn(type=type, title=title, description=description, url=url or None)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    return await service.create(db, academy, data, file)


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(
    resource_id: int,
    data: service.ResourceUpdateIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ResourceOut:
    return service.update(db, service.resource_for(db, resource_id, user), data)


@router.post("/resources/{resource_id}/file", response_model=ResourceOut)
async def upload_resource_file(
    resource_id: int,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ResourceOut:
    resource = service.resource_for(db, resource_id, user)  # scope check before reading the upload
    return await service.replace_file(db, resource, file)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    service.delete(db, service.resource_for(db, resource_id, user))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
