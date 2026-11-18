"""Email images (UPS-088, spec 004 §Images): PNG/JPEG copies, because Outlook desktop shows no WebP.

`email_copy(url)` gives the renderer a URL an email client can show for a site/club logo or an event cover.
The copy is cached by name: `mail/<sha256 of the source key>[:32].png|jpg`, so no table is needed and the
same source always maps to the same copy. An SVG logo is rasterized on the server with resvg-py (UPS-099);
the site keeps serving the SVG, only emails get the PNG.
"""

import hashlib
import io
import logging
from urllib.parse import urlsplit

import resvg_py
from PIL import Image

from app.config import get_settings
from app.services import media

log = logging.getLogger(__name__)
_STATIC_RASTER = (".png", ".jpg", ".jpeg")
SVG_RENDER_HEIGHT = 144  # 3x the 48 px header: sharp on high-density screens
SVG_MAX_WIDTH = 1200
SVG_MAX_BYTES = 512 * 1024  # the logo upload limit is far lower; a bound for stray rows anyway


def _local_path(url: str) -> str:
    """The path of `url`, whether it is relative or an absolute URL of this site."""
    parts = urlsplit(url)
    if parts.scheme and parts.netloc:
        base = urlsplit(get_settings().public_base_url)
        if parts.netloc != base.netloc:
            return ""  # a foreign host: not ours to read or copy
    return parts.path


def _rasterize(svg: bytes) -> bytes:
    """A transparent PNG of an upload-checked SVG: 144 px high, at most 1200 wide, no outside resources."""
    markup = svg.decode("utf-8")
    options = {"skip_system_fonts": True, "resources_dir": None}
    png = bytes(resvg_py.svg_to_bytes(svg_string=markup, height=SVG_RENDER_HEIGHT, **options))
    with Image.open(io.BytesIO(png)) as image:
        too_wide = image.width > SVG_MAX_WIDTH
    if too_wide:
        png = bytes(resvg_py.svg_to_bytes(svg_string=markup, width=SVG_MAX_WIDTH, **options))
    return png


def _svg_copy(source: bytes | None, digest: str) -> str | None:
    if source is None or len(source) > SVG_MAX_BYTES or not media._svg_is_safe(source):
        return None
    try:
        png = _rasterize(source)
    except Exception:  # broken or hostile markup, renderer failure: the wordmark takes over
        log.warning("svg email copy failed: %s", digest, exc_info=True)
        return None
    return media.store_named(png, "mail", f"{digest}.png")


def email_copy(url: str | None) -> str | None:
    """A PNG/JPEG URL for `url`, or None when there is none (SVG, missing or unreadable source)."""
    if not url:
        return None
    path = _local_path(url)
    lowered = (path or url).lower()
    if lowered.endswith(_STATIC_RASTER):
        return url  # already something every client shows (e.g. /brand/upiixsol/wordmark.png)
    is_svg = lowered.endswith(".svg")
    if not path.startswith("/media/") or not (is_svg or lowered.endswith(".webp")):
        return None  # a static /brand SVG, or anything not a stored upload: the wordmark takes over
    key = path.removeprefix("/media/")
    digest = hashlib.sha256(key.encode()).hexdigest()[:32]
    for extension in ("png", "jpg"):  # cached from an earlier call
        if media.read_public(f"mail/{digest}.{extension}") is not None:
            return f"/media/mail/{digest}.{extension}"
    source = media.read_public(key)
    if is_svg:
        return _svg_copy(source, digest)
    if source is None:
        return None
    try:
        with Image.open(io.BytesIO(source)) as image:
            encoded, extension = media.encode_for_email(image, media.RULES["mail"].max_side)
    except Exception:  # untrusted-ish bytes: any decode failure just means no copy
        log.warning("email copy failed: %s", key, exc_info=True)
        return None
    return media.store_named(encoded, "mail", f"{digest}.{extension}")


def email_logo(*candidates: str | None) -> str | None:
    """The first candidate (club logo, then site logo) with an email-safe copy; None → text wordmark."""
    for candidate in candidates:
        copy = email_copy(candidate)
        if copy:
            return copy
    return None
