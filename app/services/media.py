"""Image uploads: real-type check, size limits, resize + re-encode (strips EXIF), random names.

    url = await save_upload(file, "post")   # → "/media/post/<uuid>.webp"

Raster images are re-encoded to WebP. SVG is only accepted for logos/mascots and must pass an
element/attribute allowlist (parsed as XML); `/media` is also served with a `sandbox` CSP (app/main.py).

Storage (UPS-030): files go to MEDIA_DIR, or to the `media_objects` table with MEDIA_STORAGE=database on
hosts whose disk is wiped on every restart (Render free). The URL is the same either way.

Withdrawn uploads (UPS-035, e.g. the image of a post hidden by moderation) leave the public namespace:
`withdraw_media` keeps a copy in `media_objects` under `hidden/<kind>/<name>` (both storage modes) and the
caller then drops the public copy with `delete_media`. `/media` never serves that key: the database route
only accepts MEDIA_KEY and the disk mount only reads MEDIA_DIR. Moderators read it with `load_withdrawn`.
"""

import io
import logging
import mimetypes
import re
import uuid
import xml.etree.ElementTree as ET  # noqa: S405 (DTDs/entities are rejected before parsing)
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from PIL import Image, ImageOps
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.errors import AppError
from app.models import MediaObject

log = logging.getLogger(__name__)
Kind = Literal["logo", "mascot", "avatar", "post", "cover", "resource", "mail"]
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
    "mail": Rule(5 * MB, 1200),  # UPS-088: JPEG/PNG for email clients; max_side is the width
}
RASTER_FORMATS = {"PNG", "JPEG", "WEBP"}
CONTENT_TYPES = {"webp": "image/webp", "svg": "image/svg+xml", "jpg": "image/jpeg", "png": "image/png"}
MEDIA_KEY = re.compile(r"[a-z]+/[0-9a-f]{32}\.(?:webp|svg|jpg|png)")  # <kind>/<name>.<ext>


def register_media_types() -> None:
    """Serve what _store writes with its real type whatever the OS mime table holds (UPS-063).

    With MEDIA_STORAGE=disk, StaticFiles guesses the Content-Type with `mimetypes`, whose built-in table has
    no .webp before Python 3.13: on Windows without it in the registry (or an image without /etc/mime.types)
    every upload went out as application/octet-stream, which browsers may refuse under `nosniff`.
    """
    for extension, content_type in CONTENT_TYPES.items():
        mimetypes.add_type(content_type, f".{extension}")


register_media_types()
WITHDRAWN = "hidden/"  # prefix of moderator-only copies; never matches MEDIA_KEY
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
_XML_DECLARATION = re.compile(rb"\A\s*<\?xml\s[^>]*\?>", re.IGNORECASE)
MAX_USE_ELEMENTS = 20  # `use` copies render once each: a small cap keeps a logo cheap to paint


def _too_large(rule: Rule) -> AppError:
    return AppError(413, f"La imagen supera {rule.max_bytes // MB} MB.")


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    media_storage: Literal["disk", "database"] = "disk"


@lru_cache
def media_storage() -> str:
    return StorageSettings().media_storage


def store_named(data: bytes, kind: str, name: str) -> str:
    """Write `<kind>/<name>` (the name is already `<32 hex>.<ext>`); same name = same content."""
    extension = name.rsplit(".", 1)[1]
    if media_storage() == "database":
        # Its own short transaction, like the file write: the bytes exist before any row points to them.
        with SessionLocal() as db:
            db.merge(MediaObject(key=f"{kind}/{name}", content_type=CONTENT_TYPES[extension], data=data))
            db.commit()
    else:
        folder = Path(get_settings().media_dir) / kind
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
    return f"/media/{kind}/{name}"


def _store(data: bytes, kind: str, extension: str) -> str:
    return store_named(data, kind, f"{uuid.uuid4().hex}.{extension}")


def read_public(key: str) -> bytes | None:
    """The bytes of a stored public upload (either storage mode), or None when it does not exist."""
    if not MEDIA_KEY.fullmatch(key):
        return None
    if media_storage() == "database":
        with SessionLocal() as db:
            stored = db.get(MediaObject, key)
            return stored.data if stored else None
    path = Path(get_settings().media_dir) / key
    return path.read_bytes() if path.is_file() else None


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


def _use_is_cheap(root: ET.Element) -> bool:
    """At most MAX_USE_ELEMENTS `use`, and none points at something that holds another `use` (no fan-out)."""
    uses = [element for element in root.iter() if _split(element.tag)[1] == "use"]
    if len(uses) > MAX_USE_ELEMENTS:
        return False
    ids = [element.get("id") for element in root.iter() if element.get("id")]
    if len(ids) != len(set(ids)):  # renderers pick the first of two equal ids: the check below must not guess
        return False
    by_id = {element.get("id"): element for element in root.iter() if element.get("id")}
    for use in uses:
        for name, value in use.attrib.items():
            if _split(name)[1] != "href":
                continue
            target = by_id.get(value.strip().removeprefix("#"))
            if target is not None and any(_split(inner.tag)[1] == "use" for inner in target.iter()):
                return False
    return True


def _svg_is_safe(data: bytes) -> bool:
    """Allowlist: SVG-namespace shapes only, no scripts/styles/events, references only to local ids."""
    if re.search(rb"<!(DOCTYPE|ENTITY)", data, re.IGNORECASE):
        return False
    # ElementTree drops processing instructions but the raw bytes are stored: only the declaration has `<?`.
    if b"<?" in _XML_DECLARATION.sub(b"", data, count=1):
        return False
    try:
        root = ET.fromstring(data)  # noqa: S314 (no DTD → no entity expansion)
    except ET.ParseError:
        return False
    if not _use_is_cheap(root):
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


def _has_transparency(image: Image.Image) -> bool:
    if image.mode in ("RGBA", "LA"):
        return image.getchannel("A").getextrema()[0] < 255
    return image.mode == "P" and "transparency" in image.info


def encode_for_email(image: Image.Image, max_width: int = 1200) -> tuple[bytes, str]:
    """(bytes, extension): PNG when the image has transparency, else JPEG; never wider than `max_width`.

    Outlook desktop shows no WebP and no client shows SVG. Transparency is kept (not flattened onto white),
    so a logo with a transparent background still reads in Gmail dark mode. EXIF is dropped.
    """
    image = ImageOps.exif_transpose(image)
    transparent = _has_transparency(image)
    if image.width > max_width:
        image = image.resize((max_width, max(1, round(image.height * max_width / image.width))))
    output = io.BytesIO()
    if transparent:
        image.convert("RGBA").save(output, "PNG", optimize=True)
        return output.getvalue(), "png"
    image.convert("RGB").save(output, "JPEG", quality=88, optimize=True)
    return output.getvalue(), "jpg"


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

    invalid = AppError(422, "El archivo no es una imagen válida.", code="invalid_image")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
    except Exception as exc:  # any failure on untrusted bytes: bomb, bad CRC (SyntaxError)…
        raise invalid from exc
    if fmt not in RASTER_FORMATS:
        raise AppError(422, "Formato no permitido: usa PNG, JPG, WebP o SVG.", code="invalid_image")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if kind == "mail":
                encoded, extension = encode_for_email(image, rule.max_side)
                return _store(encoded, kind, extension)
            image.thumbnail((rule.max_side, rule.max_side))
            output = io.BytesIO()
            mode = "RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB"
            image.convert(mode).save(output, "WEBP", quality=85, method=4)
    except Exception as exc:  # verify() does not decode pixels: broken data fails here
        raise invalid from exc
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


def _public_key(url: str | None) -> str | None:
    key = url.removeprefix("/media/") if url and url.startswith("/media/") else None
    return key if key and MEDIA_KEY.fullmatch(key) else None


def withdraw_media(db: Session, url: str | None) -> None:
    """Keeps a moderator-only copy of an upload in the caller's session (committed with its change).

    With MEDIA_STORAGE=database the public row is removed in that same transaction; on disk the caller
    unlinks the file with delete_media(url) after committing. Unknown or foreign URLs are ignored.
    """
    key = _public_key(url)
    if key is None:
        return
    if media_storage() == "database":
        stored = db.get(MediaObject, key)
        if stored is None:
            return
        data, content_type = stored.data, stored.content_type
        db.delete(stored)
    else:
        path = Path(get_settings().media_dir) / key
        if not path.is_file():
            return
        data, content_type = path.read_bytes(), CONTENT_TYPES[key.rsplit(".", 1)[1]]
    db.merge(MediaObject(key=WITHDRAWN + key, content_type=content_type, data=data))
    db.flush()


def load_withdrawn(db: Session, url: str | None) -> MediaObject | None:
    """The moderator-only copy kept by withdraw_media, or None."""
    key = _public_key(url)
    return db.get(MediaObject, WITHDRAWN + key) if key else None
