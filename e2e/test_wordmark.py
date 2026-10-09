"""A club without a logo looks like the logo images (UPS-039): its name is drawn in Fredoka bold, lowercase up
to the "x", plain colors with no outline, at the size of the logo it replaces in each place.

Compares the seeded UpiixIA (logo image) with the same club without a logo (a copy with the same name and
colors, or its own data with `logo_url` removed in flight) in the top bar, the /clubes card and the "mis
clubs" tile: the letters (i dot to p tail) must have the logo's height and place within 2 px and its width
within 4 %. Evidence in e2e/artifacts/<viewport>-wordmark-<place>.png (logo left, text right)."""

import io

from PIL import Image
from playwright.sync_api import Locator, Route, expect

from e2e.conftest import ARTIFACTS, SEED_PASSWORD, Site
from e2e.test_branding import CLUB, assert_fits_phone, create_club_as_superadmin, rgb

MEMBER = "alumno.demo@upiixsol.dev"  # seeded with progress in UpiixIA: the "mis clubs" tile shows it

TEXT_SLUG = "upiixia-texto"
# One word of 72 letters, no spaces to wrap at.
ONE_WORD = {
    **CLUB,
    "slug": "upiix-una-palabra",
    "name": "UpiixNanotecnologiaYBiomecatronicaAplicadaALaExploracionDeLasProfundidades",
}
# Each wordmark piece: text shown (after text-transform), color, outline and font.
PIECES = """
  (root) => [...root.children].map((el) => {
    const s = getComputedStyle(el);
    const shown = s.textTransform === "lowercase" ? el.textContent.toLowerCase() : el.textContent;
    return [shown, s.color, s.textShadow, s.fontWeight, s.fontFamily.split(",")[0].replaceAll('"', "")];
  })
"""


def ink_box(locator: Locator) -> tuple[Image.Image, tuple[float, float, float, float]]:
    """Screenshot of the element and the page box of its non-background pixels (the letters)."""
    shot = Image.open(io.BytesIO(locator.screenshot(animations="disabled"))).convert("RGB")
    background = shot.getpixel((0, 0))
    mask = Image.new("L", shot.size)
    mask.putdata(
        [
            255 if sum(abs(a - b) for a, b in zip(px, background, strict=True)) > 60 else 0
            for px in shot.getdata()
        ]
    )
    box, at = mask.getbbox(), locator.bounding_box()
    assert box and at, "no ink found"  # noqa: S101
    return shot, (at["x"] + box[0], at["y"] + box[1], at["x"] + box[2], at["y"] + box[3])


def compare(
    site: Site, place: str, logo: tuple[Locator, Locator], text: tuple[Locator, Locator]
) -> dict[str, tuple[float, float]]:
    """(brand, frame) pairs: the logo image and the text wordmark, each inside the box that holds it. The
    letters must match the logo's height and vertical place in the frame (2 px) and its width (4 %).
    Saves both frames side by side and returns the measured (height, width) of each."""
    (_, logo_ink), (_, text_ink) = ink_box(logo[0]), ink_box(text[0])
    logo_frame, text_frame = logo[1].bounding_box(), text[1].bounding_box()
    assert logo_frame and text_frame  # noqa: S101
    size = {
        "logo": (logo_ink[3] - logo_ink[1], logo_ink[2] - logo_ink[0]),
        "text": (text_ink[3] - text_ink[1], text_ink[2] - text_ink[0]),
    }
    print(f"{site.name} {place}: logo h×w {size['logo']} · text h×w {size['text']}")
    assert abs(size["logo"][0] - size["text"][0]) <= 2, (place, size)  # noqa: S101
    assert abs(size["logo"][1] - size["text"][1]) <= 0.04 * size["logo"][1], (place, size)  # noqa: S101
    top = (logo_ink[1] - logo_frame["y"], text_ink[1] - text_frame["y"])
    assert abs(top[0] - top[1]) <= 2, (place, top)  # noqa: S101

    frames = [
        Image.open(io.BytesIO(frame.screenshot(animations="disabled"))).convert("RGB")
        for frame in (logo[1], text[1])
    ]
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    gap = 16
    side = Image.new("RGB", (frames[0].width + gap + frames[1].width, max(f.height for f in frames)), "white")
    side.paste(frames[0], (0, 0))
    side.paste(frames[1], (frames[0].width + gap, 0))
    side.save(ARTIFACTS / f"{site.name}-wordmark-{place}.png")
    return size


def header_shot(site: Site) -> Image.Image:
    """The left part of the top bar, where the brand is."""
    width = min(site.page.viewport_size["width"], 480) if site.page.viewport_size else 480
    clip = {"x": 0, "y": 0, "width": width, "height": 64}
    return Image.open(io.BytesIO(site.page.screenshot(clip=clip, animations="disabled"))).convert("RGB")


def loaded(image: Locator) -> Locator:
    """Waits for a (lazy) image to be decoded, so its screenshot shows it."""
    expect(image).to_be_visible()
    image.scroll_into_view_if_needed()
    expect(image).to_have_js_property("complete", True)
    return image


def dismiss_toasts(site: Site) -> None:
    """The compact toast lies over the top bar (the logo on phones): close it before measuring."""
    toasts = site.page.get_by_role("region", name="Avisos")
    while toasts.get_by_role("button", name="Descartar").count():
        toasts.get_by_role("button", name="Descartar").first.click()


def test_text_wordmark_matches_the_logo(site: Site) -> None:
    page = site.page
    seeded = page.request.get(site.url("/api/academies/upiixia")).json()
    assert seeded["logo_url"], seeded  # noqa: S101 · the seeded club shows its logo image
    colors = {key: seeded[key] for key in ("color_primary", "color_secondary", "color_accent")}
    create_club_as_superadmin(
        page, site.base_url, {"slug": TEXT_SLUG, "name": seeded["name"], "short_description": "", **colors}
    )

    banner = page.get_by_role("banner")
    page.goto(site.url("/a/upiixia"))
    logo = loaded(banner.get_by_role("img", name=seeded["name"], exact=True))
    dismiss_toasts(site)
    assert logo.evaluate("(el) => el.tagName") == "IMG"  # noqa: S101
    logo_header = header_shot(site)
    logo_ink = ink_box(logo)[1]

    page.goto(site.url(f"/a/{TEXT_SLUG}"))
    text = banner.get_by_role("img", name=seeded["name"], exact=True)
    expect(text).to_be_visible()
    dismiss_toasts(site)
    page.evaluate("document.fonts.ready")
    primary, secondary, accent = (rgb(c) for c in colors.values())
    pieces = text.evaluate(PIECES)
    # "upii" primary · "x" secondary · "IA" accent; plain colors (no outline), Fredoka bold.
    assert [p[0] for p in pieces] == ["upii", "x", "IA"], pieces  # noqa: S101
    assert all(p[2] == "none" and p[3] == "700" and p[4] == "Fredoka" for p in pieces), pieces  # noqa: S101
    assert {p[0]: p[1] for p in pieces} == {"upii": primary, "x": secondary, "IA": accent}, pieces  # noqa: S101
    text_header = header_shot(site)

    # Top bar: same size and place as the logo (the bar is the frame: compare page positions too).
    compare(site, "header", (logo, banner), (text, banner))
    text_ink = ink_box(text)[1]
    assert abs(logo_ink[0] - text_ink[0]) <= 2, (logo_ink, text_ink)  # noqa: S101
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    stacked = Image.new("RGB", (logo_header.width, logo_header.height * 2 + 8), "white")
    stacked.paste(logo_header, (0, 0))
    stacked.paste(text_header, (0, logo_header.height + 8))
    stacked.resize((stacked.width * 2, stacked.height * 2)).save(
        ARTIFACTS / f"{site.name}-wordmark-headers.png"
    )
    site.shot("wordmark-text-header")

    # Club switcher: the logo-less club shows the same wordmark in its row.
    page.get_by_role("button", name="Cambiar de club").click()
    item = page.get_by_role("menuitem", name=seeded["name"]).filter(
        has=page.get_by_role("img", name=seeded["name"])
    )
    expect(item.get_by_role("img", name=seeded["name"], exact=True)).to_have_attribute("data-wordmark", "")
    site.shot("wordmark-switcher")
    page.keyboard.press("Escape")

    # /clubes card: the band holds the logo (max-h) or the wordmark, same height token.
    page.goto(site.url("/clubes"))
    logo_band = page.locator('a[href="/a/upiixia"] div.min-h-24')
    text_band = page.locator(f'a[href="/a/{TEXT_SLUG}"] div.min-h-24')
    text_card = text_band.get_by_role("img", name=seeded["name"], exact=True)
    expect(text_card).to_be_visible()
    compare(site, "card", (loaded(logo_band.locator("img")), logo_band), (text_card, text_band))
    assert logo_band.bounding_box()["height"] == text_band.bounding_box()["height"]  # noqa: S101 · same band


def test_mis_clubs_tile_wordmark_matches_the_logo(site: Site) -> None:
    """The member's "mis clubs" tile with UpiixIA's logo, then the same tile with `logo_url` removed."""
    page = site.page
    context = page.context.browser.new_context(  # type: ignore[union-attr]
        viewport=page.viewport_size, reduced_motion="reduce", locale="es-MX"
    )
    try:
        member = context.new_page()
        login = member.request.post(
            site.url("/api/auth/login"),
            headers={"X-Requested-With": "fetch"},
            data={"email": MEMBER, "password": SEED_PASSWORD},
        )
        assert login.ok, login.text()  # noqa: S101
        # The tile's brand is the only one aligned to the start (the club cards on "/" center theirs).
        tile_brand = (
            member.get_by_role("main")
            .get_by_role("img", name="UpiixIA", exact=True)
            .and_(member.locator(".self-start"))
        )
        member.goto(site.url("/"))
        logo = loaded(tile_brand)
        assert logo.evaluate("(el) => el.tagName") == "IMG"  # noqa: S101
        logo_tile = logo.locator("xpath=..")
        logo_tile_height = logo_tile.bounding_box()["height"]  # type: ignore[index]

        def without_logo(route: Route) -> None:
            body = route.fetch().json()
            body["academy"]["logo_url"] = None
            route.fulfill(json=body)

        member.route("**/api/academies/upiixia/home", without_logo)
        member.goto(site.url("/"))
        text = tile_brand
        expect(text).to_have_attribute("data-wordmark", "")
        member.evaluate("document.fonts.ready")
        text_tile = text.locator("xpath=..")
        compare(site, "tile", (logo, logo_tile), (text, text_tile))
        # Same box: the tile keeps its height whether the club has a logo or not.
        assert abs(text_tile.bounding_box()["height"] - logo_tile_height) <= 1  # type: ignore[index]  # noqa: S101
    finally:
        context.close()


def test_one_word_club_name_fits_the_greeting(site: Site) -> None:
    """A club name that is one long word wraps inside the club home greeting at 390 px (UPS-039)."""
    page = site.page
    assert len(ONE_WORD["name"]) >= 60 and " " not in ONE_WORD["name"]  # noqa: S101
    create_club_as_superadmin(page, site.base_url, ONE_WORD)
    page.set_viewport_size({"width": 390, "height": 844})
    try:
        page.goto(site.url(f"/a/{ONE_WORD['slug']}"))
        greeting = page.get_by_role("heading", level=1, name=ONE_WORD["name"])
        expect(greeting).to_be_visible()
        dismiss_toasts(site)
        card = greeting.locator("xpath=ancestor::section[1]").bounding_box()
        box = greeting.bounding_box()
        assert card and box and box["x"] + box["width"] <= card["x"] + card["width"], (box, card)  # noqa: S101
        assert greeting.evaluate("(el) => el.scrollWidth <= el.clientWidth")  # noqa: S101 · wraps, no overflow
        assert_fits_phone(site, ONE_WORD["slug"])
        site.shot("one-word-club-greeting")
    finally:
        width, height = (1280, 800) if site.name == "desktop" else (390, 844)
        page.set_viewport_size({"width": width, "height": height})
