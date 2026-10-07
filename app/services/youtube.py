"""Parse YouTube URLs into a video id and build safe embed/thumbnail URLs.

Pure stdlib: the server never fetches the URL, it only validates it (see docs/spikes/youtube.md).
"""

import re
from urllib.parse import parse_qs, urlsplit

_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_EMBED_HOSTS = _WATCH_HOSTS | {"youtube-nocookie.com", "www.youtube-nocookie.com"}
_SHORT_HOSTS = {"youtu.be"}
_PATH_PREFIXES = ("embed", "shorts", "live", "v")


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


def embed_url(video_id: str) -> str:
    return f"https://www.youtube-nocookie.com/embed/{_require_id(video_id)}"


def thumbnail_url(video_id: str) -> str:
    return f"https://img.youtube.com/vi/{_require_id(video_id)}/hqdefault.jpg"
