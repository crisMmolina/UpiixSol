"""Phone drawers (UPS-043): a drawer enters and leaves on its own side, with the backdrop, on every frame.

Production video (iPhone, 390 px): opening "Más" painted the panel against the LEFT edge without the
backdrop, then it jumped to its place on the right. Here the panel box and the backdrop opacity are sampled
on each requestAnimationFrame while the drawer opens and closes, with motion enabled (and once with reduced
motion)."""

from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Page, expect

from e2e.conftest import VIEWPORTS, Site, _start_server
from e2e.test_flow import MEMBER, sign_in

TOLERANCE = 1  # px
PHONES = {"390": (390, 844), "360": (360, 740)}

# Samples {left, right, opacity, visible} of the drawer `title` on every frame for `ms` into window.__drawer.
SAMPLE = """
  ([title, ms]) => { window.__drawer = new Promise((resolve) => {
    const samples = [];
    const start = performance.now();
    const tick = () => {
      const dialog = document.querySelector(`dialog[aria-label="${title}"]`);
      const [backdrop, panel] = dialog ? dialog.children : [];
      if (dialog && dialog.open && panel) {
        const box = panel.getBoundingClientRect();
        samples.push({
          left: box.left,
          right: box.right,
          opacity: Number(getComputedStyle(backdrop).opacity),
          // More than 1 px on screen: a panel parked just off-screen can overlap by a subpixel (WebKit).
          visible: box.right > 1 && box.left < window.innerWidth - 1 && box.width > 0,
        });
      }
      if (performance.now() - start < ms) requestAnimationFrame(tick); else resolve(samples);
    };
    requestAnimationFrame(tick);
  }); }
"""


@pytest.fixture(scope="module")
def server() -> Iterator[str]:
    """Its own seeded server: the phone viewports come from PHONES, not from the desktop/mobile `site`."""
    url, process, workdir = _start_server()
    try:
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)
        workdir.cleanup()


def phone_page(browser: Browser, size: tuple[int, int], reduced: bool) -> Page:
    context = browser.new_context(
        viewport={"width": size[0], "height": size[1]},
        reduced_motion="reduce" if reduced else "no-preference",
        locale="es-MX",
    )
    context.set_default_timeout(10_000)
    return context.new_page()


@pytest.fixture(params=list(PHONES))
def phone(request: pytest.FixtureRequest, browser: Browser, server: str) -> Iterator[Site]:
    page = phone_page(browser, PHONES[request.param], reduced=False)
    try:
        yield Site(base_url=server, name=f"phone{request.param}", page=page)
    finally:
        page.context.close()


def settled_box(page: Page, title: str, timeout_ms: int = 2000) -> dict:
    """The panel box once two measurements 50 ms apart agree (the enter animation has finished)."""
    previous: dict | None = None
    for _ in range(timeout_ms // 50):
        page.evaluate(SAMPLE, [title, 50])
        current = page.evaluate("window.__drawer")[-1]
        if previous and abs(current["left"] - previous["left"]) <= 0.5 and current["opacity"] == 1:
            return current
        previous = current
    return previous or {}


def drawer_samples(page: Page, title: str, opener: str, ms: int = 700) -> tuple[list[dict], list[dict], dict]:
    """(opening samples, closing samples, settled box) for the drawer opened by the button `opener`."""
    page.evaluate(SAMPLE, [title, ms])  # starts sampling; the click below lands while it runs
    page.get_by_role("button", name=opener, exact=True).click()
    opening = page.evaluate("window.__drawer")
    dialog = page.get_by_role("dialog", name=title)
    expect(dialog).to_be_visible()
    settled = settled_box(page, title)
    page.evaluate(SAMPLE, [title, ms])
    dialog.get_by_role("button", name="Cerrar").click()
    closing = page.evaluate("window.__drawer")
    expect(dialog).to_be_hidden()
    return opening, closing, settled


def assert_on_its_side(samples: list[dict], settled: dict, side: str, phase: str) -> None:
    shown = [s for s in samples if s["visible"]]
    assert shown, f"{phase}: the panel was never on screen"  # noqa: S101
    for i, s in enumerate(shown):
        where = f"{phase} frame {i}: {s} vs settled {settled}"
        if side == "right":
            assert s["left"] >= settled["left"] - TOLERANCE, where  # noqa: S101
        else:
            assert s["right"] <= settled["right"] + TOLERANCE, where  # noqa: S101
        assert s["opacity"] > 0, f"{phase} frame {i}: panel on screen without the backdrop"  # noqa: S101


def test_more_drawer_enters_and_leaves_on_the_right(phone: Site) -> None:
    sign_in(phone, MEMBER, "/a/upiixia")
    page = phone.page
    expect(page.get_by_role("button", name="Más", exact=True)).to_be_visible()
    opening, closing, settled = drawer_samples(page, "Más", "Más")
    assert settled["right"] == pytest.approx(PHONES[phone.name.removeprefix("phone")][0], abs=TOLERANCE)  # noqa: S101
    assert_on_its_side(opening, settled, "right", "opening")
    assert_on_its_side(closing, settled, "right", "closing")


def test_contents_drawer_enters_and_leaves_on_the_left(phone: Site) -> None:
    sign_in(phone, MEMBER, "/a/upiixia/clases/1")
    page = phone.page
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    opening, closing, settled = drawer_samples(page, "Contenido de la ruta", "Contenido")
    assert settled["left"] == pytest.approx(0, abs=TOLERANCE)  # noqa: S101
    assert_on_its_side(opening, settled, "left", "opening")
    assert_on_its_side(closing, settled, "left", "closing")


def test_reduced_motion_drawer_appears_in_place_with_the_backdrop(browser: Browser, server: str) -> None:
    page = phone_page(browser, VIEWPORTS["mobile"], reduced=True)
    phone = Site(base_url=server, name="phone-reduced", page=page)
    try:
        sign_in(phone, MEMBER, "/a/upiixia")
        opening, closing, settled = drawer_samples(page, "Más", "Más", ms=300)
        shown = [s for s in opening if s["visible"]]
        assert shown and shown[0]["left"] == pytest.approx(settled["left"], abs=TOLERANCE)  # noqa: S101
        assert all(s["opacity"] == pytest.approx(1, abs=0.01) for s in shown)  # noqa: S101
        assert not [s for s in closing if s["visible"] and s["opacity"] < 0.99]  # noqa: S101
    finally:
        page.context.close()
