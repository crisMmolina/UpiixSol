"""Site brand editable in /admin (UPS-041), in a real browser. Own server per viewport (module-scoped `site`),
so the brand change never reaches the other e2e files; the defaults are restored at the end anyway.

A superadmin renames the site and changes its colors in "Marca del sitio", then removes the logo: the campus
header switches to the three-color wordmark without a reload (and the visit counts one page view), signing out
shows the login with the new colors, and a fresh browser context (no session, no cache) sees them too.
A brand that reaches the login after its first paint (slow GET /api/site) updates it in place, keeping what
the visitor already typed."""

import re

from playwright.sync_api import Page, Request, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_branding import WORDMARK_PARTS, rgb

SUPERADMIN = "superadmin1@upiixsol.dev"
BRAND = {
    "name": "UpiixLuna",
    "color_primary": "#1E40AF",
    "color_secondary": "#B91C1C",
    "color_accent": "#CA8A04",
}
DEFAULTS = {
    "name": "UpiixSol",
    "color_primary": "#00BF63",
    "color_secondary": "#04944F",
    "color_accent": "#F28034",
}
COLOR_FIELDS = (("Primario", "color_primary"), ("Secundario", "color_secondary"), ("Acento", "color_accent"))
EXPECTED_PARTS = [
    ["Upii", rgb(BRAND["color_primary"])],
    ["x", rgb(BRAND["color_secondary"])],
    ["Luna", rgb(BRAND["color_accent"])],
]


def superadmin_token(site: Site) -> str:
    """Signs in through the API (the refresh cookie lands in the site's browser context)."""
    login = site.page.request.post(
        site.url("/api/auth/login"),
        headers={"X-Requested-With": "fetch"},
        data={"email": SUPERADMIN, "password": SEED_PASSWORD},
    )
    assert login.ok, login.text()  # noqa: S101
    return login.json()["access_token"]


def restore_brand(site: Site, token: str) -> None:
    """Back to the shipped brand (the logo comes back by uploading the original file)."""
    request, auth = site.page.request, {"Authorization": f"Bearer {token}"}
    restored = request.put(site.url("/api/admin/site"), headers=auth, data=DEFAULTS)
    assert restored.ok, restored.text()  # noqa: S101
    original = request.get(site.url("/brand/upiixsol/wordmark.png")).body()
    uploaded = request.post(
        site.url("/api/admin/site/logo"),
        headers=auth,
        multipart={"file": {"name": "wordmark.png", "mimeType": "image/png", "buffer": original}},
    )
    assert uploaded.ok and uploaded.json()["name"] == DEFAULTS["name"], uploaded.text()  # noqa: S101


def page_views(requests: list[Request], path: str) -> int:
    events = [
        event
        for request in requests
        if request.method == "POST" and request.url.endswith("/api/analytics/events")
        for event in request.post_data_json["events"]
    ]
    return sum(1 for e in events if e["name"] == "page.view" and e.get("path") == path)


def assert_wordmark(page: Page) -> None:
    wordmark = page.get_by_role("img", name=BRAND["name"], exact=True)
    expect(wordmark).to_be_visible()
    assert wordmark.evaluate(WORDMARK_PARTS) == EXPECTED_PARTS  # noqa: S101


def test_superadmin_renames_the_site_and_removes_its_logo(site: Site) -> None:
    token = superadmin_token(site)
    try:
        edit_brand_in_admin(site)
    finally:
        restore_brand(site, token)


def edit_brand_in_admin(site: Site) -> None:
    page = site.page
    sent: list[Request] = []
    page.on("request", lambda request: sent.append(request))
    page.goto(site.url("/admin?tab=marca"))
    expect(page.get_by_role("tab", name="Marca del sitio")).to_have_attribute("aria-selected", "true")
    save = page.get_by_role("button", name="Guardar marca")
    expect(save).to_be_disabled()  # nothing to save yet
    site.shot("site-brand-tab")

    # A bad color shows its error in the reserved lines: the save button does not move.
    top = "(el) => el.getBoundingClientRect().top + window.scrollY"
    before = save.evaluate(top)
    page.get_by_label("Primario", exact=True).fill("#12")
    save.click()
    expect(page.get_by_text("Usa el formato #RRGGBB.")).to_be_visible()
    assert abs(save.evaluate(top) - before) < 1  # noqa: S101

    page.get_by_label("Nombre del sitio").fill(BRAND["name"])
    for label, key in COLOR_FIELDS:
        page.get_by_label(label, exact=True).fill(BRAND[key])
    preview = page.get_by_test_id("preview-login")
    # Live preview, before saving.
    expect(preview.get_by_role("img", name=BRAND["name"], exact=True)).to_be_visible()
    save.click()
    expect(page.get_by_text("Marca guardada.")).to_be_visible()
    expect(page).to_have_title(f"{BRAND['name']} Campus")

    # Removing the logo: the header shows the name as the three-color wordmark, no reload.
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Quitar logo").click()
    expect(page.get_by_text("Logo quitado")).to_be_visible()
    header = page.get_by_role("banner").get_by_role("img", name=BRAND["name"], exact=True)
    expect(header).to_be_visible()
    assert header.evaluate(WORDMARK_PARTS) == EXPECTED_PARTS  # noqa: S101
    expect(page.get_by_role("button", name="Quitar logo")).to_be_disabled()
    site.shot("site-brand-saved")

    # The save and the removal re-render the routes, but the visit to /admin counts one page view.
    with page.expect_request(lambda r: r.url.endswith("/api/analytics/events")):
        page.evaluate("window.dispatchEvent(new Event('pagehide'))")  # flushes the analytics queue
    assert page_views(sent, "/admin") == 1, page_views(sent, "/admin")  # noqa: S101

    # Signing out (no reload): the login draws the new name with the new colors.
    page.get_by_role("banner").locator('button[aria-haspopup="menu"]').last.click()  # user menu
    page.get_by_role("menuitem", name="Cerrar sesión").click()
    expect(page.get_by_role("tab", name="Entrar")).to_be_visible()
    assert_wordmark(page)

    # A visitor (fresh context: no session, no HTTP cache) sees the new brand on the login page.
    visitor = page.context.browser.new_context(viewport=page.viewport_size, reduced_motion="reduce")
    try:
        login_page = visitor.new_page()
        login_page.goto(site.url("/"))
        assert_wordmark(login_page)
        expect(login_page.get_by_role("button", name="Entrar", exact=True)).to_be_visible()
        expect(login_page).to_have_title(re.compile(rf"^{BRAND['name']} Campus$"))
        Site(base_url=site.base_url, name=site.name, page=login_page).shot("site-brand-login")
    finally:
        visitor.close()


def test_a_late_brand_updates_the_login_in_place(site: Site) -> None:
    token = superadmin_token(site)
    auth = {"Authorization": f"Bearer {token}"}
    assert site.page.request.put(site.url("/api/admin/site"), headers=auth, data=BRAND).ok  # noqa: S101
    assert site.page.request.delete(site.url("/api/admin/site/logo"), headers=auth).ok  # noqa: S101
    visitor = site.page.context.browser.new_context(viewport=site.page.viewport_size, reduced_motion="reduce")
    try:
        page = visitor.new_page()
        held = []
        page.route(
            "**/api/site", lambda route: held.append(route)
        )  # GET /api/site answers only when released below
        page.goto(site.url("/login"))
        # After the 800 ms wait the login paints with the built-in brand (the UpiixSol logo).
        expect(page.get_by_role("img", name=DEFAULTS["name"], exact=True)).to_be_visible()
        email = page.get_by_label("Correo")
        email.fill("alumno.demo@upiixsol.dev")
        assert len(held) == 1  # noqa: S101
        held[0].continue_()

        assert_wordmark(page)
        expect(page).to_have_title(f"{BRAND['name']} Campus")
        expect(email).to_have_value("alumno.demo@upiixsol.dev")  # nothing remounted under the visitor
        enter = page.get_by_role("button", name="Entrar", exact=True)
        # Retried: even a 0.01 ms transition (reduced motion) reports the old color until the next frame.
        expect(enter).to_have_css("background-color", rgb(BRAND["color_primary"]))
    finally:
        visitor.close()
        restore_brand(site, token)
