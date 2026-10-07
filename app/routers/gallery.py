"""Project gallery: public listing/detail of published projects; superadmin CRUD and cover upload."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project, Role, User
from app.pagination import CursorParam, LimitParam, paginate
from app.schemas.common import Page
from app.schemas.content import ProjectIn, ProjectOut
from app.security import optional_user, require_role
from app.services import gallery as service

router = APIRouter(prefix="/api/projects", tags=["gallery"])
Superadmin = Annotated[User, Depends(require_role(Role.superadmin))]


@router.get("", response_model=Page[ProjectOut])
def list_projects(
    tag: Annotated[str | None, Query(max_length=40)] = None,
    drafts: bool = False,
    cursor: CursorParam = None,
    limit: LimitParam = 12,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> Page[ProjectOut]:
    drafts = drafts and service.is_superadmin(user)  # only superadmins ever see drafts
    order = [Project.created_at, Project.id] if drafts else [Project.published_at, Project.id]
    return paginate(
        db,
        service.list_stmt(tag, drafts),
        order,
        cursor=cursor,
        limit=limit,
        transform=ProjectOut.model_validate,
    )


@router.get("/{slug}", response_model=ProjectOut)
def get_project(
    slug: str, user: User | None = Depends(optional_user), db: Session = Depends(get_db)
) -> ProjectOut:
    return service.get_by_slug(db, slug, user)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectIn, _user: Superadmin, db: Session = Depends(get_db)) -> ProjectOut:
    result = service.save(db, Project(), data)
    db.commit()
    return result


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, data: ProjectIn, _user: Superadmin, db: Session = Depends(get_db)
) -> ProjectOut:
    result = service.save(db, service.get(db, project_id), data)
    db.commit()
    return result


@router.post("/{project_id}/cover", response_model=ProjectOut)
async def upload_cover(
    project_id: int, _user: Superadmin, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> ProjectOut:
    return await service.replace_cover(db, service.get(db, project_id), file)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, _user: Superadmin, db: Session = Depends(get_db)) -> Response:
    service.delete(db, service.get(db, project_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
