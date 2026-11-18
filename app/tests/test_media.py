import asyncio
import io
from pathlib import Path

import pytest
from fastapi import UploadFile
from PIL import Image

from app.config import get_settings
from app.errors import AppError
from app.services.media import MB, delete_media, register_media_types, save_image_bytes, save_upload


def _png(size=(2000, 1000), mode="RGBA") -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, (0, 191, 99, 255) if mode == "RGBA" else (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def _media_path(url: str) -> Path:
    return Path(get_settings().media_dir) / url.removeprefix("/media/")


def test_raster_is_resized_and_reencoded_to_webp() -> None:
    url = save_image_bytes(_png(), "avatar")
    assert url.startswith("/media/avatar/") and url.endswith(".webp")
    with Image.open(_media_path(url)) as image:
        assert image.format == "WEBP" and max(image.size) == 256


def test_jpeg_without_alpha() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buffer, "JPEG")
    assert save_image_bytes(buffer.getvalue(), "post").endswith(".webp")


@pytest.mark.parametrize("data", [b"not an image", b"GIF89a" + b"\x00" * 20, b"%PDF-1.4 fake"])
def test_rejects_non_images(data: bytes) -> None:
    with pytest.raises(AppError) as error:
        save_image_bytes(data, "post")
    assert error.value.status == 422


def test_rejects_unsupported_real_format_even_if_named_png() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, "GIF")
    with pytest.raises(AppError) as error:
        save_image_bytes(buffer.getvalue(), "post")
    assert error.value.status == 422


def test_rejects_empty_and_oversized() -> None:
    with pytest.raises(AppError) as empty:
        save_image_bytes(b"", "post")
    assert empty.value.status == 422
    with pytest.raises(AppError) as big:
        save_image_bytes(b"x" * (2 * MB + 1), "logo")
    assert big.value.status == 413


SVG_OPEN = b'<svg xmlns="http://www.w3.org/2000/svg">'


def test_svg_only_for_logos_and_must_be_clean() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
        b' viewBox="0 0 10 10">'
        b'<defs><linearGradient id="g"><stop offset="0" stop-color="#00BF63"/></linearGradient></defs>'
        b'<circle r="5" fill="url(#g)"/><use xlink:href="#g"/></svg>'
    )
    url = save_image_bytes(svg, "logo")
    assert url.endswith(".svg") and _media_path(url).read_bytes() == svg
    assert save_image_bytes(b'<?xml version="1.0"?>\n' + svg, "mascot").endswith(".svg")
    with pytest.raises(AppError):
        save_image_bytes(svg, "post")
    for evil in (
        b"<svg><script>alert(1)</script></svg>",
        b'<svg onload="alert(1)"></svg>',
        b'<svg><a href="javascript:alert(1)">x</a></svg>',
        b'<svg><image href="https://evil.com/x.png"/></svg>',
        b"<svg><foreignObject><div/></foreignObject></svg>",
        # Regressions from the security review (bypassed the old denylist):
        SVG_OPEN + b'<x:script xmlns:x="http://www.w3.org/2000/svg">alert(1)</x:script></svg>',
        SVG_OPEN + b'<animate attributeName="href" values="javascript&#58;alert(1)"/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://evil.com/x.css)</style></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="url(https://evil.com/p)"/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><use href="https://evil.com/a.svg#x"/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><rect data-x="1"/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:o="urn:other"><rect o:fill="red"/></svg>',
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "b">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>',
        b"<svg><rect></svg>",
        b"<svg><rect/></svg>",  # no SVG namespace
    ):
        with pytest.raises(AppError):
            save_image_bytes(evil, "logo")


def test_svg_rejects_processing_instruction() -> None:
    # ElementTree drops processing instructions, so the raw bytes would keep the PI inside (UPS-050).
    body = SVG_OPEN + b'<path d="M0 0"/></svg>'
    pi = b'<?xml-stylesheet type="text/xsl" href="https://evil.example/x.xsl"?>'
    declaration = b'<?xml version="1.0"?>\n'
    for evil in (pi + body, declaration + pi + body, declaration + SVG_OPEN + pi + b"</svg>"):
        with pytest.raises(AppError) as error:
            save_image_bytes(evil, "logo")
        assert error.value.status == 422


def test_svg_rejects_use_fan_out() -> None:
    many = SVG_OPEN + b'<defs><path id="p" d="M0 0"/></defs>' + b'<use href="#p"/>' * 21 + b"</svg>"
    # A `use` that points at a group holding another `use` multiplies the work at every level.
    nested = (
        SVG_OPEN + b'<defs><g id="a"><use href="#b"/><use href="#b"/></g>'
        b'<g id="b"><path d="M0 0"/></g></defs><use href="#a"/></svg>'
    )
    chained = SVG_OPEN + b'<defs><use id="a" href="#b"/><path id="b" d="M0 0"/></defs><use href="#a"/></svg>'
    # Renderers resolve a duplicated id to the first element: a check that keeps the last is blind to it.
    duplicated = (
        SVG_OPEN + b'<g id="a"><use href="#b"/></g><g id="a"><path d="M0 0"/></g><path id="b" d="M0 0"/>'
        b'<use href="#a"/></svg>'
    )
    for evil in (many, nested, chained, duplicated):
        with pytest.raises(AppError) as error:
            save_image_bytes(evil, "logo")
        assert error.value.status == 422


def test_svg_plain_logo_still_accepted() -> None:
    svg = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        + SVG_OPEN
        + b'<defs><symbol id="s"><path d="M0 0h5v5z"/></symbol>'
        + b'<linearGradient id="g"><stop offset="0"/></linearGradient></defs>'
        + b'<g><use href="#s"/><use href="#s" x="6"/></g><circle r="5" fill="url(#g)"/>'
        + b'<use href="#g"/>' * 18  # 20 `use` in all: exactly at the cap
        + b"</svg>"
    )
    assert save_image_bytes(svg, "logo").endswith(".svg")


def test_save_upload_reads_at_most_the_limit() -> None:
    upload = UploadFile(io.BytesIO(_png((40, 40))), filename="x.png")
    assert asyncio.run(save_upload(upload, "post")).endswith(".webp")
    huge = UploadFile(io.BytesIO(b"x" * (2 * MB + 10)), filename="big.png")
    with pytest.raises(AppError) as error:
        asyncio.run(save_upload(huge, "avatar"))
    assert error.value.status == 413


def test_delete_media_only_inside_media_dir(tmp_path: Path) -> None:
    url = save_image_bytes(_png((10, 10)), "post")
    delete_media(url)
    assert not _media_path(url).exists()
    outside = tmp_path / "keep.txt"
    outside.write_text("x")
    delete_media("/media/../../" + str(outside))
    delete_media("https://evil.com/x.png")
    delete_media(None)
    assert outside.exists()


def broken_png(*, bad_crc: bool) -> bytes:
    """1x1 PNG with a valid header and a broken IDAT: bad checksum (verify() raises SyntaxError, not
    OSError: was a 500) or a valid checksum over bytes that are not zlib (fails only when decoding)."""
    import struct
    import zlib

    def chunk(kind: bytes, data: bytes, crc: int | None = None) -> bytes:
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF if crc is None else crc
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    header = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", b"garbage-not-zlib", 0 if bad_crc else None)
    return b"\x89PNG\r\n\x1a\n" + header + idat + chunk(b"IEND", b"")


@pytest.mark.parametrize("bad_crc", [True, False])
def test_malformed_png_is_422_not_500(bad_crc: bool) -> None:
    with pytest.raises(AppError) as error:
        save_image_bytes(broken_png(bad_crc=bad_crc), "post")
    assert error.value.status == 422 and error.value.code == "invalid_image"


# ── UPS-063: WebP served as image/webp on every OS ───────────


@pytest.fixture
def os_without_webp(monkeypatch: pytest.MonkeyPatch):
    """Python's built-in mime table only (no OS files), as on Windows without the type or a slim image:
    before Python 3.13 it has no .webp."""
    import mimetypes

    monkeypatch.setattr(mimetypes, "knownfiles", [])  # init() would read the OS files again otherwise
    monkeypatch.setattr(mimetypes, "_db", None)  # and it would reuse the table already loaded
    mimetypes.init(files=[])
    assert mimetypes.guess_type("x.webp")[0] is None  # the simulated OS really lacks it (Python < 3.13)
    yield
    monkeypatch.undo()
    mimetypes._db = None
    mimetypes.init()  # back to this machine's table
    register_media_types()


def test_webp_is_served_as_image_webp_without_an_os_mime_table(client, os_without_webp) -> None:
    url = save_image_bytes(_png(), "avatar")
    register_media_types()  # what the app does when media loads
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]


def test_svg_keeps_its_type_without_an_os_mime_table(client, os_without_webp) -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'
    url = save_image_bytes(svg, "logo")
    register_media_types()
    assert client.get(url).headers["content-type"].startswith("image/svg+xml")
