"""UPS-093: the superadmin makes the demo member a club admin, who then reaches the club panel, and demotes
them again. Every step through the real UI (confirmation dialog names the person and the club), keyboard
operable, in both viewports."""

from playwright.sync_api import Locator, Page, expect

from e2e.conftest import Site
from e2e.test_admin_panels import modal_panel
from e2e.test_flow import sign_in
from e2e.test_layout_stability import stable_box

SUPERADMIN = "superadmin1@upiixsol.dev"
MEMBER = "alumno.demo@upiixsol.dev"
NAME = "Alumno Demo"
CLUB = "UpiixIA"


def member_row(page: Page) -> Locator:
    page.get_by_label("Buscar").fill(MEMBER)
    page.get_by_role("button", name="Filtrar").click()
    row = page.get_by_role("row").filter(has_text=MEMBER)
    expect(row).to_have_count(1)
    return row


def club_panel_tab(site: Site) -> Locator:
    site.page.goto(site.url("/panel/academia"))
    site.page.wait_for_load_state("networkidle")
    return site.page.get_by_role("tab", name="Contenido")


def test_member_starts_without_the_club_panel(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    expect(club_panel_tab(site)).to_have_count(0)


def test_superadmin_makes_the_member_a_club_admin(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin?tab=usuarios")
    page = site.page
    row = member_row(page)
    expect(row.get_by_text("Miembro", exact=True)).to_be_visible()
    site.shot("roles-before")
    row.get_by_role("button", name="Hacer admin de un club").click()
    dialog = page.get_by_role("dialog", name="Hacer admin de un club")
    expect(dialog.get_by_label("Club")).to_be_visible()
    expect(dialog.get_by_text(f"¿Hacer admin de {CLUB} a {NAME}?")).to_be_visible()
    stable_box(modal_panel(page, "Hacer admin de un club"))  # let the dialog finish growing
    site.shot("roles-promote-dialog")
    dialog.get_by_role("button", name="Hacer admin", exact=True).click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_text(f"{NAME} ahora es admin de {CLUB}.")).to_be_visible()
    expect(row.get_by_text("Admin de club", exact=True)).to_be_visible()
    expect(row.get_by_role("button", name="Quitar admin")).to_be_visible()
    site.shot("roles-after-promote")


def test_the_new_admin_reaches_the_club_panel(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    expect(club_panel_tab(site)).to_be_visible()
    site.shot("roles-club-panel")


def test_superadmin_removes_admin_with_a_confirmation(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin?tab=usuarios")
    page = site.page
    row = member_row(page)
    row.get_by_role("button", name="Quitar admin").click()
    dialog = page.get_by_role("dialog", name="Quitar admin")
    expect(dialog.get_by_text(f"¿Quitar a {NAME} como admin de {CLUB}?")).to_be_visible()
    stable_box(modal_panel(page, "Quitar admin"))
    site.shot("roles-demote-dialog")
    # Cancelling changes nothing.
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()
    expect(row.get_by_text("Admin de club", exact=True)).to_be_visible()
    # Keyboard only: focus the action, open with Enter, confirm with Enter.
    row.get_by_role("button", name="Quitar admin").focus()
    page.keyboard.press("Enter")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="Quitar admin", exact=True).focus()
    page.keyboard.press("Enter")
    expect(dialog).to_be_hidden()
    expect(page.get_by_text(f"{NAME} ya no es admin de {CLUB}.")).to_be_visible()
    expect(row.get_by_text("Miembro", exact=True)).to_be_visible()
    expect(row.get_by_role("button", name="Hacer admin de un club")).to_be_visible()
    site.shot("roles-after-demote")


def test_the_demoted_member_loses_the_club_panel(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    expect(club_panel_tab(site)).to_have_count(0)


def test_superadmin_rows_have_no_role_action(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin?tab=usuarios")
    own = site.page.get_by_role("row").filter(has_text=SUPERADMIN)
    expect(own.get_by_text("Superadmin", exact=True)).to_be_visible()
    expect(own.get_by_role("button", name="Hacer admin de un club")).to_have_count(0)
    expect(own.get_by_role("button", name="Quitar admin")).to_have_count(0)
