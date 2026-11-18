"""Site brand (UPS-041): the campus name, logo, mascot and wordmark colors, in one singleton row.

    get_site(db)                          # public; the built-in defaults when the row is missing
    update_site(db, SiteIn(...))          # superadmin: name and colors
    await upload_image(db, file, "logo")  # superadmin: same media rules as club logos (PNG/JPG/WebP/safe SVG)
    remove_image(db, "mascot")            # no logo → three-color wordmark; no mascot → none shown

Its Pydantic contracts live here (app/schemas has a single owner). Old uploads are removed with
`delete_media` only after the new state is committed; the built-in /brand/… files are never touched.
"""

from typing import Annotated, Literal

from fastapi import Response, UploadFile
from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.errors import AppError
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

# Bidirectional controls (LRM/RLM, embeddings, overrides, isolates) would let a name render reversed or
# reorder the text around it (title, switcher, wordmark).
BIDI_CONTROLS = frozenset("\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
SWAP_ATTEMPTS = 5


def _no_bidi_controls(value: str) -> str:
    if any(char in BIDI_CONTROLS for char in value):
        raise ValueError("El nombre no puede llevar caracteres de control de dirección.")
    return value


SiteName = Annotated[
    str,
    StringConstraints(min_length=2, max_length=40, pattern=r"^[^\x00-\x1f\x7f]+$"),
    AfterValidator(_no_bidi_controls),
]


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


def _stored(db: Session, field: str) -> str | None:
    """The value in the database right now (not the session's copy)."""
    return db.execute(select(getattr(SiteSettings, field)).where(SiteSettings.id == 1)).scalar_one()


def _swap(db: Session, kind: ImageKind, url: str | None) -> str | None:
    """Points `<kind>_url` at `url` and returns the value it replaced.

    Compare-and-swap: the UPDATE only applies while the column still holds the value just read, so two
    simultaneous uploads each get (and later delete) exactly the file they replaced, never orphaning one.
    """
    _row(db)
    field = f"{kind}_url"
    column = getattr(SiteSettings, field)
    for _ in range(SWAP_ATTEMPTS):
        previous = _stored(db, field)
        unchanged = column.is_(None) if previous is None else column == previous
        swapped = db.execute(update(SiteSettings).where(SiteSettings.id == 1, unchanged).values({field: url}))
        if swapped.rowcount == 1:
            return previous
    raise AppError(409, "La marca cambió mientras se guardaba. Intenta de nuevo.", code="conflict")


def _out(db: Session) -> SiteOut:
    return SiteOut.model_validate(db.get(SiteSettings, 1, populate_existing=True))


async def upload_image(
    db: Session,
    file: UploadFile,
    kind: ImageKind,
    *,
    transparent_background: bool = False,
    response: Response | None = None,
) -> SiteOut:
    """Store the new file, swap it in, commit, and only then delete the file it replaced.

    If anything fails the new file is removed and the previous one is kept (no orphans, no data loss).
    """
    stored = await media.store_upload(file, kind, transparent_background=transparent_background)
    url = stored.url
    media.announce_background(response, stored)
    try:
        previous = _swap(db, kind, url)
        db.commit()
    except Exception:
        db.rollback()
        media.delete_media(url)
        raise
    media.delete_media(previous)  # only removes files we stored under /media
    return _out(db)


def remove_image(db: Session, kind: ImageKind) -> SiteOut:
    previous = _swap(db, kind, None)
    db.commit()
    media.delete_media(previous)
    return _out(db)
