"""Email images (UPS-088, spec 004 §Images): PNG/JPEG copies, because Outlook desktop shows no WebP.

`email_copy(url)` gives the renderer a URL an email client can show for a site/club logo or an event cover.
The copy is cached by name: `mail/<sha256 of the source key>[:32].png|jpg`, so no table is needed and the
same source always maps to the same copy. An SVG cannot be rasterized without a new dependency: None.
"""

import hashlib
import io
import logging
from urllib.parse import urlsplit

from PIL import Image

from app.config import get_settings
from app.services import media

log = logging.getLogger(__name__)
_STATIC_RASTER = (".png", ".jpg", ".jpeg")


def _local_path(url: str) -> str:
    """The path of `url`, whether it is relative or an absolute URL of this site."""
    parts = urlsplit(url)
    if parts.scheme and parts.netloc:
        base = urlsplit(get_settings().public_base_url)
        if parts.netloc != base.netloc:
            return ""  # a foreign host: not ours to read or copy
    return parts.path


def email_copy(url: str | None) -> str | None:
    """A PNG/JPEG URL for `url`, or None when there is none (SVG, missing or unreadable source)."""
    if not url:
        return None
    path = _local_path(url)
    lowered = (path or url).lower()
    if lowered.endswith(".svg"):
        return None
    if lowered.endswith(_STATIC_RASTER):
        return url  # already something every client shows (e.g. /brand/upiixsol/wordmark.png)
    if not path.startswith("/media/") or not lowered.endswith(".webp"):
        return None
    key = path.removeprefix("/media/")
    digest = hashlib.sha256(key.encode()).hexdigest()[:32]
    for extension in ("png", "jpg"):  # cached from an earlier call
        if media.read_public(f"mail/{digest}.{extension}") is not None:
            return f"/media/mail/{digest}.{extension}"
    source = media.read_public(key)
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
