"""Server-side sanitization (defense in depth; the web also sanitizes with DOMPurify).

- `clean_markdown`: markdown/HTML from posts and descriptions. Keeps markdown text, strips dangerous HTML.
- `safe_url`: only absolute http(s) URLs; anything else (javascript:, data:, relative) is rejected.
Plain-text fields are not touched here: React escapes them on render.
"""

import re
from urllib.parse import urlsplit

import nh3

ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}
ALLOWED_SCHEMES = {"http", "https", "mailto"}


def clean_markdown(text: str) -> str:
    cleaned = nh3.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel="noopener noreferrer nofollow",
        strip_comments=True,
    )
    # nh3 escapes `>`; restore it only as a markdown blockquote marker at line start. Never un-escape `&`:
    # `&amp;colon;` would turn back into `&colon;`, which browsers decode inside href (javascript:).
    return _QUOTE_MARKER.sub(lambda m: m.group(1) + ">", cleaned)


_QUOTE_MARKER = re.compile(r"(?m)^([ \t]*)&gt;")


def safe_url(url: str) -> str:
    candidate = url.strip()
    parts = urlsplit(candidate)
    if (
        parts.scheme.lower() not in {"http", "https"}
        or not parts.hostname
        or any(c.isspace() for c in candidate)
    ):
        raise ValueError("La URL debe empezar con http:// o https://")
    return candidate
