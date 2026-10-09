"""Site brand editable in /admin (UPS-041), in a real browser. Own server per viewport (module-scoped `site`),
so the brand change never reaches the other e2e files; the defaults are restored at the end anyway.

A superadmin renames the site and changes its colors in "Marca del sitio", then removes the logo: the campus
header switches to the three-color wordmark without a reload, and the login page in a fresh browser context
(no session, no cache) shows the new name as the wordmark and as the tab title."""

import re

from playwright.sync_api import expect

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


def test_superadmin_renames_the_site_and_removes_its_logo(site: Site) -> None:
    page = site.page
    login = page.request.post(
        site.url("/api/auth/login"),
        headers={"X-Requested-With": "fetch"},
        data={"email": SUPERADMIN, "password": SEED_PASSWORD},
    )
    assert login.ok, login.text()  # noqa: S101
    token = login.json()["access_token"]

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

    # A visitor (fresh context: no session, no HTTP cache) sees the new brand on the login page.
    visitor = page.context.browser.new_context(viewport=page.viewport_size, reduced_motion="reduce")
    try:
        login_page = visitor.new_page()
        login_page.goto(site.url("/"))
        wordmark = login_page.get_by_role("img", name=BRAND["name"], exact=True)
        expect(wordmark).to_be_visible()
        assert wordmark.evaluate(WORDMARK_PARTS) == EXPECTED_PARTS  # noqa: S101
        expect(login_page.get_by_role("button", name="Entrar", exact=True)).to_be_visible()
        expect(login_page).to_have_title(re.compile(rf"^{BRAND['name']} Campus$"))
        Site(base_url=site.base_url, name=site.name, page=login_page).shot("site-brand-login")
    finally:
        visitor.close()

    # Restore the shipped brand (the logo comes back by uploading the original file).
    auth = {"Authorization": f"Bearer {token}"}
    restored = page.request.put(site.url("/api/admin/site"), headers=auth, data=DEFAULTS)
    assert restored.ok, restored.text()  # noqa: S101
    original = page.request.get(site.url("/brand/upiixsol/wordmark.png")).body()
    uploaded = page.request.post(
        site.url("/api/admin/site/logo"),
        headers=auth,
        multipart={"file": {"name": "wordmark.png", "mimeType": "image/png", "buffer": original}},
    )
    assert uploaded.ok and uploaded.json()["name"] == DEFAULTS["name"], uploaded.text()  # noqa: S101
