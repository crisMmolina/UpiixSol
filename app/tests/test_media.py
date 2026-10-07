import asyncio
import io
from pathlib import Path

import pytest
from fastapi import UploadFile
from PIL import Image

from app.config import get_settings
from app.errors import AppError
from app.services.media import MB, delete_media, save_image_bytes, save_upload


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
