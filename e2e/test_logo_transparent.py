"""Logos and mascots with a transparent background (UPS-095), in a real browser at 1280 and 390 wide.

A superadmin uploads a logo on a white background with "Quitar el fondo blanco" checked (the default) and sees
it on the light and dark swatches without a white box; a mostly white image is refused and the logo stays;
"Quitar fondo blanco al logo actual" sends the stored `/media/…` image back through the same route with the
flag on (and only same-origin requests are made). The club panel offers the same box and button.

One sign-in per viewport (the module's server is shared by its tests); the brand is restored at the end."""

import io
import re

from PIL import Image, ImageDraw
from playwright.sync_api import Page, expect

from e2e.conftest import Site
from e2e.test_content import as_superadmin
from e2e.test_site_brand import restore_brand, superadmin_token

LOGO_UPLOADED = "Logo actualizado en todo el campus."


def on_white(size: tuple[int, int] = (400, 200)) -> dict:
    """A dark badge with a white dot inside, on a pure white background (a JPG-style export)."""
    image = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((100, 20, 300, 180), fill=(4, 148, 79))
    draw.ellipse((170, 70, 230, 130), fill=(255, 255, 255))  # white enclosed by the artwork
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return {"name": "logo.png", "mimeType": "image/png", "buffer": buffer.getvalue()}


def mostly_white() -> dict:
    image = Image.new("RGB", (300, 300), (255, 255, 255))
    ImageDraw.Draw(image).rectangle((140, 140, 150, 150), fill=(0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return {"name": "blanco.png", "mimeType": "image/png", "buffer": buffer.getvalue()}


def alpha_at(page: Page, site: Site, src: str, point: tuple[int, int]) -> tuple[int, int, int, int]:
    body = page.request.get(site.url(src)).body()
    return Image.open(io.BytesIO(body)).convert("RGBA").getpixel(point)


def stored_logo(page: Page, previous: str = "") -> str:
    """The uploaded logo's url, once it is not `previous` any more (the new upload has been applied)."""
    image = page.get_by_test_id("site-logo").get_by_role("img", name="Logo actual")
    expect(image).to_have_attribute("src", re.compile(r"^/media/logo/.+\.webp$"))
    if previous:
        expect(image).not_to_have_attribute("src", previous)
    return image.get_attribute("src") or ""


def test_superadmin_logo_loses_its_white_background(site: Site) -> None:
    token = superadmin_token(site)
    try:
        brand_tab(site)
    finally:
        restore_brand(site, token)


def brand_tab(site: Site) -> None:
    page = as_superadmin(site, "/admin?tab=marca")
    box = page.get_by_test_id("transparent-logo").get_by_role(
        "checkbox", name=re.compile("Quitar el fondo blanco")
    )
    expect(box).to_be_checked()  # on by default for the logo...
    expect(
        page.get_by_test_id("transparent-mascot").get_by_role("checkbox")
    ).to_be_checked()  # ...and the mascot

    # Checked: the white around the badge is gone, the white dot inside stays.
    page.get_by_test_id("site-logo").locator("input[type=file]").set_input_files(on_white())
    expect(page.get_by_text(LOGO_UPLOADED).first).to_be_visible()
    src = stored_logo(page)
    assert alpha_at(page, site, src, (2, 2))[3] == 0  # noqa: S101
    assert alpha_at(page, site, src, (200, 100))[3] == 255  # noqa: S101
    swatches = page.get_by_test_id("swatches-logo")
    expect(swatches.get_by_text("Sobre oscuro")).to_be_visible()
    expect(swatches.locator("img")).to_have_count(2)
    page.get_by_test_id("transparent-logo").scroll_into_view_if_needed()
    site.shot("logo-transparent")

    # A mostly white picture is refused and the logo does not change.
    page.get_by_test_id("site-logo").locator("input[type=file]").set_input_files(mostly_white())
    expect(page.get_by_text("casi toda blanca")).to_be_visible()
    assert stored_logo(page) == src  # noqa: S101

    # Unchecked: the white box stays (that is how the original comes back)...
    box.uncheck()
    page.get_by_test_id("site-logo").locator("input[type=file]").set_input_files(on_white())
    expect(page.get_by_text(LOGO_UPLOADED).first).to_be_visible()
    opaque = stored_logo(page, src)
    assert alpha_at(page, site, opaque, (2, 2))[3] == 255  # noqa: S101

    # ...and "Quitar fondo blanco al logo actual" re-sends it through the same route with the flag on.
    page.get_by_test_id("site-logo").get_by_role("button", name="Quitar fondo blanco al logo actual").click()
    expect(page.get_by_text(LOGO_UPLOADED).first).to_be_visible()
    fixed = stored_logo(page, opaque)
    assert alpha_at(page, site, fixed, (2, 2))[3] == 0  # noqa: S101
    assert page.request.get(site.url(opaque)).status == 404  # noqa: S101,PLR2004 (the old file is gone)


def test_fix_current_only_fetches_same_origin_media(site: Site) -> None:
    token = superadmin_token(site)
    try:
        page = as_superadmin(site, "/admin?tab=marca")
        page.get_by_test_id("site-logo").locator("input[type=file]").set_input_files(on_white())
        stored_logo(page)
        requests: list[str] = []
        page.on("request", lambda request: requests.append(request.url))
        page.get_by_test_id("site-logo").get_by_role(
            "button", name="Quitar fondo blanco al logo actual"
        ).click()
        expect(page.get_by_text("No encontramos un fondo blanco para quitar.")).to_be_visible()
        media = [url for url in requests if "/media/" in url]
        assert media and all(url.startswith(site.base_url + "/media/") for url in media), media  # noqa: S101
        site.shot("logo-nothing-to-remove")
    finally:
        restore_brand(site, token)


def test_club_panel_offers_the_same_box_and_button(site: Site) -> None:
    page = as_superadmin(site, "/panel/academia/upiixia?tab=identidad")
    box = page.get_by_test_id("transparent-logo").get_by_role("checkbox")
    expect(box).to_be_checked()
    page.locator("input[type=file][name=logo]").set_input_files(on_white())
    expect(page.get_by_text("Logo actualizado.")).to_be_visible()
    swatches = page.get_by_test_id("swatches-logo")
    expect(swatches.locator("img")).to_have_count(2)
    src = swatches.locator("img").first.get_attribute("src") or ""
    assert alpha_at(page, site, src, (2, 2))[3] == 0  # noqa: S101
    page.get_by_test_id("transparent-logo").scroll_into_view_if_needed()
    site.shot("logo-club-panel")
    page.get_by_role("button", name="Quitar fondo blanco al logo actual").click()
    expect(page.get_by_text("No encontramos un fondo blanco para quitar.")).to_be_visible()
