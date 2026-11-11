"""Course player (UPS-038): changing lesson keeps the shell (no full-page skeleton) and the sidebar search,
a search with no matches says so once, and the video area shows a placeholder until the iframe loads.
Slow responses are simulated by holding the requests until the test releases them."""

import contextlib
import re

from playwright.sync_api import Locator, Page, Route, expect

from e2e.conftest import Site
from e2e.test_flow import MEMBER, sign_in

FIRST_LESSON = "/a/upiixia/clases/1"
SAW_SKELETON = """
  () => {
    window.__sawSkeleton = false;
    new MutationObserver(() => {
      if (document.querySelector('[aria-label="Cargando clase"]')) window.__sawSkeleton = true;
    }).observe(document.body, { childList: true, subtree: true });
  }
"""


class Held:
    """Holds matching requests until released, like a slow network. `body` answers them instead of the network."""

    def __init__(self, page: Page, pattern: str, body: str | None = None) -> None:
        self.page, self.pattern, self.body = page, pattern, body
        self.routes: list[Route] = []
        page.route(pattern, lambda route: self.routes.append(route))

    def release(self) -> None:
        self.page.unroute(self.pattern)
        for route in self.routes:
            with contextlib.suppress(Exception):  # the request may have been cancelled meanwhile
                if self.body is None:
                    route.continue_()
                else:
                    route.fulfill(status=200, content_type="text/html", body=self.body)


def open_lesson(site: Site, path: str = FIRST_LESSON) -> Page:
    sign_in(site, MEMBER, path)
    page = site.page
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    return page


def search_box(site: Site) -> Locator:
    """The sidebar search on desktop; on a phone it lives in the "Contenido" drawer, which this opens."""
    page = site.page
    if site.name == "desktop":
        return page.locator("aside").get_by_role("searchbox")
    page.get_by_role("button", name="Contenido").click()
    return page.get_by_role("dialog").get_by_role("searchbox")


def close_drawer(site: Site) -> None:
    if site.name != "desktop":
        # Not Escape: inside a type=search field it clears the text before it closes the dialog.
        site.page.get_by_role("dialog").get_by_role("button", name="Cerrar").click()
        expect(site.page.get_by_role("dialog")).to_be_hidden()


def test_next_lesson_keeps_the_shell_and_the_search(site: Site) -> None:
    page = open_lesson(site)
    first_title = page.get_by_role("heading", level=1).inner_text()
    search_box(site).fill("Descenso")
    close_drawer(site)
    page.evaluate(SAW_SKELETON)

    held = Held(page, "**/api/lessons/*")
    page.get_by_role("link", name="Siguiente").click()
    expect(page).to_have_url(re.compile(r"/a/upiixia/clases/2$"))
    page.wait_for_timeout(300)  # the new lesson is still on its way
    expect(page.get_by_role("status", name="Cargando clase")).to_have_count(0)
    expect(page.get_by_role("heading", level=1)).to_have_text(first_title)  # the previous lesson stays meanwhile
    held.release()

    expect(page.get_by_role("heading", level=1)).not_to_have_text(first_title)
    assert page.evaluate("window.__sawSkeleton") is False  # noqa: S101
    expect(search_box(site)).to_have_value("Descenso")
    site.shot("player-next-lesson")


def test_search_without_matches_says_so_once(site: Site) -> None:
    open_lesson(site)
    box = search_box(site)
    box.fill("zzzz-sin-resultados")
    nav = site.page.get_by_role("navigation", name="Contenido de la ruta").locator("visible=true")
    expect(nav.get_by_text(re.compile("Sin coincidencias"))).to_have_count(1)
    site.shot("player-search-none")
    box.fill("")
    expect(nav.get_by_text(re.compile("Sin coincidencias"))).to_have_count(0)
    close_drawer(site)


def test_video_shows_a_placeholder_until_the_iframe_loads(site: Site) -> None:
    page = site.page
    held = Held(page, "**/www.youtube-nocookie.com/**", body="<!doctype html><title>video</title>")
    page = open_lesson(site)
    placeholder = page.get_by_role("status", name="Cargando video")
    expect(placeholder).to_be_visible()
    held.release()
    expect(placeholder).to_have_count(0)
    expect(page.locator("iframe")).to_be_visible()


def test_a_malformed_lesson_link_is_not_found(site: Site) -> None:
    sign_in(site, MEMBER, "/a/upiixia/clases/abc")
    page = site.page
    expect(page.get_by_text("No encontramos esta clase")).to_be_visible()
