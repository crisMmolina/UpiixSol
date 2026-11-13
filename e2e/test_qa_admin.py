"""QA admin panels in a real browser (UPS-055): docs/PRUEBAS-CAMPUS.md §ADM and §SUP, per viewport.

The academy admin reorders content, cancels a delete, sees the contrast warning, removes and re-enrolls a
member, edits branding (colors, logo, mascot) and welcome text, creates an event and opens resources; the
superadmin creates a club, resets a password, deactivates and reactivates an account and an academy, edits
the site brand (name, colors, logo, mascot) and pages through more than 50 users. Tests run in order on one
site per viewport and sign in once per role (login is rate-limited).

Not covered in e2e, on purpose:
- ADM-09 (academy analytics): no screen or GET endpoint shows the numbers; POST /api/analytics/events only
  ingests them. The counts are covered by app/tests/test_analytics.py.
- SUP-02, server side: "no temporary password in logs". conftest.py sends the server's stdout and stderr to
  DEVNULL (outside this UPS-055 Paths), so the e2e run cannot read the server log.
  test_sup02_temporary_password_stays_out_of_the_browser checks the browser side (console, page errors)
  instead; the server-log check needs a backend test or a conftest change (follow-up task).
"""

import io
import re

from PIL import Image
from playwright.sync_api import expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import ADMIN_IA, MEMBER, SUPERADMIN, sign_in

ROUTE = "Fundamentos de IA con Python"
BRAND_NAME = "UpiixQA"
ACADEMY_PRIMARY = "#0D47A1"  # white text on it reaches AA
# Custom property of the themed wrapper on /a/:slug (AcademyTheme sets it inline).
PRIMARY_VAR = """() => {
  const el = document.querySelector('[style*="--academy-primary"]');
  return el ? getComputedStyle(el).getPropertyValue('--academy-primary').trim().toLowerCase() : null;
}"""
LOGO_VAR = """() => {
  const el = document.querySelector('[style*="--academy-logo"]');
  return el ? getComputedStyle(el).getPropertyValue('--academy-logo').trim() : null;
}"""
BROKEN_IMAGES = "[...document.images].filter((img) => img.complete && img.naturalWidth === 0).length"
PAGED_EMAILS = [f"qa.pag.{number:02d}@upiixsol.dev" for number in range(55)]


def test_adm02_reorder_module_persists(site: Site) -> None:
    sign_in(site, ADMIN_IA, "/panel/academia")
    page = site.page
    first = page.locator("li", has_text="Módulo 1 · Python para IA").first
    first.get_by_role("button", name="Bajar módulo").first.click()
    expect(page.get_by_text("Módulo 1 · Redes neuronales").first).to_be_visible()
    page.reload()
    expect(page.get_by_text("Módulo 1 · Redes neuronales").first).to_be_visible()
    expect(page.get_by_text("Módulo 2 · Python para IA").first).to_be_visible()
    site.shot("qa-admin-reorder")


def test_adm01_cancelled_delete_keeps_the_route(site: Site) -> None:
    page = site.page
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Eliminar ruta").first.click()
    page.reload()
    expect(page.get_by_role("heading", name=ROUTE).first).to_be_visible()


def test_adm04_low_contrast_color_warns(site: Site) -> None:
    page = site.page
    page.goto(site.url("/panel/academia?tab=identidad"))
    field = page.get_by_label("Primario (botones, barras)", exact=True)
    field.fill("#808080")  # mid-gray: neither black nor white text reaches 4.5:1
    field.blur()
    expect(page.get_by_text("no alcanza contraste AA").first).to_be_visible()
    site.shot("qa-admin-contrast")


def test_adm05_remove_and_reenroll_member(site: Site) -> None:
    page = site.page
    page.goto(site.url("/panel/academia?tab=inscritos"))
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Dar de baja a Alumno Demo").click()
    expect(page.get_by_role("button", name="Dar de baja a Alumno Demo")).to_have_count(0)
    page.get_by_label("Inscribir por número de boleta").fill("2026000001")
    page.get_by_role("button", name="Inscribir", exact=True).click()
    expect(page.get_by_text("quedó inscrito").first).to_be_visible()
    expect(page.get_by_role("button", name="Dar de baja a Alumno Demo")).to_be_visible()
    site.shot("qa-admin-enrollees")


def test_adm07_resources_tab_renders(site: Site) -> None:
    page = site.page
    page.goto(site.url("/panel/academia?tab=recursos"))
    expect(page.get_by_role("tab", name="Recursos")).to_have_attribute("aria-selected", "true")
    site.shot("qa-admin-resources")


def test_adm06_welcome_text_shows_on_academy_home(site: Site) -> None:
    page = site.page
    text = f"Bienvenida del club QA {site.name}"
    page.goto(site.url("/panel/academia?tab=identidad"))
    page.get_by_label("Primario (botones, barras)", exact=True).fill("#1B5E20")  # undo the ADM-04 gray
    page.get_by_label("Texto de bienvenida (markdown)").fill(text)
    page.get_by_role("button", name="Guardar identidad").click()
    expect(page.get_by_text("Identidad guardada").first).to_be_visible()
    page.goto(site.url("/a/upiixia"))
    expect(page.get_by_text(text).first).to_be_visible()
    site.shot("qa-admin-welcome")


def test_adm08_academy_event_shows_on_academy_events(site: Site) -> None:
    page = site.page
    title = f"Taller QA del club {site.name}"
    page.goto(site.url("/calendario?vista=lista"))
    page.get_by_role("button", name="Nuevo evento").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Título").fill(title)
    dialog.get_by_label("Lugar").fill("Sala QA")
    dialog.get_by_role("button", name="Publicar evento").click()
    expect(dialog).to_be_hidden()
    page.goto(site.url("/a/upiixia/eventos"))
    page.get_by_role("button", name="Lista", exact=True).click()  # month cells truncate titles on mobile
    expect(page.get_by_text(title).first).to_be_visible()
    site.shot("qa-admin-academy-event")


def test_adm03_branding_shows_live_on_the_academy(site: Site) -> None:
    page = site.page
    page.goto(site.url("/panel/academia?tab=identidad"))
    page.get_by_label("Primario (botones, barras)", exact=True).fill(ACADEMY_PRIMARY)
    page.locator("label", has_text="Logo").locator('input[type="file"]').set_input_files(
        files=[{"name": "logo.png", "mimeType": "image/png", "buffer": _png()}]
    )
    expect(page.get_by_text("Logo actualizado.")).to_be_visible()
    page.locator("label", has_text="Mascota").locator('input[type="file"]').set_input_files(
        files=[{"name": "mascota.png", "mimeType": "image/png", "buffer": _png()}]
    )
    expect(page.get_by_text("Mascota actualizada.")).to_be_visible()
    page.get_by_role("button", name="Guardar identidad").click()
    expect(page.get_by_text("Identidad guardada").first).to_be_visible()

    page.goto(site.url("/a/upiixia"))
    page.wait_for_function(f"({PRIMARY_VAR})() === '{ACADEMY_PRIMARY.lower()}'")
    expect(page.get_by_role("img", name="Mascota de UpiixIA")).to_be_visible()
    logo = page.evaluate(LOGO_VAR)
    assert logo != "none"  # noqa: S101
    site.shot("qa-admin-branding-live")


def test_adm02_member_sees_the_new_module_order(site: Site) -> None:
    # Runs before SUP-02, which resets the member's password.
    sign_in(site, MEMBER, "/a/upiixia/rutas")
    page = site.page
    page.get_by_role("link", name=ROUTE).first.click()
    if site.name == "mobile":  # the module list sits behind a drawer
        page.get_by_role("button", name="Contenido").click()
    expect(page.locator("summary:visible").first).to_contain_text("Redes neuronales")
    site.shot("qa-member-module-order")


def test_sup02_reset_password_and_toggle_account(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin?tab=usuarios")
    page = site.page
    page.get_by_label("Buscar").fill("alumno.demo")
    page.get_by_role("button", name="Filtrar").click()
    row = page.locator("tr", has_text="alumno.demo@upiixsol.dev")
    expect(row).to_have_count(1)

    page.once("dialog", lambda dialog: dialog.accept())
    row.get_by_role("button", name="Restablecer").click()
    expect(page.get_by_role("dialog", name="Contraseña temporal")).to_be_visible()
    site.shot("qa-admin-reset")
    page.get_by_role("button", name="Listo").click()

    page.once("dialog", lambda dialog: dialog.accept())
    row.get_by_role("button", name="Desactivar").click()
    expect(row.get_by_text("Inactivo")).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept())
    row.get_by_role("button", name="Activar").click()
    expect(row.get_by_text("Activo", exact=True)).to_be_visible()


def test_sup03_deactivate_and_reactivate_academy(site: Site) -> None:
    page = site.page
    page.goto(site.url("/admin?tab=academias"))
    card = page.locator("p", has_text="/a/upiixia").locator("xpath=..")
    page.once("dialog", lambda dialog: dialog.accept())
    card.get_by_role("button", name="Desactivar").click()
    expect(card.get_by_text("Inactivo")).to_be_visible()
    site.shot("qa-admin-academy-off")
    page.once("dialog", lambda dialog: dialog.accept())
    card.get_by_role("button", name="Activar", exact=True).click()
    expect(card.get_by_text("Activo", exact=True)).to_be_visible()


def test_sup05_home_text_shows_on_home(site: Site) -> None:
    # The home page renders hero_text only; hero_title is saved but never shown (reported in the PR).
    page = site.page
    text = f"Bienvenida QA {site.name}"
    page.goto(site.url("/admin?tab=inicio"))
    page.get_by_label("Texto de bienvenida").fill(text)
    page.get_by_role("button", name="Guardar").click()
    expect(page.get_by_text("Página principal actualizada.")).to_be_visible()
    page.goto(site.url("/"))
    expect(page.get_by_text(text).first).to_be_visible()
    site.shot("qa-admin-home")


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (240, 64), "#1B5E20").save(buffer, format="PNG")
    return buffer.getvalue()


def test_sup04_remove_site_logo_falls_back_to_wordmark(site: Site) -> None:
    page = site.page
    page.goto(site.url("/admin?tab=marca"))
    card = page.get_by_label("Logo y mascota")
    card.get_by_label("Subir logo").set_input_files(
        files=[{"name": "logo.png", "mimeType": "image/png", "buffer": _png()}]
    )
    expect(page.get_by_text("Logo actualizado en todo el campus.")).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept())
    card.get_by_role("button", name="Quitar logo").click()
    expect(page.get_by_text("Logo quitado").first).to_be_visible()
    expect(card.get_by_role("button", name="Quitar logo")).to_be_disabled()
    broken = page.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0).length")
    assert broken == 0  # noqa: S101
    site.shot("qa-admin-logo-removed")


def test_sup02_temporary_password_stays_out_of_the_browser(site: Site) -> None:
    # The password is shown once in the modal; nothing the browser logs may carry it.
    sign_in(site, SUPERADMIN, "/admin?tab=usuarios")
    page = site.page
    seen: list[str] = []
    page.on("console", lambda message: seen.append(message.text))
    page.on("pageerror", lambda error: seen.append(str(error)))
    page.get_by_label("Buscar").fill("superadmin2")
    page.get_by_role("button", name="Filtrar").click()
    row = page.locator("tr", has_text="superadmin2@upiixsol.dev")
    expect(row).to_have_count(1)
    page.once("dialog", lambda dialog: dialog.accept())
    row.get_by_role("button", name="Restablecer").click()
    dialog = page.get_by_role("dialog", name="Contraseña temporal")
    code = dialog.locator("code")
    expect(code).to_be_visible()
    password = code.inner_text()
    assert len(password) >= 8  # noqa: S101
    page.get_by_role("button", name="Listo").click()
    expect(dialog).to_be_hidden()
    assert not any(password in line for line in seen)  # noqa: S101


def test_sup05_removing_the_site_mascot_falls_back_without_a_broken_image(site: Site) -> None:
    page = site.page
    page.goto(site.url("/admin?tab=marca"))
    card = page.get_by_label("Logo y mascota")
    card.get_by_label("Subir mascota").set_input_files(
        files=[{"name": "mascota.png", "mimeType": "image/png", "buffer": _png()}]
    )
    expect(page.get_by_text("Mascota actualizada en todo el campus.")).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept())
    card.get_by_role("button", name="Quitar mascota").click()
    expect(page.get_by_text("Mascota quitada: ya no se muestra en el campus.")).to_be_visible()
    expect(card.get_by_role("button", name="Quitar mascota")).to_be_disabled()
    expect(card.get_by_text("Sin mascota")).to_be_visible()
    expect(page.get_by_role("img", name="Mascota actual")).to_have_count(0)
    assert page.evaluate(BROKEN_IMAGES) == 0  # noqa: S101
    page.goto(site.url("/"))
    assert page.evaluate(BROKEN_IMAGES) == 0  # noqa: S101
    site.shot("qa-admin-mascot-removed")


def test_sup04_site_brand_edit_shows_on_home_header_and_login_without_redeploy(site: Site) -> None:
    page = site.page
    page.goto(site.url("/admin?tab=marca"))
    page.get_by_label("Nombre del sitio").fill(BRAND_NAME)
    page.get_by_label("Primario", exact=True).fill("#1E40AF")
    page.get_by_role("button", name="Guardar marca").click()
    expect(page.get_by_text("Marca guardada.")).to_be_visible()

    page.goto(site.url("/"))
    expect(page).to_have_title(f"{BRAND_NAME} Campus")
    expect(page.get_by_role("banner").get_by_role("img", name=BRAND_NAME, exact=True)).to_be_visible()
    site.shot("qa-admin-brand-home")

    # A visitor with no session (fresh context) sees the same brand on the login page.
    visitor = page.context.browser.new_context(viewport=page.viewport_size, reduced_motion="reduce")
    try:
        login = visitor.new_page()
        login.goto(site.url("/"))
        expect(login).to_have_title(re.compile(rf"^{BRAND_NAME} Campus$"))
        expect(login.get_by_role("img", name=BRAND_NAME, exact=True)).to_be_visible()
    finally:
        visitor.close()


def test_sup01_superadmin_creates_a_club_with_theme_and_channel(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin?tab=academias")
    page = site.page
    name = f"Club QA {site.name.title()}"
    slug = f"qa-{site.name}"
    page.get_by_role("button", name="Nuevo club").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Nombre", exact=True).fill(name)
    dialog.get_by_label("Identificador (slug)").fill(slug)
    dialog.get_by_label("Primario", exact=True).fill("#7C3AED")  # white text on it reaches AA
    dialog.get_by_role("button", name="Crear club").click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_text(name).first).to_be_visible()

    page.goto(site.url(f"/a/{slug}"))
    page.wait_for_function(f"({PRIMARY_VAR})() === '#7c3aed'")
    expect(page.get_by_text(name).first).to_be_visible()

    page.goto(site.url("/comunidad"))  # the club's own channel is created with the club (IDEA §6)
    channels = page.get_by_role("complementary", name="Canales")
    expect(channels.get_by_role("button", name=slug, exact=True)).to_be_visible()
    site.shot("qa-admin-club-created")


def test_sup06_user_list_pages_over_fifty_without_duplicates_or_gaps(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin?tab=usuarios")
    page = site.page
    login = page.request.post(
        site.url("/api/auth/login"),
        headers={"X-Requested-With": "fetch"},
        data={"email": SUPERADMIN, "password": SEED_PASSWORD},
    )
    assert login.ok, login.text()  # noqa: S101
    headers = {"Authorization": f"Bearer {login.json()['access_token']}", "X-Requested-With": "fetch"}
    for email in PAGED_EMAILS:  # 55 members: more than one page of 50
        created = page.request.post(
            site.url("/api/admin/users"),
            headers=headers,
            data={
                "role": "member",
                "email": email,
                "full_name": "Alumno Paginado",
                "password": "paginado-qa-123",
            },
        )
        assert created.status == 201, created.text()  # noqa: S101

    page.get_by_label("Buscar").fill("qa.pag.")
    page.get_by_role("button", name="Filtrar").click()
    rows = page.locator("tbody tr")
    expect(rows).to_have_count(50)
    page.get_by_role("button", name="Ver más").click()
    expect(rows).to_have_count(55)
    expect(page.get_by_role("button", name="Ver más")).to_have_count(0)
    emails = [re.search(r"qa\.pag\.\d+@upiixsol\.dev", text).group(0) for text in rows.all_inner_texts()]
    assert sorted(emails) == PAGED_EMAILS  # noqa: S101 (no duplicates, no gaps)
    site.shot("qa-admin-users-paged")
