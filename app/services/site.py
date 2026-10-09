"""Site brand (UPS-041): the campus name, logo, mascot and wordmark colors, in one singleton row.

    get_site(db)                          # public; the built-in defaults when the row is missing
    update_site(db, SiteIn(...))          # superadmin: name and colors
    await upload_image(db, file, "logo")  # superadmin: same media rules as club logos (PNG/JPG/WebP/safe SVG)
    remove_image(db, "mascot")            # no logo → three-color wordmark; no mascot → none shown

Its Pydantic contracts live here (app/schemas has a single owner). Old uploads are removed with
`delete_media` only after the new state is committed; the built-in /brand/… files are never touched.
"""

from typing import Annotated, Literal

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy.orm import Session

from app.models import SiteSettings
from app.schemas.common import HexColor, InModel
from app.services import media

ImageKind = Literal["logo", "mascot"]

# Same values as migration 0006 and web/src/lib/brand.tsx (the brand the web shipped with).
DEFAULTS: dict[str, str | None] = {
    "name": "UpiixSol",
    "logo_url": "/brand/upiixsol/wordmark.png",
    "mascot_url": "/brand/upiixsol/mascot.png",
    "color_primary": "#00BF63",
    "color_secondary": "#04944F",
    "color_accent": "#F28034",
}

SiteName = Annotated[str, StringConstraints(min_length=2, max_length=40, pattern=r"^[^\x00-\x1f\x7f]+$")]


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    logo_url: str | None
    mascot_url: str | None
    color_primary: str
    color_secondary: str
    color_accent: str


class SiteIn(InModel):
    name: SiteName
    color_primary: HexColor
    color_secondary: HexColor
    color_accent: HexColor


def get_site(db: Session) -> SiteOut:
    row = db.get(SiteSettings, 1)
    return SiteOut.model_validate(row) if row else SiteOut.model_validate(DEFAULTS)


def _row(db: Session) -> SiteSettings:
    row = db.get(SiteSettings, 1)
    if row is None:
        row = SiteSettings(id=1, **DEFAULTS)
        db.add(row)
        db.flush()
    return row


def update_site(db: Session, data: SiteIn) -> SiteOut:
    row = _row(db)
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    db.flush()
    return SiteOut.model_validate(row)


async def upload_image(db: Session, file: UploadFile, kind: ImageKind) -> SiteOut:
    """Store the new file, commit, and only then delete the previous upload.

    If the commit fails the new file is removed and the previous one is kept (no orphans, no data loss).
    """
    url = await media.save_upload(file, kind)
    field = f"{kind}_url"
    try:
        row = _row(db)
        previous = getattr(row, field)
        setattr(row, field, url)
        db.commit()
    except Exception:
        db.rollback()
        media.delete_media(url)
        raise
    media.delete_media(previous)  # only removes files we stored under /media
    return SiteOut.model_validate(row)


def remove_image(db: Session, kind: ImageKind) -> SiteOut:
    row = _row(db)
    field = f"{kind}_url"
    previous = getattr(row, field)
    setattr(row, field, None)
    db.commit()
    media.delete_media(previous)
    return SiteOut.model_validate(row)
