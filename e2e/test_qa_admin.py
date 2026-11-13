"""QA admin panels in a real browser (UPS-055): docs/PRUEBAS-CAMPUS.md §ADM and §SUP, per viewport.

The academy admin reorders content, cancels a delete, sees the contrast warning, removes and re-enrolls a
member and opens resources; the superadmin resets a password, deactivates and reactivates an account and an
academy, and edits the home welcome text. Tests run in order on one site per viewport and sign in once per
role (login is rate-limited).
"""

import io

from PIL import Image
from playwright.sync_api import expect

from e2e.conftest import Site
from e2e.test_flow import ADMIN_IA, MEMBER, SUPERADMIN, sign_in

ROUTE = "Fundamentos de IA con Python"


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
    assert broken == 0
    site.shot("qa-admin-logo-removed")
