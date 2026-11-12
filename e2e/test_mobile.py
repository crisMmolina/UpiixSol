"""Mobile pass (UPS-040): every route of the three roles at 390×844 and 360×740.

Per screen (and per tab): no horizontal scroll, touch targets ≥ 44 px, nothing hidden behind the bottom tab
bar, no clipped button text. Per route at 390: while the API is held the skeleton is never wider than the
screen, and when the data arrives nothing that was already on screen moves more than 4 px (layout-shift
sources). Screenshots of the skeleton and the content go to e2e/artifacts/ for review."""

import contextlib
import re
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from playwright.sync_api import Browser, Page, Route, expect

from e2e.conftest import ARTIFACTS, SEED_PASSWORD, _start_server

PHONES = {"390": (390, 844), "360": (360, 740)}
MIN_TARGET = 44  # px, both sides (acceptance)
MAX_SHIFT = 4  # px

MEMBER = "alumno.demo@upiixsol.dev"
ADMIN_IA = "admin.ia@upiixsol.dev"
SUPERADMIN = "superadmin1@upiixsol.dev"

MEMBER_ROUTES = [
    "/",
    "/clubes",
    "/comunidad",
    "/calendario",
    "/blog",
    "/galeria",
    "/cuenta",
    "/a/upiixia",
    "/a/upiixia/rutas",
    "/a/upiixia/comunidad",
    "/a/upiixia/eventos",
    "/a/upiixia/recursos",
    "/a/upiixia/clases/1",
]
# Detail pages reached from the first card of a list (their slugs come from the seed).
DETAIL_FROM = {"/blog": r"^/blog/[^/]+$", "/galeria": r"^/galeria/[^/]+$"}
ADMIN_ROUTES = ["/panel/academia/upiixia"]
SUPERADMIN_ROUTES = ["/admin"]

# Problems on the current screen, computed in the page.
AUDIT = """
  (minTarget) => {
    const problems = [];
    const vw = window.innerWidth, vh = window.innerHeight;
    const overflow = document.documentElement.scrollWidth - vw;
    if (overflow > 0) problems.push(`horizontal scroll ${overflow}px`);
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return false;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.opacity === '0') return false;
      if (el.closest('[aria-hidden="true"], .sr-only, details:not([open]) > :not(summary)')) return false;
      if (el.closest('dialog:not([open])')) return false;
      return true;
    };
    const name = (el) => (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder')
        || el.name || el.tagName)
      .trim().replace(/\\s+/g, ' ').slice(0, 40);
    const targets = document.querySelectorAll(
      'a[href], button, input:not([type=hidden]), select, textarea, [role=tab], summary, [role=button]');
    for (const el of targets) {
      if (!visible(el)) continue;
      const cs = getComputedStyle(el);
      if (el.tagName === 'A' && cs.display === 'inline') continue;  // a link inside running text
      let box = el.getBoundingClientRect();
      if (el.matches('input[type=checkbox], input[type=radio], input[type=file], input[type=color]')) {
        const label = el.closest('label');
        if (!label) continue;
        box = label.getBoundingClientRect();
      }
      if (box.width < minTarget - 0.5 || box.height < minTarget - 0.5)
        problems.push(`target ${Math.round(box.width)}×${Math.round(box.height)} "${name(el)}"`);
      if ((el.tagName === 'BUTTON' || el.tagName === 'A') && el.scrollWidth > el.clientWidth + 1
          && cs.textOverflow !== 'ellipsis' && cs.overflow !== 'visible')
        problems.push(`clipped text "${name(el)}"`);
    }
    return problems;
  }
"""

# Controls under the fixed bottom tab bar once the page is scrolled to the end.
UNDER_TAB_BAR = """
  () => {
    const bar = [...document.querySelectorAll('nav')].find((n) => getComputedStyle(n).position === 'fixed'
      && n.getBoundingClientRect().bottom >= window.innerHeight - 1
      && n.getBoundingClientRect().height < 120);
    if (!bar) return [];
    const top = bar.getBoundingClientRect().top;
    const main = document.querySelector('main') || document.body;
    return [...main.querySelectorAll('a[href], button, input, select, textarea, [role=tab]')]
      .filter((el) => !el.closest('.sr-only, [aria-hidden="true"], dialog:not([open])'))
      .filter((el) => {
        const r = el.getBoundingClientRect();
        return r.height > 1 && r.width > 1 && r.bottom > top + 1 && r.top < window.innerHeight;
      })
      .map((el) => (el.getAttribute('aria-label') || el.textContent || el.tagName).trim().slice(0, 40));
  }
"""

# Layout shifts after the data arrives: the largest movement of anything that was already on screen.
WATCH_SHIFTS = """
  () => {
    window.__shifts = [];
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.hadRecentInput) continue;
        for (const s of entry.sources || []) {
          const p = s.previousRect, c = s.currentRect;
          if (!p || !c || p.height === 0 || p.width === 0) continue;
          window.__shifts.push({
            dy: Math.abs(c.y - p.y), dx: Math.abs(c.x - p.x),
            node: s.node ? (s.node.tagName + '.' + [...(s.node.classList || [])].slice(0, 3).join('.')) : '?',
          });
        }
      }
    }).observe({ type: 'layout-shift', buffered: false });
  }
"""
WIDE_SKELETONS = """
  () => [...document.querySelectorAll('.skeleton')]
    .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1)
    .map((el) => `${el.className.slice(0, 60)} → ${Math.round(el.getBoundingClientRect().right)}px`)
"""


@dataclass
class Phone:
    base_url: str
    page: Page

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"


@pytest.fixture(scope="module")
def server() -> Iterator[str]:
    url, process, workdir = _start_server()
    try:
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)
        workdir.cleanup()


def open_phone(browser: Browser, server: str, size: tuple[int, int], email: str | None) -> Phone:
    context = browser.new_context(
        viewport={"width": size[0], "height": size[1]},
        reduced_motion="reduce",
        locale="es-MX",
        has_touch=True,
    )
    context.set_default_timeout(15_000)
    phone = Phone(base_url=server, page=context.new_page())
    if email:
        phone.page.goto(phone.url("/login"))
        phone.page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(email)
        phone.page.get_by_label("Contraseña", exact=True).fill(SEED_PASSWORD)
        phone.page.get_by_role("button", name="Entrar").click()
        expect(phone.page).not_to_have_url(re.compile(r"/login"))
    return phone


def settle(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
    with contextlib.suppress(Exception):
        page.locator('[role="status"][aria-label^="Cargando"]').first.wait_for(state="detached", timeout=3000)


def scroll_to_end(page: Page) -> None:
    """Scroll until the bottom stays put (the page can still grow while images and lists settle)."""
    for _ in range(20):
        at_end = page.evaluate(
            """() => {
              window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' });
              const end = document.documentElement.scrollHeight - 1;
              return Math.ceil(window.scrollY + window.innerHeight) >= end;
            }"""
        )
        page.wait_for_timeout(100)
        if at_end:
            return


def audit_screen(page: Page, where: str) -> list[str]:
    settle(page)
    problems = [f"{where}: {p}" for p in page.evaluate(AUDIT, MIN_TARGET)]
    scroll_to_end(page)
    problems += [f'{where}: under the tab bar "{name}"' for name in page.evaluate(UNDER_TAB_BAR)]
    page.evaluate("() => window.scrollTo(0, 0)")
    return problems


def audit_route(page: Page, path: str, label: str) -> list[str]:
    problems = audit_screen(page, f"{label} {path}")
    tabs = page.get_by_role("tab")
    for i in range(tabs.count()):
        tab = tabs.nth(i)
        if not tab.is_visible() or tab.get_attribute("aria-selected") == "true":
            continue
        tab_name = (tab.inner_text() or "").strip()
        tab.click()
        problems += audit_screen(page, f"{label} {path} [{tab_name}]")
    return problems


def routes_for(phone: Phone, routes: list[str]) -> list[str]:
    found = list(routes)
    for list_path, pattern in DETAIL_FROM.items():
        if list_path not in routes:
            continue
        phone.page.goto(phone.url(list_path))
        settle(phone.page)
        hrefs = phone.page.eval_on_selector_all("a[href]", "(els) => els.map((a) => a.getAttribute('href'))")
        detail = next((h for h in hrefs if re.match(pattern, h or "")), None)
        if detail:
            found.append(detail)
    return found


ROLES = {
    "visitante": (None, ["/login", "/login?tab=registro"]),
    "miembro": (MEMBER, MEMBER_ROUTES),
    "admin del club": (ADMIN_IA, ADMIN_ROUTES),
    "superadmin": (SUPERADMIN, SUPERADMIN_ROUTES),
}


@pytest.mark.parametrize("size", list(PHONES))
@pytest.mark.parametrize("role", list(ROLES))
def test_every_screen_fits_the_phone(browser: Browser, server: str, role: str, size: str) -> None:
    email, routes = ROLES[role]
    phone = open_phone(browser, server, PHONES[size], email)
    try:
        problems: list[str] = []
        for path in routes_for(phone, routes):
            phone.page.goto(phone.url(path))
            problems += audit_route(phone.page, path, f"{role}@{size}")
            if size == "390":
                ARTIFACTS.mkdir(parents=True, exist_ok=True)
                slug = re.sub(r"[^a-z0-9]+", "-", f"{role}-{path}".lower()).strip("-")
                phone.page.screenshot(path=ARTIFACTS / f"mobile-{slug}.png", full_page=True)
        report = ARTIFACTS / f"mobile-problems-{re.sub(r'[^a-z0-9]+', '-', role)}-{size}.txt"
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        report.write_text("\n".join(dict.fromkeys(problems)) + "\n", encoding="utf-8")
        assert not problems, "\n".join(dict.fromkeys(problems))  # noqa: S101
    finally:
        phone.page.context.close()


class Held:
    """Holds every API call except the session and the site brand, like a slow network."""

    SKIP = ("/api/auth/", "/api/site", "/api/health", "/api/ready")

    def __init__(self, page: Page) -> None:
        self.page = page
        self.routes: list[Route] = []
        self.holding = True
        page.route("**/api/**", self._handle)

    def _handle(self, route: Route) -> None:
        if not self.holding or any(part in route.request.url for part in self.SKIP):
            route.continue_()
        else:
            self.routes.append(route)

    def release(self) -> None:
        self.holding = False
        for route in self.routes:
            with contextlib.suppress(Exception):
                route.continue_()
        self.routes.clear()


SKELETON_ROUTES = [(MEMBER, path) for path in MEMBER_ROUTES if path != "/"] + [
    (MEMBER, "/"),
    (ADMIN_IA, "/panel/academia/upiixia"),
    (SUPERADMIN, "/admin"),
]


@pytest.mark.parametrize(
    ("email", "path"), SKELETON_ROUTES, ids=[f"{e.split('@')[0]}{p}" for e, p in SKELETON_ROUTES]
)
def test_skeleton_matches_the_content(browser: Browser, server: str, email: str, path: str) -> None:
    phone = open_phone(browser, server, PHONES["390"], email)
    page = phone.page
    try:
        page.goto(phone.url("/cuenta" if path != "/cuenta" else "/"))
        settle(page)
        held = Held(page)
        page.goto(phone.url(path))
        page.wait_for_timeout(400)
        wide = page.evaluate(WIDE_SKELETONS)
        slug = re.sub(r"[^a-z0-9]+", "-", f"{email.split('@')[0]}-{path}".lower()).strip("-")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=ARTIFACTS / f"skeleton-{slug}-before.png")
        page.evaluate(WATCH_SHIFTS)
        held.release()
        settle(page)
        page.wait_for_timeout(300)
        page.screenshot(path=ARTIFACTS / f"skeleton-{slug}-after.png")
        shifts = page.evaluate("window.__shifts")
        moved = [s for s in shifts if s["dy"] > MAX_SHIFT or s["dx"] > MAX_SHIFT]
        assert not wide, f"{path}: skeleton wider than the screen: {wide}"  # noqa: S101
        assert not moved, (  # noqa: S101
            f"{path}: content moved when the data arrived: "
            + ", ".join(
                f"{s['node']} dy={s['dy']:.0f} dx={s['dx']:.0f}" for s in moved[:6]
            )
        )
    finally:
        page.context.close()
