"""Parse YouTube URLs into a video id and build safe embed/thumbnail URLs.

Pure stdlib: the server never fetches the URL, it only validates it (see docs/spikes/youtube.md).
"""

import re
from urllib.parse import parse_qs, urlencode, urlsplit

_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_EMBED_HOSTS = _WATCH_HOSTS | {"youtube-nocookie.com", "www.youtube-nocookie.com"}
_SHORT_HOSTS = {"youtu.be"}
_PATH_PREFIXES = ("embed", "shorts", "live", "v")
# Segment bounds (UPS-045): one day, the same cap the API schemas use.
MAX_SECONDS = 86_400
_PLAIN_SECONDS = re.compile(r"\d{1,6}")
_CLOCK = re.compile(r"(?:(\d{1,2})h)?(?:(\d{1,4})m)?(?:(\d{1,6})s)?")
_TIME_KEYS = ("t", "start")


def _valid(candidate: str | None) -> str | None:
    return candidate if candidate and _ID.fullmatch(candidate) else None


def extract_video_id(url: str) -> str | None:
    """Return the 11-char video id, or None if `url` is not a recognised YouTube URL."""
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or "@" in parts.netloc:
        return None
    host = (parts.hostname or "").lower()
    segments = [s for s in parts.path.split("/") if s]

    if host in _SHORT_HOSTS:
        return _valid(segments[0]) if len(segments) == 1 else None
    if host in _WATCH_HOSTS and segments == ["watch"]:
        values = parse_qs(parts.query).get("v", [])
        return _valid(values[0]) if len(values) == 1 else None
    if host in _EMBED_HOSTS and len(segments) == 2 and segments[0] in _PATH_PREFIXES:
        return _valid(segments[1])
    return None


def _require_id(video_id: str) -> str:
    if not _valid(video_id):
        raise ValueError("invalid YouTube video id")
    return video_id


def _seconds(value: str) -> int | None:
    """850, 850s, 14m10s or 1h2m3s → seconds; anything else (or past one day) → None."""
    if len(value) > 12:
        return None
    if _PLAIN_SECONDS.fullmatch(value):
        total = int(value)
    else:
        match = _CLOCK.fullmatch(value)
        if not match or not any(match.groups()):
            return None
        hours, minutes, seconds = (int(group or 0) for group in match.groups())
        total = hours * 3600 + minutes * 60 + seconds
    return total if total <= MAX_SECONDS else None


def parse_start(url: str) -> int | None:
    """The start time a YouTube URL carries (`t=` or `start=`, in the query or the fragment), or None.

    Parses the string only (no fetch). More than one time value, or any value outside the known forms,
    gives None, so nothing but a validated int ever reaches an embed URL (UPS-045).
    """
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    values = [
        value
        for section in (parts.query, parts.fragment)
        for key, found in parse_qs(section, keep_blank_values=True).items()
        if key in _TIME_KEYS
        for value in found
    ]
    return _seconds(values[0]) if len(values) == 1 else None


def _require_seconds(value: object) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SECONDS:
        raise ValueError("invalid segment second")
    return value


def embed_url(video_id: str, start_s: int | None = None, end_s: int | None = None) -> str:
    """Privacy-enhanced embed; `start`/`end` only from validated ints. No segment → today's exact URL."""
    base = f"https://www.youtube-nocookie.com/embed/{_require_id(video_id)}"
    params = {
        key: _require_seconds(value)
        for key, value in (("start", start_s), ("end", end_s))
        if value is not None
    }
    return f"{base}?{urlencode(params)}" if params else base


def thumbnail_url(video_id: str) -> str:
    return f"https://img.youtube.com/vi/{_require_id(video_id)}/hqdefault.jpg"
