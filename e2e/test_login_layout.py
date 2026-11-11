"""Login layout (UPS-042): from 1024 px the login block (brand column + card) is centered in the viewport when
it fits, starts at the top and scrolls when it does not, and the card never moves when its content grows."""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Page, expect

from e2e.conftest import ARTIFACTS, _start_server

TOLERANCE = 16  # px between the space above and below (and left and right)

# Union box of the brand column and the card, in page coordinates.
BLOCK = """
  () => {
    const card = document.querySelector('section[aria-label="Tu cuenta"]');
    const boxes = [card.previousElementSibling, card].map((el) => el.getBoundingClientRect());
    const top = Math.min(...boxes.map((b) => b.top)) + window.scrollY;
    const bottom = Math.max(...boxes.map((b) => b.bottom)) + window.scrollY;
    const left = Math.min(...boxes.map((b) => b.left));
    const right = Math.max(...boxes.map((b) => b.right));
    return {
      top, bottom, left, right, vw: window.innerWidth, vh: window.innerHeight,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      cardTop: card.getBoundingClientRect().top,
    };
  }
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


def login_at(browser: Browser, server: str, width: int, height: int) -> Page:
    viewport = {"width": width, "height": height}
    context = browser.new_context(viewport=viewport, reduced_motion="reduce", locale="es-MX")
    context.set_default_timeout(10_000)
    page = context.new_page()
    page.goto(f"{server}/login")
    expect(page.get_by_role("button", name="Entrar", exact=True)).to_be_visible()
    page.wait_for_load_state("networkidle")
    return page


def shot(page: Page, name: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=ARTIFACTS / f"login-layout-{name}.png", full_page=True)


@pytest.mark.parametrize(("width", "height"), [(1280, 800), (1920, 1000)])
def test_login_is_centered_when_it_fits(browser: Browser, server: str, width: int, height: int) -> None:
    page = login_at(browser, server, width, height)
    try:
        b = page.evaluate(BLOCK)
        above, below = b["top"], b["vh"] - b["bottom"]
        assert b["bottom"] - b["top"] < b["vh"], f"the block should fit {width}×{height}: {b}"  # noqa: S101
        where = f"above {above:.0f} px, below {below:.0f} px at {width}×{height}"
        assert abs(above - below) <= TOLERANCE, where  # noqa: S101
        assert abs(b["left"] - (b["vw"] - b["right"])) <= TOLERANCE, f"not centered horizontally: {b}"  # noqa: S101
        shot(page, f"{width}x{height}")

        # The card keeps its top edge when "Crear cuenta" makes it taller.
        card_top = b["cardTop"]
        page.get_by_role("tab", name="Crear cuenta").click()
        expect(page.get_by_label("Nombre completo")).to_be_visible()
        page.wait_for_timeout(300)
        assert page.evaluate(BLOCK)["cardTop"] == pytest.approx(card_top, abs=0.5)  # noqa: S101
    finally:
        page.context.close()


def test_short_window_starts_at_the_top_and_scrolls(browser: Browser, server: str) -> None:
    page = login_at(browser, server, 1280, 480)
    try:
        b = page.evaluate(BLOCK)
        assert b["bottom"] - b["top"] > b["vh"] - 64, f"the block should not fit 1280×480: {b}"  # noqa: S101
        assert 32 <= b["top"] <= 80, f"should start at the top with the usual padding: {b}"  # noqa: S101
        assert b["overflow"] <= 0  # noqa: S101
    finally:
        page.context.close()


@pytest.mark.parametrize(("width", "height"), [(390, 844), (360, 740)])
def test_phone_login_starts_at_the_top_without_side_scroll(
    browser: Browser, server: str, width: int, height: int
) -> None:
    page = login_at(browser, server, width, height)
    try:
        b = page.evaluate(BLOCK)
        assert b["overflow"] <= 0, f"horizontal scroll at {width}: {b}"  # noqa: S101
        assert b["top"] <= 48, f"phones keep the top padding: {b}"  # noqa: S101
        assert b["left"] >= 0 and b["right"] <= b["vw"]  # noqa: S101
        shot(page, f"{width}x{height}")
    finally:
        page.context.close()
