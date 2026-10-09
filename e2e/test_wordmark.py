"""A club without a logo looks like the logo images (UPS-039): its name is drawn in Fredoka bold, lowercase up
to the "x", plain colors with no outline, at the same size as the logo in the club header.

Compares the seeded UpiixIA (logo image) with a copy named "UpiixIA" without a logo and the same colors:
both header brands are screenshotted (e2e/artifacts/<viewport>-wordmark-*.png, plus a side-by-side) and the
ink boxes must match (height of the letters, i dot to p tail, and width)."""

import io

from PIL import Image
from playwright.sync_api import Locator, expect

from e2e.conftest import ARTIFACTS, Site
from e2e.test_branding import CLUB, assert_fits_phone, create_club_as_superadmin, rgb

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


def header_shot(site: Site) -> Image.Image:
    """The left part of the top bar, where the brand is."""
    width = min(site.page.viewport_size["width"], 480) if site.page.viewport_size else 480
    clip = {"x": 0, "y": 0, "width": width, "height": 64}
    return Image.open(io.BytesIO(site.page.screenshot(clip=clip, animations="disabled"))).convert("RGB")


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

    page.goto(site.url("/a/upiixia"))
    logo = page.get_by_role("banner").get_by_role("img", name=seeded["name"], exact=True)
    expect(logo).to_be_visible()
    dismiss_toasts(site)
    assert logo.evaluate("(el) => el.tagName") == "IMG"  # noqa: S101
    logo_shot, logo_ink = ink_box(logo)
    logo_header = header_shot(site)

    page.goto(site.url(f"/a/{TEXT_SLUG}"))
    text = page.get_by_role("banner").get_by_role("img", name=seeded["name"], exact=True)
    expect(text).to_be_visible()
    dismiss_toasts(site)
    page.evaluate("document.fonts.ready")
    primary, secondary, accent = (rgb(c) for c in colors.values())
    pieces = text.evaluate(PIECES)
    # "upii" primary · "x" secondary · "IA" accent; plain colors (no outline), Fredoka bold.
    assert [p[0] for p in pieces] == ["upii", "x", "IA"], pieces  # noqa: S101
    assert all(p[2] == "none" and p[3] == "700" and p[4] == "Fredoka" for p in pieces), pieces  # noqa: S101
    assert {p[0]: p[1] for p in pieces} == {"upii": primary, "x": secondary, "IA": accent}, pieces  # noqa: S101
    text_shot, text_ink = ink_box(text)
    text_header = header_shot(site)

    # Same place and size as the logo: letters (i dot to p tail) within 2 px, width within 4 %.
    for edge in (0, 1, 3):
        assert abs(logo_ink[edge] - text_ink[edge]) <= 2, (logo_ink, text_ink)  # noqa: S101
    logo_w, text_w = logo_ink[2] - logo_ink[0], text_ink[2] - text_ink[0]
    assert abs(logo_w - text_w) <= 0.04 * logo_w, (logo_ink, text_ink)  # noqa: S101

    # Evidence: the two brands side by side, and the two headers stacked (logo above, text below), 2x.
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    gap = 24
    side = Image.new(
        "RGB", (logo_shot.width + gap + text_shot.width, max(logo_shot.height, text_shot.height)), "white"
    )
    side.paste(logo_shot, (0, 0))
    side.paste(text_shot, (logo_shot.width + gap, 0))
    side.save(ARTIFACTS / f"{site.name}-wordmark-side-by-side.png")
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
