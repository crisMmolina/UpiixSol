"""Step 3 recipients (UPS-107, spec 006 §Combined recipients): sources as chips, one list with a checkbox per person,
the summary, the people who cannot receive listed apart. Same server setup as test_mail.py (console backend)."""

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in

SUPERADMIN = "superadmin1@upiixsol.dev"
CLUB_ADMIN = "admin.ia@upiixsol.dev"
OUTSIDE = "invitado@example.com"
BLOCKED = "persona@bloqueado.example.com"


@pytest.fixture(scope="module")
def mail_env() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SEED_DEFAULT_PASSWORD", SEED_PASSWORD)
        patch.setenv("MAIL_ENABLED", "true")
        patch.setenv("MAIL_BACKEND", "console")
        patch.setenv("MAIL_BLOCKED_DOMAINS", "bloqueado.example.com")
        yield


@pytest.fixture(scope="module")
def site(mail_env: None, site: Site) -> Site:  # noqa: ARG001 - overrides conftest's `site` with mail enabled
    return site


def open_step(site: Site, email: str = SUPERADMIN, club: bool = False) -> Page:
    sign_in(site, email, "/")
    page = site.page
    page.goto(site.url(f"/{'panel/academia' if club else 'admin'}?tab=correos&paso=envio"))
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    return page


def add_source(page: Page, name: str) -> None:
    page.get_by_role("button", name="Agregar destinatarios").click()
    page.get_by_role("menu", name="Agregar destinatarios").get_by_role("menuitem", name=name, exact=True).click()


def add_club(page: Page) -> None:
    add_source(page, "Un club")
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    page.get_by_role("button", name="Agregar club").click()


def paste(page: Page, text: str) -> None:
    add_source(page, "Correos de fuera")
    page.get_by_label("Pegar varios correos").fill(text)
    page.get_by_role("button", name="Agregar todos").click()


def chips(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("list", name="Fuentes de destinatarios").get_by_role("listitem")


def people(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("list", name="Destinatarios", exact=True).get_by_role("listitem")


def summary(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("status").filter(has_text="recibirán")


def test_add_sources_as_chips_with_counts(site: Site) -> None:
    page = open_step(site)
    add_club(page)
    expect(chips(page).filter(has_text="UpiixIA")).to_have_text(re.compile(r"UpiixIA · \d+"))
    add_source(page, "Un rol")
    page.get_by_label("Rol", exact=True).select_option(label="Miembro")
    page.get_by_role("button", name="Agregar rol").click()
    expect(chips(page)).to_have_count(2)
    expect(chips(page).filter(has_text="Miembro")).to_have_text(re.compile(r"Miembro · \d+"))
    page.get_by_role("button", name="Quitar fuente Rol: Miembro").click()
    expect(chips(page)).to_have_count(1)
    site.shot("recipients-chips")


def test_list_checks_people_of_added_sources(site: Site) -> None:
    page = open_step(site)
    add_source(page, "Todo UpiixSol")
    expect(people(page).first).to_be_visible()
    row = people(page).filter(has_text="Alumno Demo")
    expect(row.get_by_role("checkbox")).to_be_checked()
    expect(row).to_contain_text("alumno.demo@upiixsol.dev")
    expect(row).to_contain_text("Todo UpiixSol")
    expect(summary(page)).to_contain_text(re.compile(r"\d+ recibirán · 0 quitados por ti"))
    site.shot("recipients-list")


def test_uncheck_excludes_and_counts_update(site: Site) -> None:
    page = open_step(site)
    add_source(page, "Todo UpiixSol")
    expect(summary(page)).to_contain_text("0 quitados por ti")
    people(page).filter(has_text="Alumno Demo").get_by_role("checkbox").uncheck()
    expect(summary(page)).to_contain_text("1 quitado por ti")
    expect(people(page).filter(has_text="Alumno Demo").get_by_role("checkbox")).not_to_be_checked()
    page.get_by_role("navigation", name="Pasos del correo").get_by_role("button", name=re.compile("Contenido")).click()
    page.get_by_label("Asunto").fill("Aviso con exclusiones")
    page.get_by_label("Texto del párrafo").first.fill("Hola a todos.")
    page.get_by_role("navigation", name="Pasos del correo").get_by_role("button", name=re.compile("Destinatarios")).click()
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_text("1 quitado por ti")).to_be_visible()
    dialog.get_by_role("button", name="Cancelar").click()
    people(page).filter(has_text="Alumno Demo").get_by_role("checkbox").check()
    expect(summary(page)).to_contain_text("0 quitados por ti")


def test_search_and_load_more_in_the_list(site: Site) -> None:
    page = open_step(site)
    paste(page, "\n".join(f"masivo{i}@example.com" for i in range(60)))
    expect(people(page)).to_have_count(50)
    page.get_by_role("button", name="Cargar más").click()
    expect(people(page)).to_have_count(60)
    page.get_by_label("Buscar en la lista").fill("masivo5@")
    expect(people(page)).to_have_count(1)
    expect(people(page).first).to_contain_text("masivo5@example.com")


def test_cannot_receive_listed_apart_with_reason(site: Site) -> None:
    page = open_step(site)
    paste(page, f"{OUTSIDE}\n{BLOCKED}")
    apart = page.get_by_role("list", name="No se pueden enviar")
    expect(apart.get_by_role("listitem").filter(has_text=BLOCKED)).to_contain_text("Dominio bloqueado")
    expect(apart.get_by_role("checkbox")).to_have_count(0)
    expect(people(page).filter(has_text=BLOCKED)).to_have_count(0)
    expect(summary(page)).to_contain_text("1 no se puede enviar")


def test_outside_addresses_in_the_list_removable(site: Site) -> None:
    page = open_step(site)
    paste(page, OUTSIDE)
    expect(people(page).filter(has_text=OUTSIDE)).to_contain_text("De fuera")
    page.get_by_role("button", name=f"Quitar {OUTSIDE}").click()
    expect(people(page).filter(has_text=OUTSIDE)).to_have_count(0)


def test_club_admin_sees_only_own_club_sources(site: Site) -> None:
    page = open_step(site, CLUB_ADMIN, club=True)
    page.get_by_role("button", name="Agregar destinatarios").click()
    menu = page.get_by_role("menu", name="Agregar destinatarios")
    for name in ("Mi club", "Personas", "Correos de fuera"):
        expect(menu.get_by_role("menuitem", name=name, exact=True)).to_be_visible()
    for name in ("Todo UpiixSol", "Un club", "Un rol"):
        expect(menu.get_by_role("menuitem", name=name, exact=True)).to_have_count(0)
    menu.get_by_role("menuitem", name="Mi club", exact=True).click()
    expect(chips(page).filter(has_text="Mi club")).to_have_count(1)
    expect(people(page).first).to_be_visible()
    expect(people(page).first).to_contain_text("@")  # addresses of people in scope are shown


def test_recipients_step_at_390_wide(site: Site) -> None:
    page = open_step(site)
    page.set_viewport_size({"width": 390, "height": 844})
    add_club(page)
    paste(page, OUTSIDE)
    expect(people(page).first).to_be_visible()
    expect(chips(page)).to_have_count(2)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    site.shot("recipients-390")
