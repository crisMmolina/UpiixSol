"""Drawers and modals keep Tab focus inside until they close (UPS-061, found by UPS-057 MOB-02).

A native `showModal()` makes the page inert but still lets Tab leave the document after the last control,
so focus ended up outside the open "Más" drawer. Each case tabs a full lap plus two extra presses forward
and backward, then closes with Escape and expects focus back on the control that opened the dialog.
"""

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Locator, Page, expect

from e2e.conftest import SEED_PASSWORD, _start_server
from e2e.test_flow import ADMIN_IA, MEMBER

INSIDE_OPEN_DIALOG = "() => !!document.activeElement && !!document.activeElement.closest('dialog[open]')"
STOPS = """
  () => [...document.querySelector('dialog[open]').querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select, textarea,'
    + ' [tabindex]:not([tabindex="-1"])')]
    .filter((el) => el.getClientRects().length > 0).length
"""


@pytest.fixture(scope="module")
def server() -> Iterator[str]:
    url, process, workdir = _start_server()
    try:
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)
        workdir.cleanup()


def signed_in(browser: Browser, server: str, email: str, size: tuple[int, int], path: str) -> Page:
    context = browser.new_context(viewport={"width": size[0], "height": size[1]}, reduced_motion="reduce")
    context.set_default_timeout(10_000)
    page = context.new_page()
    page.goto(f"{server}/login?next={path}")
    page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(email)
    page.get_by_label("Contraseña", exact=True).fill(SEED_PASSWORD)
    page.get_by_role("button", name="Entrar").click()
    expect(page).not_to_have_url(re.compile(r"/login"))
    return page


def assert_focus_stays_inside(page: Page, opener: Locator) -> None:
    opener.click()
    expect(page.locator("dialog[open]")).to_be_visible()
    stops = page.evaluate(STOPS)
    assert stops >= 1  # noqa: S101
    for key in ("Tab", "Shift+Tab"):
        for press in range(stops + 2):
            page.keyboard.press(key)
            assert page.evaluate(INSIDE_OPEN_DIALOG), f"{key} #{press + 1} took focus out of the dialog"  # noqa: S101
    page.keyboard.press("Escape")
    expect(page.locator("dialog[open]")).to_have_count(0)
    expect(opener).to_be_focused()


def test_more_drawer_keeps_focus_at_375(browser: Browser, server: str) -> None:
    page = signed_in(browser, server, MEMBER, (375, 812), "/a/upiixia")
    try:
        assert_focus_stays_inside(page, page.get_by_role("button", name="Más", exact=True))
    finally:
        page.context.close()


def test_player_contents_drawer_keeps_focus_at_375(browser: Browser, server: str) -> None:
    page = signed_in(browser, server, MEMBER, (375, 812), "/a/upiixia/clases/1")
    try:
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        assert_focus_stays_inside(page, page.get_by_role("button", name="Contenido"))
    finally:
        page.context.close()


@pytest.mark.parametrize("size", [(375, 812), (1280, 800)], ids=["375", "1280"])
def test_new_event_modal_keeps_focus(browser: Browser, server: str, size: tuple[int, int]) -> None:
    page = signed_in(browser, server, ADMIN_IA, size, "/a/upiixia/eventos")
    try:
        assert_focus_stays_inside(page, page.get_by_role("button", name="Nuevo evento"))
    finally:
        page.context.close()
