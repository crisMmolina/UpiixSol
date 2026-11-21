"""The composer's pickers ("Enviado por", "Club", "Rol") use the same menu style as "Agregar destinatarios"
(UPS-109): a button that opens a rounded card with options, never a native <select>. Same server setup as
test_mail_recipients.py (console backend)."""

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import ARTIFACTS, SEED_PASSWORD, Site
from e2e.test_mail_recipients import add_source, open_step


@pytest.fixture(scope="module")
def mail_env() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SEED_DEFAULT_PASSWORD", SEED_PASSWORD)
        patch.setenv("MAIL_ENABLED", "true")
        patch.setenv("MAIL_BACKEND", "console")
        yield


@pytest.fixture(scope="module")
def site(mail_env: None, site: Site) -> Site:  # noqa: ARG001 - overrides conftest's `site` with mail enabled
    return site


def trigger(page: Page, label: str):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("button", name=label, exact=True)


def listbox(page: Page, label: str):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("listbox", name=label, exact=True)


def test_sender_picker_uses_the_menu_style(site: Site) -> None:
    page = open_step(site)
    expect(page.locator("select")).to_have_count(0)
    sender = trigger(page, "Enviado por")
    expect(sender).to_have_attribute("aria-haspopup", "listbox")
    expect(sender).to_have_attribute("aria-expanded", "false")
    expect(sender).to_contain_text("La mesa directiva de UpiixSol")
    site.shot("select-sender-closed")
    sender.click()
    menu = listbox(page, "Enviado por")
    expect(menu).to_be_visible()
    expect(sender).to_have_attribute("aria-expanded", "true")
    for cls in ("rounded-2xl", "border-line", "bg-surface", "shadow-lift"):  # the "Agregar destinatarios" card
        expect(menu).to_have_class(re.compile(rf"\b{cls}\b"))
    expect(menu.get_by_role("option", name="UpiixIA")).to_be_visible()
    site.shot("select-sender-open")
    page.screenshot(path=ARTIFACTS / f"{site.name}-select-sender-viewport.png")  # what the person sees, bottom bar included
    menu.get_by_role("option", name="UpiixIA").click()
    expect(menu).to_have_count(0)
    expect(sender).to_contain_text("UpiixIA")
    expect(sender).to_be_focused()


def test_club_and_role_pickers_use_the_menu_style(site: Site) -> None:
    page = open_step(site)
    add_source(page, "Un club")
    expect(page.locator("select")).to_have_count(0)
    club = trigger(page, "Club")
    expect(club).to_contain_text("Elige un club")
    expect(page.get_by_role("button", name="Agregar club")).to_be_disabled()
    club.click()
    site.shot("select-club-open")
    listbox(page, "Club").get_by_role("option", name="UpiixIA").click()
    expect(club).to_contain_text("UpiixIA")
    page.get_by_role("button", name="Agregar club").click()
    expect(page.get_by_role("list", name="Fuentes de destinatarios").get_by_role("listitem").filter(has_text="UpiixIA")).to_have_count(1)
    add_source(page, "Un rol")
    role = trigger(page, "Rol")
    expect(role).to_contain_text("Miembro")
    role.click()
    site.shot("select-role-open")
    listbox(page, "Rol").get_by_role("option", name="Admin de club").click()
    expect(role).to_contain_text("Admin de club")
    page.get_by_role("button", name="Agregar rol").click()
    expect(page.get_by_role("button", name="Quitar fuente Rol: Admin de club")).to_be_visible()


def test_menu_select_keyboard_arrows_enter_escape(site: Site) -> None:
    page = open_step(site)
    sender = trigger(page, "Enviado por")
    menu = listbox(page, "Enviado por")
    options = menu.get_by_role("option")
    sender.focus()
    page.keyboard.press("ArrowDown")  # opens, on the current choice
    expect(menu).to_be_visible()
    expect(options.first).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(options.nth(1)).to_be_focused()
    page.keyboard.press("ArrowUp")
    page.keyboard.press("ArrowUp")  # wraps to the last one
    expect(options.last).to_be_focused()
    page.keyboard.press("Home")
    expect(options.first).to_be_focused()
    page.keyboard.press("End")
    expect(options.last).to_be_focused()
    page.keyboard.press("Escape")
    expect(menu).to_have_count(0)
    expect(sender).to_be_focused()
    page.keyboard.press("Enter")  # opens again
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")  # picks the second option
    expect(menu).to_have_count(0)
    expect(sender).not_to_contain_text("La mesa directiva de UpiixSol")
    sender.click()
    expect(menu).to_be_visible()
    page.get_by_role("heading", name="¿A quién se lo mandas?").click()  # outside click
    expect(menu).to_have_count(0)


def test_menu_select_shows_the_current_choice_with_a_check(site: Site) -> None:
    page = open_step(site)
    sender = trigger(page, "Enviado por")
    sender.click()
    options = listbox(page, "Enviado por").get_by_role("option")
    expect(options.first).to_have_attribute("aria-selected", "true")
    expect(options.first.locator("svg")).to_have_count(1)  # the check
    expect(options.nth(1)).to_have_attribute("aria-selected", "false")
    expect(options.nth(1).locator("svg")).to_have_count(0)
    options.nth(1).click()
    sender.click()
    expect(options.first).to_have_attribute("aria-selected", "false")
    expect(options.nth(1)).to_have_attribute("aria-selected", "true")
    expect(options.nth(1).locator("svg")).to_have_count(1)


def test_menu_select_at_390_wide(site: Site) -> None:
    page = open_step(site)
    add_source(page, "Un club")
    for label in ("Club", "Enviado por"):
        trigger(page, label).click()
        box = listbox(page, label).bounding_box()
        assert box is not None
        width = page.evaluate("window.innerWidth")
        assert box["x"] >= 0 and box["x"] + box["width"] <= width, (label, box, width)
        nav = page.get_by_role("navigation", name="Principal móvil")
        if nav.is_visible():  # the phone's bottom bar never covers the open list
            nav_box = nav.bounding_box()
            assert nav_box is not None and box["y"] + box["height"] <= nav_box["y"] + 1, (label, box, nav_box)
        for option in listbox(page, label).get_by_role("option").all():
            assert (option.bounding_box() or {"height": 0})["height"] >= 44  # touch target
        site.shot(f"select-{label.split()[0].lower()}-fits")
        page.keyboard.press("Escape")
