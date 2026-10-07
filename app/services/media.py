"""Image uploads: real-type check, size limits, resize + re-encode (strips EXIF), random names.

    url = await save_upload(file, "post")   # → "/media/post/<uuid>.webp"

Raster images are re-encoded to WebP. SVG is only accepted for logos/mascots, after a strict check;
`/media` is also served with a `sandbox` CSP (app/main.py), so a file can never run scripts.
"""

import io
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.errors import AppError

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
_SVG_FORBIDDEN = re.compile(
    rb"<\s*script|<\s*foreignObject|\bon[a-z]+\s*=|javascript:|<!ENTITY|<\s*iframe|<\s*embed|<\s*object"
    rb"|(?:xlink:)?href\s*=\s*[\"'](?!#)",
    re.IGNORECASE,
)


def _too_large(rule: Rule) -> AppError:
    return AppError(413, f"La imagen supera {rule.max_bytes // MB} MB.")


def _store(data: bytes, kind: str, extension: str) -> str:
    folder = Path(get_settings().media_dir) / kind
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{extension}"
    (folder / name).write_bytes(data)
    return f"/media/{kind}/{name}"


def _looks_like_svg(data: bytes) -> bool:
    head = data[:512].lstrip().lower()
    return head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2048].lower())


def save_image_bytes(data: bytes, kind: Kind) -> str:
    rule = RULES[kind]
    if len(data) > rule.max_bytes:
        raise _too_large(rule)
    if not data:
        raise AppError(422, "El archivo está vacío.", code="invalid_image")

    if _looks_like_svg(data):
        if not rule.allow_svg:
            raise AppError(422, "Este tipo de imagen solo acepta PNG, JPG o WebP.", code="invalid_image")
        if _SVG_FORBIDDEN.search(data):
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
    base = Path(get_settings().media_dir).resolve()
    target = (base / url.removeprefix("/media/")).resolve()
    if base in target.parents and target.is_file():
        target.unlink()
