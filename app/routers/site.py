"""Site brand (UPS-041): public read for every page (login included), superadmin-only writes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import require_role
from app.services import site as service
from app.services.site import SiteIn, SiteOut

router = APIRouter(prefix="/api", tags=["site"])
Superadmin = Annotated[User, Depends(require_role(Role.superadmin))]

# Short, so a change reaches everyone within a minute; the editor's own browser re-fetches with
# `cache: "reload"` right after saving.
PUBLIC_CACHE = "public, max-age=60"


@router.get("/site", response_model=SiteOut)
def get_site(response: Response, db: Session = Depends(get_db)) -> SiteOut:
    response.headers["Cache-Control"] = PUBLIC_CACHE
    return service.get_site(db)


@router.put("/admin/site", response_model=SiteOut)
def put_site(data: SiteIn, _user: Superadmin, db: Session = Depends(get_db)) -> SiteOut:
    result = service.update_site(db, data)
    db.commit()
    return result


@router.post("/admin/site/logo", response_model=SiteOut)
async def upload_logo(
    _user: Superadmin,
    response: Response,
    file: UploadFile = File(...),
    transparent_background: bool = Form(False),
    db: Session = Depends(get_db),
) -> SiteOut:
    return await service.upload_image(  # commits itself (file cleanup on failure)
        db, file, "logo", transparent_background=transparent_background, response=response
    )


@router.post("/admin/site/mascot", response_model=SiteOut)
async def upload_mascot(
    _user: Superadmin,
    response: Response,
    file: UploadFile = File(...),
    transparent_background: bool = Form(False),
    db: Session = Depends(get_db),
) -> SiteOut:
    return await service.upload_image(
        db, file, "mascot", transparent_background=transparent_background, response=response
    )


@router.delete("/admin/site/logo", response_model=SiteOut)
def delete_logo(_user: Superadmin, db: Session = Depends(get_db)) -> SiteOut:
    return service.remove_image(db, "logo")


@router.delete("/admin/site/mascot", response_model=SiteOut)
def delete_mascot(_user: Superadmin, db: Session = Depends(get_db)) -> SiteOut:
    return service.remove_image(db, "mascot")
