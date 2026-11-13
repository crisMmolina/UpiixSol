"""QA mobile and accessibility (UPS-057): docs/PRUEBAS-CAMPUS.md §12 (MOB-01…04) and §13 (A11Y-01…05).

MOB-01 reuses the per-screen audit of test_mobile.py at 375 px (landscape 812×375 for MOB-04). A11Y-01 needs
axe-core in web/node_modules (not a dependency yet: UPS-001 owns web/package.json, asked the human); until it
is there the test fails on purpose instead of passing silently. A11Y-05 (NVDA) is manual: see
docs/qa/a11y-report.md.
"""

import contextlib
import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Page, expect

from e2e.conftest import ARTIFACTS, ROOT, SEED_PASSWORD, _start_server
from e2e.test_mobile import (
    ADMIN_IA,
    ADMIN_ROUTES,
    MEMBER,
    MEMBER_ROUTES,
    SUPERADMIN,
    SUPERADMIN_ROUTES,
    audit_route,
    audit_screen,
    open_phone,
    settle,
)

PHONE = (375, 812)
LANDSCAPE = (812, 375)
DESKTOP = (1440, 900)
USER_MENU = 'header button[aria-haspopup="menu"]:not([aria-label])'
AXE = ROOT / "web" / "node_modules" / "axe-core" / "axe.min.js"
# Visible focus: a focused control has a real outline or a box shadow (index.css: :focus-visible outline).
FOCUS_STYLE = """
  (el) => {
    const cs = getComputedStyle(el);
    const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
    return outline || cs.boxShadow !== 'none';
  }
"""
# Contrast: a probe span inside <main> so it inherits the academy theme of the page being read.
PROBE_COLORS = """
  ([fg, bg]) => {
    const host = document.querySelector('main') || document.body;
    const probe = document.createElement('span');
    probe.textContent = 'x';
    probe.style.color = `var(${fg})`;
    probe.style.backgroundColor = `var(${bg})`;
    host.appendChild(probe);
    const cs = getComputedStyle(probe);
    const colors = [cs.color, cs.backgroundColor];
    probe.remove();
    return colors;
  }
"""
# Tables that do not sit inside a horizontally scrolling container (MOB-03).
TABLES_WITHOUT_SCROLL = """
  () => {
    const scrolls = (el) => /(auto|scroll)/.test(getComputedStyle(el).overflowX);
    const bad = [];
    for (const table of document.querySelectorAll('table')) {
      if (!table.offsetParent) continue;
      let box = table.parentElement;
      while (box && box !== document.body && !scrolls(box)) box = box.parentElement;
      if (!box || box === document.body) bad.push(table.getAttribute('aria-label') || 'table');
    }
    return bad;
  }
"""
# Motion: the longest running animation (seconds) on the page.
LONGEST_ANIMATION = """
  () => Math.max(0, ...[...document.querySelectorAll('body *')]
    .map((el) => getComputedStyle(el))
    .filter((cs) => cs.animationName !== 'none')
    .map((cs) => parseFloat(cs.animationDuration) || 0))
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


def srgb_channel(value: float) -> float:
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (srgb_channel(c / 255) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    """WCAG 2.x ratio of two computed `rgb(...)` / `rgba(...)` strings."""

    def parse(text: str) -> tuple[float, float, float]:
        numbers = [float(n) for n in re.findall(r"[\d.]+", text)[:3]]
        return (numbers[0], numbers[1], numbers[2])

    lighter, darker = sorted((luminance(parse(fg)), luminance(parse(bg))), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@contextlib.contextmanager
def phone_session(browser: Browser, server: str, size: tuple[int, int], email: str | None) -> Iterator[Page]:
    phone = open_phone(browser, server, size, email)
    try:
        yield phone.page
    finally:
        phone.page.context.close()


def goto(page: Page, server: str, path: str) -> None:
    page.goto(f"{server}{path}")
    settle(page)


def focus_is_visible(page: Page) -> bool:
    return bool(page.evaluate(f"(() => {{ const f = {FOCUS_STYLE}; return f(document.activeElement); }})()"))


def inside_dialog(page: Page) -> bool:
    return bool(page.evaluate("() => !!document.activeElement.closest('dialog[open]')"))


FOCUSABLE = (
    "a[href], button:not([disabled]), input:not([type=hidden]), select, textarea, "
    "[tabindex]:not([tabindex='-1'])"
)


def dialog_stops(page: Page) -> int:
    return int(
        page.evaluate(
            "(selector) => document.querySelector('dialog[open]').querySelectorAll(selector).length",
            FOCUSABLE,
        )
    )


def tab_through_dialog(page: Page) -> None:
    """One full lap of the dialog plus two extra Tabs: every stop must stay inside the open dialog."""
    for _ in range(dialog_stops(page) + 2):
        page.keyboard.press("Tab")
        assert inside_dialog(page), "el foco salió del diálogo con Tab (sin cerrarlo)"  # noqa: S101


# ── MOB-01 · every route at 375 px ──────────────────────────


@pytest.mark.parametrize(
    ("email", "routes"),
    [
        (None, ["/login", "/login?tab=registro"]),
        (MEMBER, MEMBER_ROUTES),
        (ADMIN_IA, ADMIN_ROUTES),
        (SUPERADMIN, SUPERADMIN_ROUTES),
    ],
    ids=["visitante", "miembro", "admin-club", "superadmin"],
)
def test_mob01_every_route_fits_375(
    browser: Browser, server: str, email: str | None, routes: list[str]
) -> None:
    with phone_session(browser, server, PHONE, email) as page:
        problems: list[str] = []
        for path in routes:
            page.goto(f"{server}{path}")
            problems += audit_route(page, path, "375")
        assert not problems, "\n".join(problems)  # noqa: S101


# ── MOB-02 · menu, ClubSwitcher and modals at 375 px ─────────


def test_mob02_account_menu_and_club_switcher_open_and_close(browser: Browser, server: str) -> None:
    with phone_session(browser, server, PHONE, MEMBER) as page:
        goto(page, server, "/a/upiixia")

        trigger = page.locator(USER_MENU)
        trigger.click()
        expect(page.get_by_role("menu")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("menu")).to_have_count(0)
        expect(trigger).to_be_focused()

        switcher = page.get_by_role("button", name="Cambiar de club")
        switcher.click()
        expect(page.get_by_role("menu")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("menu")).to_have_count(0)
        expect(switcher).to_be_focused()


def test_mob02_drawer_traps_focus_and_returns_it(browser: Browser, server: str) -> None:
    with phone_session(browser, server, PHONE, MEMBER) as page:
        goto(page, server, "/a/upiixia")
        opener = page.get_by_role("button", name="Más", exact=True)
        opener.click()
        expect(page.locator("dialog[open]")).to_be_visible()
        page.screenshot(path=ARTIFACTS / "ups057-375-drawer-mas.png")
        tab_through_dialog(page)
        page.keyboard.press("Escape")
        expect(page.locator("dialog[open]")).to_have_count(0)
        expect(opener).to_be_focused()


def test_mob02_modal_traps_focus_and_returns_it(browser: Browser, server: str) -> None:
    with phone_session(browser, server, PHONE, ADMIN_IA) as page:
        goto(page, server, "/a/upiixia/eventos")
        opener = page.get_by_role("button", name="Nuevo evento")
        opener.click()
        expect(page.locator("dialog[open]")).to_be_visible()
        tab_through_dialog(page)
        page.keyboard.press("Escape")
        expect(page.locator("dialog[open]")).to_have_count(0)
        expect(opener).to_be_focused()


# ── MOB-03 · Player and admin tables scroll inside their container ──


def test_mob03_player_scrolls_inside_its_blocks(browser: Browser, server: str) -> None:
    with phone_session(browser, server, PHONE, MEMBER) as page:
        goto(page, server, "/a/upiixia/clases/1")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 0, f"la página hace scroll horizontal {overflow}px"  # noqa: S101
        page.screenshot(path=ARTIFACTS / "ups057-375-player.png", full_page=True)


@pytest.mark.parametrize(
    ("email", "path"),
    [(ADMIN_IA, "/panel/academia/upiixia"), (SUPERADMIN, "/admin")],
    ids=["admin-club", "superadmin"],
)
def test_mob03_admin_tables_scroll_inside_their_container(
    browser: Browser, server: str, email: str, path: str
) -> None:
    with phone_session(browser, server, PHONE, email) as page:
        goto(page, server, path)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 0, f"la página hace scroll horizontal {overflow}px"  # noqa: S101
        loose = page.evaluate(TABLES_WITHOUT_SCROLL)
        assert not loose, f"tablas sin contenedor con scroll: {loose}"  # noqa: S101
        page.screenshot(
            path=ARTIFACTS / f"ups057-375-{path.strip('/').replace('/', '-')}.png", full_page=True
        )


# ── MOB-04 · landscape phone ────────────────────────────────


@pytest.mark.parametrize(
    ("email", "paths"),
    [
        (None, ["/login"]),
        (MEMBER, ["/", "/a/upiixia", "/a/upiixia/clases/1"]),
        (ADMIN_IA, ["/panel/academia/upiixia"]),
    ],
    ids=["visitante", "miembro", "admin-club"],
)
def test_mob04_landscape_does_not_break(
    browser: Browser, server: str, email: str | None, paths: list[str]
) -> None:
    with phone_session(browser, server, LANDSCAPE, email) as page:
        problems: list[str] = []
        for path in paths:
            page.goto(f"{server}{path}")
            problems += audit_screen(page, f"landscape {path}")
        assert not problems, "\n".join(problems)  # noqa: S101


# ── A11Y-01 · axe, 0 serious or critical violations ──────────

AXE_PAGES = [
    ("inicio", "/", MEMBER),
    ("academia", "/a/upiixia", MEMBER),
    ("player", "/a/upiixia/clases/1", MEMBER),
    ("comunidad", "/comunidad", MEMBER),
    ("cuenta", "/cuenta", MEMBER),
    ("admin", "/panel/academia/upiixia", ADMIN_IA),
    ("superadmin", "/admin", SUPERADMIN),
]


@pytest.mark.parametrize("size", [PHONE, DESKTOP], ids=["375", "1440"])
@pytest.mark.parametrize(("label", "path", "email"), AXE_PAGES, ids=[p[0] for p in AXE_PAGES])
def test_a11y01_axe_has_no_serious_violations(
    browser: Browser, server: str, size: tuple[int, int], label: str, path: str, email: str
) -> None:
    assert AXE.exists(), (  # noqa: S101
        f"axe-core no está instalado ({AXE}). A11Y-01 queda bloqueado hasta que web/package.json "
        "agregue axe-core (UPS-001, pedido al humano)."
    )
    with phone_session(browser, server, size, email) as page:
        goto(page, server, path)
        page.add_script_tag(path=str(AXE))
        result = page.evaluate(
            "async () => await axe.run(document, {runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']})"
        )
        serious = [
            f"{v['id']} ({v['impact']}): {v['help']} · {len(v['nodes'])} nodos"
            for v in result["violations"]
            if v["impact"] in ("serious", "critical")
        ]
        assert not serious, f"{label} {path} @{size[0]}: " + " | ".join(serious)  # noqa: S101


# ── A11Y-02 · keyboard only, visible focus ───────────────────


def test_a11y02_login_is_reachable_and_submittable_by_keyboard(browser: Browser, server: str) -> None:
    with phone_session(browser, server, DESKTOP, None) as page:
        goto(page, server, "/login")
        page.get_by_role("textbox", name="Boleta o correo", exact=True).focus()
        page.keyboard.type(MEMBER)
        page.keyboard.press("Tab")
        expect(page.get_by_label("Contraseña", exact=True)).to_be_focused()
        assert focus_is_visible(page), "el campo Contraseña no muestra foco"  # noqa: S101
        page.keyboard.type(SEED_PASSWORD)
        page.keyboard.press("Tab")
        expect(page.get_by_role("button", name="Entrar")).to_be_focused()
        assert focus_is_visible(page), "el botón Entrar no muestra foco"  # noqa: S101
        page.keyboard.press("Enter")
        expect(page).not_to_have_url(re.compile(r"/login"))


@pytest.mark.parametrize("path", ["/", "/a/upiixia/clases/1"], ids=["inicio", "player"])
def test_a11y02_every_tab_stop_shows_a_visible_focus(browser: Browser, server: str, path: str) -> None:
    with phone_session(browser, server, DESKTOP, MEMBER) as page:
        goto(page, server, path)
        hidden: list[str] = []
        for _ in range(60):
            page.keyboard.press("Tab")
            tag = page.evaluate("() => document.activeElement.tagName")
            if tag == "BODY":  # end of the tab order: focus went back to the browser UI
                break
            # An iframe's own focus ring is painted by the cross-origin content: not measurable from here.
            if tag != "IFRAME" and not focus_is_visible(page):
                hidden.append(
                    page.evaluate("() => (document.activeElement.textContent || tag).trim().slice(0, 40)")
                )
        assert not hidden, f"paradas de Tab sin foco visible: {hidden}"  # noqa: S101


# ── A11Y-03 · AA contrast of the rendered text pairs ─────────

TEXT_PAIRS_LIGHT = [
    ("--theme-ink", "--theme-bg"),
    ("--theme-muted", "--theme-bg"),
    ("--theme-link", "--theme-bg"),
    ("--theme-danger", "--theme-bg"),
]


@pytest.mark.parametrize("path", ["/clubes", "/a/upiixia"], ids=["campus", "academia"])
def test_a11y03_rendered_text_pairs_meet_aa_on_light_background(
    browser: Browser, server: str, path: str
) -> None:
    pairs = list(TEXT_PAIRS_LIGHT)
    if path.startswith("/a/"):
        pairs.append(("--academy-on-primary", "--academy-primary"))
    with phone_session(browser, server, DESKTOP, None) as page:
        goto(page, server, path)
        failing = []
        for fg, bg in pairs:
            colors = page.evaluate(PROBE_COLORS, [fg, bg])
            ratio = contrast(colors[0], colors[1])
            if ratio < 4.5:
                failing.append(f"{fg} sobre {bg}: {ratio:.2f}:1")
        assert not failing, f"{path}: " + " | ".join(failing)  # noqa: S101


# ── A11Y-04 · prefers-reduced-motion removes large animation ─


def open_drawer_and_measure(browser: Browser, server: str, reduced: str) -> tuple[float, float]:
    """Longest Web Animation and CSS animation (seconds) started by opening the mobile "Más" drawer.

    The drawer is the one large motion in the app (Motion, WAAPI): without the preference it runs ~220 ms.
    """
    context = browser.new_context(
        viewport={"width": PHONE[0], "height": PHONE[1]},
        reduced_motion=reduced,
        locale="es-MX",
        has_touch=True,
    )
    try:
        page = context.new_page()
        page.goto(f"{server}/login")
        page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(MEMBER)
        page.get_by_label("Contraseña", exact=True).fill(SEED_PASSWORD)
        page.get_by_role("button", name="Entrar").click()
        expect(page).not_to_have_url(re.compile(r"/login"))
        goto(page, server, "/a/upiixia")
        page.get_by_role("button", name="Más", exact=True).click()
        page.wait_for_timeout(60)
        waapi = page.evaluate(
            """() => Math.max(0, ...document.getAnimations().map(
              (a) => Number(a.effect.getComputedTiming().duration) || 0))"""
        )
        css = page.evaluate(LONGEST_ANIMATION)
        page.screenshot(path=ARTIFACTS / f"ups057-drawer-motion-{reduced}.png")
        return waapi / 1000, css
    finally:
        context.close()


def test_a11y04_reduced_motion_removes_the_drawer_animation(browser: Browser, server: str) -> None:
    moving, _ = open_drawer_and_measure(browser, server, "no-preference")
    assert moving > 0.1, f"sin la preferencia el cajón no anima ({moving}s): la prueba no mide nada"  # noqa: S101
    still, css = open_drawer_and_measure(browser, server, "reduce")
    assert still <= 0.001, f"con reduced-motion el cajón sigue animando {still}s (WAAPI)"  # noqa: S101
    assert css <= 0.001, f"con reduced-motion hay animación CSS de {css}s"  # noqa: S101
