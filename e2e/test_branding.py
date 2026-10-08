"""Club colors and wordmark (UPS-032), in a real browser. Own server per viewport (module-scoped `site`),
so it does not depend on test_flow.py's state.

A superadmin creates a club without a logo through the API; inside the club, the header draws its name as a
three-color wordmark and a primary button uses the club's primary color (`@theme inline` in index.css)."""

import re

from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site

SUPERADMIN = "superadmin2@upiixsol.dev"
CLUB = {
    "slug": "upiixmarte",
    "name": "UpiixMarte",
    "short_description": "",  # no description: the card must not leave a gap
    "color_primary": "#1E40AF",
    "color_secondary": "#B91C1C",
    "color_accent": "#CA8A04",
}
# Color of each wordmark piece, as the browser computes it.
WORDMARK_PARTS = """
  (root) => [...root.children].map((el) => [el.textContent, getComputedStyle(el).color])
"""


def rgb(hex_color: str) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgb({r}, {g}, {b})"


def create_club_as_superadmin(page: Page, base_url: str, club: dict[str, str] = CLUB) -> None:
    """Logs in through the API (the refresh cookie lands in the browser context) and creates the club."""
    login = page.request.post(
        f"{base_url}/api/auth/login",
        headers={"X-Requested-With": "fetch"},
        data={"email": SUPERADMIN, "password": SEED_PASSWORD},
    )
    assert login.ok, login.text()  # noqa: S101
    token = login.json()["access_token"]
    created = page.request.post(
        f"{base_url}/api/admin/academies", headers={"Authorization": f"Bearer {token}"}, data=club
    )
    assert created.status == 201, created.text()  # noqa: S101


def test_club_without_logo_uses_its_three_colors(site: Site) -> None:
    page = site.page
    create_club_as_superadmin(page, site.base_url)

    # Club header: "Upii" primary · "x" secondary · "Marte" accent; accessible name = club name.
    page.goto(site.url(f"/a/{CLUB['slug']}"))
    wordmark = page.get_by_role("banner").get_by_role("img", name=CLUB["name"], exact=True)
    expect(wordmark).to_be_visible()
    assert wordmark.evaluate(WORDMARK_PARTS) == [  # noqa: S101
        ["Upii", rgb(CLUB["color_primary"])],
        ["x", rgb(CLUB["color_secondary"])],
        ["Marte", rgb(CLUB["color_accent"])],
    ]
    expect(page).to_have_title(re.compile(rf"^{CLUB['name']} · "))
    site.shot("branding-club-home")

    # A primary button inside the club uses the club's primary, not the campus green.
    page.goto(site.url(f"/a/{CLUB['slug']}/eventos"))
    button = page.get_by_role("button", name="Nuevo evento")
    expect(button).to_be_visible()
    assert button.evaluate("(el) => getComputedStyle(el).backgroundColor") == rgb(CLUB["color_primary"])  # noqa: S101

    # Club switcher: a 44 px button; the club's fallback shows its wordmark too.
    switcher = page.get_by_role("button", name="Cambiar de club")
    box = switcher.bounding_box()
    assert box and box["width"] >= 44 and box["height"] >= 44, box  # noqa: S101
    switcher.click()
    item = page.get_by_role("menuitem", name=CLUB["name"])
    expect(item.get_by_role("img", name=CLUB["name"])).to_be_visible()
    page.keyboard.press("Escape")

    # Catalog card: the wordmark is the heading (name shown once) and the band uses the club's primary.
    page.goto(site.url("/clubes"))
    card = page.get_by_role("link", name=f"Entrar a {CLUB['name']}")
    expect(card).to_be_visible()
    expect(card.get_by_role("heading")).to_have_count(1)
    assert card.inner_text().count(CLUB["name"]) == 1  # noqa: S101 · the wordmark only, no second copy
    stripe = card.locator("div.h-1.bg-primary")
    assert stripe.evaluate("(el) => getComputedStyle(el).backgroundColor") == rgb(CLUB["color_primary"])  # noqa: S101
    site.shot("branding-clubs")


LONG_CLUBS = [
    {**CLUB, "slug": "upiixastronomia", "name": "UpiixAstronomía y Ciencias Planetarias del Norte"},
    {**CLUB, "slug": "club-robotica", "name": "Club de Robótica Competitiva", "color_primary": "#FDE047"},
]


def assert_fits_phone(site: Site, step: str) -> None:
    """No sideways scroll at 390 px and the bell (top-bar actions) fully on screen."""
    page = site.page
    assert page.evaluate("document.documentElement.scrollWidth") <= 390, step  # noqa: S101
    bell = page.get_by_role("banner").get_by_role("button", name=re.compile(r"^Notificaciones"))
    box = bell.bounding_box()
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390, (step, box)  # noqa: S101


def test_long_club_names_fit_a_phone(site: Site) -> None:
    page = site.page
    for club in LONG_CLUBS:
        create_club_as_superadmin(page, site.base_url, club)
    page.set_viewport_size({"width": 390, "height": 844})
    try:
        page.goto(site.url("/clubes"))
        expect(page.get_by_role("link", name=f"Entrar a {LONG_CLUBS[0]['name']}")).to_be_visible()
        assert_fits_phone(site, "/clubes")
        page.goto(site.url("/"))
        expect(page.get_by_role("link", name=f"Entrar a {LONG_CLUBS[0]['name']}")).to_be_visible()
        assert_fits_phone(site, "/")
        for club in LONG_CLUBS:
            page.goto(site.url(f"/a/{club['slug']}"))
            expect(page.get_by_role("banner").get_by_role("img", name=club["name"], exact=True)).to_be_visible()
            assert_fits_phone(site, club["slug"])
        site.shot("branding-long-name")
    finally:
        width, height = (1280, 800) if site.name == "desktop" else (390, 844)
        page.set_viewport_size({"width": width, "height": height})
