"""Image uploads: real-type check, size limits, resize + re-encode (strips EXIF), random names.

    url = await save_upload(file, "post")   # → "/media/post/<uuid>.webp"

Raster images are re-encoded to WebP. SVG is only accepted for logos/mascots and must pass an
element/attribute allowlist (parsed as XML); `/media` is also served with a `sandbox` CSP (app/main.py).

Storage (UPS-030): files go to MEDIA_DIR, or to the `media_objects` table with MEDIA_STORAGE=database on
hosts whose disk is wiped on every restart (Render free). The URL is the same either way.
"""

import io
import logging
import re
import uuid
import xml.etree.ElementTree as ET  # noqa: S405 (DTDs/entities are rejected before parsing)
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.errors import AppError
from app.models import MediaObject

log = logging.getLogger(__name__)
Kind = Literal["logo", "mascot", "avatar", "post", "cover", "resource"]
MB = 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard


@dataclass(frozen=True)
class Rule:
    max_bytes: int
    max_side: int
    allow_svg: bool = False


RULES: dict[str, Rule] = {
    "logo": Rule(2 * MB, 1024, allow_svg=True),
    "mascot": Rule(2 * MB, 1024, allow_svg=True),
    "avatar": Rule(2 * MB, 256),
    "post": Rule(5 * MB, 1600),
    "cover": Rule(5 * MB, 1600),
    "resource": Rule(5 * MB, 1600),
}
RASTER_FORMATS = {"PNG", "JPEG", "WEBP"}
CONTENT_TYPES = {"webp": "image/webp", "svg": "image/svg+xml"}
MEDIA_KEY = re.compile(r"[a-z]+/[0-9a-f]{32}\.(?:webp|svg)")  # what _store writes: <kind>/<uuid>.<ext>
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
SVG_ELEMENTS = {
    "svg",
    "g",
    "path",
    "circle",
    "ellipse",
    "rect",
    "line",
    "polyline",
    "polygon",
    "defs",
    "title",
    "desc",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
    "mask",
    "use",
    "symbol",
}
SVG_ATTRIBUTES = {
    "id",
    "class",
    "d",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "width",
    "height",
    "viewBox",
    "points",
    "fill",
    "fill-opacity",
    "fill-rule",
    "clip-rule",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-opacity",
    "stroke-dasharray",
    "opacity",
    "transform",
    "offset",
    "stop-color",
    "stop-opacity",
    "gradientUnits",
    "gradientTransform",
    "clip-path",
    "mask",
    "preserveAspectRatio",
    "version",
    "href",
    "role",
    "aria-label",
    "aria-hidden",
    "focusable",
}
_LOCAL_REF = re.compile(r"^#[A-Za-z][\w.-]*$")
_URL_FUNC = re.compile(r"url\(\s*(?!#)", re.IGNORECASE)


def _too_large(rule: Rule) -> AppError:
    return AppError(413, f"La imagen supera {rule.max_bytes // MB} MB.")


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    media_storage: Literal["disk", "database"] = "disk"


@lru_cache
def media_storage() -> str:
    return StorageSettings().media_storage


def _store(data: bytes, kind: str, extension: str) -> str:
    name = f"{uuid.uuid4().hex}.{extension}"
    if media_storage() == "database":
        # Its own short transaction, like the file write: the bytes exist before any row points to them.
        with SessionLocal() as db:
            db.add(MediaObject(key=f"{kind}/{name}", content_type=CONTENT_TYPES[extension], data=data))
            db.commit()
    else:
        folder = Path(get_settings().media_dir) / kind
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
    return f"/media/{kind}/{name}"


def load_media(db: Session, key: str) -> MediaObject | None:
    """A stored upload (MEDIA_STORAGE=database); None for unknown or malformed keys."""
    return db.get(MediaObject, key) if MEDIA_KEY.fullmatch(key) else None


def _looks_like_svg(data: bytes) -> bool:
    head = data[:512].lstrip().lower()
    return head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2048].lower())


def _split(name: str) -> tuple[str | None, str]:
    if name.startswith("{"):
        namespace, local = name[1:].split("}", 1)
        return namespace, local
    return None, name


def _svg_is_safe(data: bytes) -> bool:
    """Allowlist: SVG-namespace shapes only, no scripts/styles/events, references only to local ids."""
    if re.search(rb"<!(DOCTYPE|ENTITY)", data, re.IGNORECASE):
        return False
    try:
        root = ET.fromstring(data)  # noqa: S314 (no DTD → no entity expansion)
    except ET.ParseError:
        return False
    for element in root.iter():
        namespace, tag = _split(element.tag)
        if namespace != SVG_NS or tag not in SVG_ELEMENTS:
            return False
        for name, value in element.attrib.items():
            attr_ns, attr = _split(name)
            if attr_ns not in (None, XLINK_NS) or attr not in SVG_ATTRIBUTES:
                return False
            if attr == "href" and not _LOCAL_REF.match(value.strip()):
                return False
            if _URL_FUNC.search(value):
                return False
    return True


def save_image_bytes(data: bytes, kind: Kind) -> str:
    rule = RULES[kind]
    if len(data) > rule.max_bytes:
        raise _too_large(rule)
    if not data:
        raise AppError(422, "El archivo está vacío.", code="invalid_image")

    if _looks_like_svg(data):
        if not rule.allow_svg:
            raise AppError(422, "Este tipo de imagen solo acepta PNG, JPG o WebP.", code="invalid_image")
        if not _svg_is_safe(data):
            raise AppError(422, "El SVG contiene elementos no permitidos.", code="invalid_image")
        return _store(data, kind, "svg")

    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in RASTER_FORMATS:
            raise AppError(422, "Formato no permitido: usa PNG, JPG, WebP o SVG.", code="invalid_image")
        with Image.open(io.BytesIO(data)) as image:
            image.thumbnail((rule.max_side, rule.max_side))
            output = io.BytesIO()
            mode = "RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB"
            image.convert(mode).save(output, "WEBP", quality=85, method=4)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise AppError(422, "El archivo no es una imagen válida.", code="invalid_image") from exc
    return _store(output.getvalue(), kind, "webp")


async def save_upload(file: UploadFile, kind: Kind) -> str:
    rule = RULES[kind]
    data = await file.read(rule.max_bytes + 1)  # never read more than the limit
    if len(data) > rule.max_bytes:
        raise _too_large(rule)
    return save_image_bytes(data, kind)


def delete_media(url: str | None) -> None:
    """Best-effort removal of a file previously returned by save_*; ignores foreign URLs."""
    if not url or not url.startswith("/media/"):
        return
    if media_storage() == "database":
        key = url.removeprefix("/media/")
        if MEDIA_KEY.fullmatch(key):
            try:  # runs after the caller committed: an orphan row is better than a 500 for a saved change
                with SessionLocal() as db:
                    db.execute(delete(MediaObject).where(MediaObject.key == key))
                    db.commit()
            except SQLAlchemyError:
                log.warning("media delete failed: %s", key, exc_info=True)
        return
    base = Path(get_settings().media_dir).resolve()
    target = (base / url.removeprefix("/media/")).resolve()
    if base in target.parents and target.is_file():
        target.unlink()
