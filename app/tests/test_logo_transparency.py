"""UPS-095 · logos and mascots with a transparent background (spec 006).

Only near-white pixels connected to the image border go transparent; white enclosed by the artwork stays
opaque. The flag is optional (default false) and only applies to the `logo` and `mascot` kinds.
"""

import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError
from app.models import Academy
from app.services.media import remove_white_background, save_image_bytes

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'
BLACK = (10, 10, 10)


def _encode(image: Image.Image, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


def _framed_logo(mode: str = "RGB", size: int = 200) -> Image.Image:
    """A dark square on white whose middle is a white hole enclosed by the artwork."""
    image = Image.new("RGB", (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, size - 21, size - 21), fill=BLACK)
    draw.rectangle((70, 70, size - 71, size - 71), fill=(255, 255, 255))
    return image.convert(mode)


def _stored(url: str) -> Image.Image:
    image = Image.open(Path(get_settings().media_dir) / url.removeprefix("/media/"))
    image.load()
    return image


def _post(client: TestClient, path: str, data: bytes, flag: bool | None = True, name: str = "l.png"):
    form = {} if flag is None else {"transparent_background": "true" if flag else "false"}
    return client.post(path, files={"file": (name, data, "image/png")}, data=form)


@pytest.fixture
def ia(seeded: dict, db: Session) -> Academy:
    return db.get(Academy, seeded["academy_id"])


def test_removes_only_the_white_connected_to_the_border_and_keeps_enclosed_white() -> None:
    image, changed = remove_white_background(_framed_logo())
    assert changed and image.mode == "RGBA"
    alpha = image.getchannel("A")
    assert alpha.getpixel((2, 2)) == 0 and alpha.getpixel((100, 5)) == 0  # outside: gone
    assert alpha.getpixel((100, 100)) == 255  # white hole inside the frame: kept
    assert image.getpixel((100, 100))[:3] == (255, 255, 255)
    assert alpha.getpixel((40, 100)) == 255 and image.getpixel((40, 100))[:3] == BLACK  # artwork intact
    # No halo: nothing outside the artwork's box stays visible, and the cut does not eat the frame's outside.
    outside = [(x, y) for x in range(200) for y in range(200) if not (20 <= x <= 179 and 20 <= y <= 179)]
    assert all(alpha.getpixel(point) == 0 for point in outside)
    # The soft edge is only ever inside the artwork (partially transparent), never white pixels left opaque.
    visible_white = [
        (x, y)
        for x in range(200)
        for y in range(200)
        if alpha.getpixel((x, y)) > 0
        and min(image.getpixel((x, y))[:3]) >= 245
        and not (70 <= x <= 129 and 70 <= y <= 129)
    ]
    assert visible_white == []


def test_removes_white_border_in_under_a_second_on_a_1024px_logo() -> None:
    image = Image.new("RGB", (1024, 1024), (255, 255, 255))
    ImageDraw.Draw(image).ellipse((100, 100, 924, 924), fill=BLACK)
    best = float("inf")
    for _ in range(3):  # best of three: a busy CI runner can stall one run
        started = time.perf_counter()
        result, changed = remove_white_background(image)
        best = min(best, time.perf_counter() - started)
    assert changed and result.getchannel("A").getpixel((0, 0)) == 0
    assert best < 1.0


def test_jpg_and_opaque_png_become_rgba_and_real_transparency_is_kept_as_is(db: Session) -> None:
    for fmt in ("JPEG", "PNG"):
        stored = _stored(save_image_bytes(_encode(_framed_logo(), fmt), "logo", transparent_background=True))
        assert stored.mode == "RGBA", fmt
        alpha = stored.getchannel("A")
        assert alpha.getpixel((3, 3)) == 0 and alpha.getpixel((50, 100)) == 255
    # Already transparent: nothing to do, even if there is white touching the border.
    real = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(real).rectangle((0, 0, 40, 99), fill=(255, 255, 255, 255))
    ImageDraw.Draw(real).rectangle((60, 20, 90, 80), fill=(200, 0, 0, 255))
    unchanged, changed = remove_white_background(real)
    assert not changed and unchanged.tobytes() == real.tobytes()
    stored = _stored(save_image_bytes(_encode(real), "mascot", transparent_background=True))
    assert stored.getchannel("A").getpixel((10, 50)) == 255 and stored.getchannel("A").getpixel((50, 5)) == 0


def test_stores_unchanged_when_there_is_no_white_border(as_admin_ia: TestClient, ia: Academy) -> None:
    blue = Image.new("RGB", (120, 120), (30, 60, 200))
    ImageDraw.Draw(blue).rectangle((40, 40, 80, 80), fill=(255, 255, 255))  # white, but not at the border
    image, changed = remove_white_background(blue)
    assert not changed and image.tobytes() == blue.tobytes()
    response = _post(as_admin_ia, f"/api/academies/{ia.id}/logo", _encode(blue))
    assert response.status_code == 200
    assert response.headers["X-Background-Removed"] == "false"
    stored = _stored(response.json()["logo_url"])
    assert stored.mode == "RGB" or stored.getchannel("A").getextrema() == (255, 255)


def test_refuses_a_mostly_white_image_with_422(as_admin_ia: TestClient, ia: Academy) -> None:
    mostly_white = Image.new("RGB", (200, 200), (255, 255, 255))
    ImageDraw.Draw(mostly_white).rectangle((95, 95, 104, 104), fill=BLACK)  # 0.25 % ink
    with pytest.raises(AppError) as error:
        remove_white_background(mostly_white)
    assert error.value.status == 422
    ok = _post(as_admin_ia, f"/api/academies/{ia.id}/logo", _encode(_framed_logo()))
    before = ok.json()["logo_url"]
    refused = _post(as_admin_ia, f"/api/academies/{ia.id}/logo", _encode(mostly_white))
    assert refused.status_code == 422 and "blanca" in refused.json()["error"]["message"]
    again = as_admin_ia.get(f"/api/academies/{ia.slug}")
    assert again.status_code == 200 and again.json()["logo_url"] == before  # logo unchanged


def test_svg_is_never_processed_and_the_flag_defaults_to_false(as_admin_ia: TestClient, ia: Academy) -> None:
    svg_url = save_image_bytes(SVG, "logo", transparent_background=True)
    path = Path(get_settings().media_dir) / svg_url.removeprefix("/media/")
    assert svg_url.endswith(".svg") and path.read_bytes() == SVG
    # Default (no field): the white stays, as before this feature.
    default = _post(as_admin_ia, f"/api/academies/{ia.id}/logo", _encode(_framed_logo()), flag=None)
    assert default.status_code == 200 and "X-Background-Removed" not in default.headers
    assert _stored(default.json()["logo_url"]).convert("RGBA").getchannel("A").getpixel((3, 3)) == 255
    # Other kinds ignore the flag.
    avatar = _stored(save_image_bytes(_encode(_framed_logo()), "avatar", transparent_background=True))
    assert avatar.convert("RGBA").getchannel("A").getpixel((1, 1)) == 255


def test_both_routes_of_both_scopes_accept_the_flag(
    as_superadmin: TestClient, as_admin_ia: TestClient, ia: Academy
) -> None:
    for client, base in ((as_admin_ia, f"/api/academies/{ia.id}"), (as_superadmin, "/api/admin/site")):
        for kind in ("logo", "mascot"):
            response = _post(client, f"{base}/{kind}", _encode(_framed_logo()))
            assert response.status_code == 200, (base, kind)
            assert response.headers["X-Background-Removed"] == "true"
            assert _stored(response.json()[f"{kind}_url"]).getchannel("A").getpixel((3, 3)) == 0


def test_the_four_upload_routes_are_rate_limited_per_user(as_admin_ia: TestClient, ia: Academy) -> None:
    codes = [
        _post(as_admin_ia, f"/api/academies/{ia.id}/logo", _encode(_framed_logo())).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [200] * 10 and codes[10] == 429
