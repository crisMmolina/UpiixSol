"""Blog: public listing/detail of published posts; superadmin CRUD and cover upload."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BlogPost, Role, User
from app.pagination import CursorParam, LimitParam, paginate
from app.schemas.common import Page
from app.schemas.content import BlogPostIn, BlogPostOut
from app.security import optional_user, require_role
from app.services import blog as service
from app.services.gallery import is_superadmin

router = APIRouter(prefix="/api/blog", tags=["blog"])
DbId = Annotated[int, Path(ge=1, le=2**31 - 1)]  # out-of-range ids are a 422, never a DB overflow 500
Superadmin = Annotated[User, Depends(require_role(Role.superadmin))]


@router.get("", response_model=Page[BlogPostOut])
def list_posts(
    drafts: bool = False,
    cursor: CursorParam = None,
    limit: LimitParam = 10,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> Page[BlogPostOut]:
    drafts = drafts and is_superadmin(user)  # only superadmins ever see drafts
    order = [BlogPost.created_at, BlogPost.id] if drafts else [BlogPost.published_at, BlogPost.id]
    page = paginate(db, service.list_stmt(drafts), order, cursor=cursor, limit=limit)
    return Page[BlogPostOut](items=service.outs(db, page.items), next_cursor=page.next_cursor)


@router.get("/{slug}", response_model=BlogPostOut)
def get_post(
    slug: str, user: User | None = Depends(optional_user), db: Session = Depends(get_db)
) -> BlogPostOut:
    return service.get_by_slug(db, slug, user)


@router.post("", response_model=BlogPostOut, status_code=201)
def create_post(data: BlogPostIn, user: Superadmin, db: Session = Depends(get_db)) -> BlogPostOut:
    result = service.save(db, BlogPost(), data, user)
    db.commit()
    return result


@router.put("/{blog_id}", response_model=BlogPostOut)
def update_post(
    blog_id: DbId, data: BlogPostIn, user: Superadmin, db: Session = Depends(get_db)
) -> BlogPostOut:
    result = service.save(db, service.get(db, blog_id), data, user)
    db.commit()
    return result


@router.post("/{blog_id}/cover", response_model=BlogPostOut)
async def upload_cover(
    blog_id: DbId, _user: Superadmin, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> BlogPostOut:
    return await service.replace_cover(db, service.get(db, blog_id), file)


@router.delete("/{blog_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(blog_id: DbId, _user: Superadmin, db: Session = Depends(get_db)) -> Response:
    service.delete(db, service.get(db, blog_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
