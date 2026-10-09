"""Admin panels (UPS-036): modal errors keep the modal's size, clubs without a logo show their wordmark,
the superadmin's own row says why it cannot be deactivated, an academy admin opening another club's panel
gets a permission page (not a broken panel with "Reintentar") and lesson links stay inside the modal."""

from playwright.sync_api import Locator, Page, expect

from e2e.conftest import Site
from e2e.test_flow import sign_in
from e2e.test_layout_stability import assert_box, stable_box

SUPERADMIN = "superadmin1@upiixsol.dev"
ADMIN_IA = "admin.ia@upiixsol.dev"
CLUB = "Upiix Robótica"


def modal_panel(page: Page, title: str) -> Locator:
    """The visible card of a modal (the <dialog> itself covers the whole viewport)."""
    return page.get_by_role("dialog", name=title).locator(":scope > div").nth(1)


def test_new_user_conflict_keeps_the_modal_size(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin?tab=usuarios")
    page = site.page
    page.get_by_role("button", name="Nuevo usuario").click()
    dialog = page.get_by_role("dialog", name="Nuevo usuario")
    panel = modal_panel(page, "Nuevo usuario")
    before = stable_box(panel)
    dialog.get_by_label("Nombre completo").fill("AUD Duplicado")
    dialog.get_by_label("Correo").fill("superadmin2@upiixsol.dev")
    dialog.get_by_label("Contraseña temporal").fill("temporal-123")
    dialog.get_by_role("button", name="Crear usuario").click()
    expect(dialog.get_by_text("Ya existe un usuario con ese correo o esa boleta.")).to_be_visible()
    assert_box(panel, before)
    site.shot("admin-user-conflict")
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()


def test_own_row_explains_why_it_cannot_be_deactivated(site: Site) -> None:
    page = site.page  # still the superadmin on /admin?tab=usuarios
    own = page.get_by_role("row").filter(has_text=SUPERADMIN)
    expect(own.get_by_text("No puedes desactivar tu propia cuenta")).to_be_visible()
    expect(own.get_by_role("button", name="Desactivar")).to_have_count(0)
    other = page.get_by_role("row").filter(has_text="superadmin2@upiixsol.dev")
    expect(other.get_by_role("button", name="Desactivar")).to_be_visible()


def test_new_club_without_logo_shows_its_wordmark(site: Site) -> None:
    page = site.page
    page.goto(site.url("/admin?tab=academias"))
    page.get_by_role("button", name="Nuevo club").click()
    dialog = page.get_by_role("dialog", name="Nuevo club")
    panel = modal_panel(page, "Nuevo club")
    before = stable_box(panel)
    dialog.get_by_label("Nombre", exact=True).fill(CLUB)
    dialog.get_by_label("Identificador (slug)").fill("upiixia")
    dialog.get_by_role("button", name="Crear club").click()
    expect(dialog.get_by_text("Ese identificador (slug) ya está en uso.")).to_be_visible()
    assert_box(panel, before)
    dialog.get_by_label("Identificador (slug)").fill("robotica")
    dialog.get_by_role("button", name="Crear club").click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_role("img", name=CLUB)).to_be_visible()
    site.shot("admin-clubs-wordmark")


def test_lesson_links_stay_inside_the_modal(site: Site) -> None:
    page = site.page
    page.goto(site.url("/panel/academia/upiixia?tab=contenido"))
    page.get_by_role("button", name="Agregar clase").first.click()
    dialog = page.get_by_role("dialog", name="Nueva clase")
    dialog.get_by_role("button", name="Agregar link").click()
    dialog.get_by_label("URL del link 1").fill("https://upiixsol.dev/" + "recurso-largo-" * 6)
    panel = modal_panel(page, "Nueva clase")
    right_edge = "(el) => el.getBoundingClientRect().right"
    right = panel.evaluate(right_edge)
    remove = dialog.get_by_role("button", name="Quitar link").evaluate(right_edge)
    assert remove <= right  # noqa: S101
    body = dialog.locator(".overflow-y-auto")
    assert body.evaluate("(el) => el.scrollWidth <= el.clientWidth")  # noqa: S101
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()


def test_admin_of_another_club_gets_a_permission_page(site: Site) -> None:
    sign_in(site, ADMIN_IA, "/panel/academia/robotica")
    page = site.page
    expect(page.get_by_role("heading", name="No administras este club")).to_be_visible()
    expect(page.get_by_role("tab")).to_have_count(0)
    expect(page.get_by_role("button", name="Reintentar")).to_have_count(0)
    site.shot("admin-other-club")
    page.get_by_role("link", name="Ir al panel de mi club").click()
    expect(page).to_have_url(site.url("/panel/academia"))
    expect(page.get_by_role("heading", name="UpiixIA")).to_be_visible()

    page.goto(site.url("/panel/academia/no-existe"))
    expect(page.get_by_role("heading", name="Este club no existe")).to_be_visible()
    expect(page.get_by_role("button", name="Reintentar")).to_have_count(0)
