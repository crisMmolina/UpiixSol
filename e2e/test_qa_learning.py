"""QA learning and Player (UPS-052): docs/PRUEBAS-CAMPUS.md §5, LRN-01…08, in a real browser.

A lesson is completed only when its YouTube video ends (web/src/features/learning/youtube.ts): the test sends
the same `onStateChange` message the embed would (VIDEO_ENDED from test_flow.py). The YouTube iframe is
answered locally, so no network is needed. Expected orders and ids come from the API, never hard-coded.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import Site
from e2e.test_flow import ADMIN_IA, MEMBER, VIDEO_ENDED, sign_in, sign_out

# Stands in for the YouTube embed. Since UPS-048 the Player shows the video only once the embed answers
# over postMessage, so it answers the page's handshake with a neutral state (-1, unstarted): never "ended"
# (0), which would complete lessons on its own; tests send VIDEO_ENDED themselves when they mean it (UPS-069).
FAKE_EMBED = """<!doctype html><title>video</title><script>
const state = JSON.stringify({ event: "infoDelivery", info: { playerState: -1 } });
const answer = () => parent.postMessage(state, "*");
addEventListener("message", answer);
answer();
</script>"""


def fake_youtube(page: Page) -> None:
    page.route(
        "**/www.youtube-nocookie.com/**",
        lambda route: route.fulfill(status=200, content_type="text/html", body=FAKE_EMBED),
    )


def token(site: Site) -> str:
    """The signed-in browser's own access token (same session; the refresh cookie rotates as usual)."""
    response = site.page.request.post(site.url("/api/auth/refresh"), headers={"X-Requested-With": "fetch"})
    assert response.ok, response.text()  # noqa: S101
    return response.json()["access_token"]


def api(site: Site, method: str, path: str, bearer: str, **kwargs):
    headers = {"Authorization": f"Bearer {bearer}", "X-Requested-With": "fetch"}
    return site.page.request.fetch(site.url(path), method=method, headers=headers, **kwargs)


def route_detail(site: Site, bearer: str) -> dict:
    routes = api(site, "GET", "/api/academies/upiixia/routes", bearer).json()["items"]
    return api(site, "GET", f"/api/routes/{routes[0]['id']}", bearer).json()


def lesson_ids(detail: dict) -> list[int]:
    return [lesson["id"] for module in detail["modules"] for lesson in module["lessons"]]


def percent(site: Site, bearer: str) -> int:
    return route_detail(site, bearer)["progress"]["percent"]


def complete_in_player(site: Site, lesson_id: int) -> None:
    page = site.page
    fake_youtube(page)
    page.goto(site.url(f"/a/upiixia/clases/{lesson_id}"))
    page.locator('iframe[src*="youtube-nocookie.com/embed/"]').wait_for(state="attached")
    page.evaluate(VIDEO_ENDED)
    expect(page.get_by_text("Clase completada").first).to_be_visible()


def sidebar_percent(site: Site) -> str:
    page = site.page
    if site.name == "mobile":  # the route sidebar lives in a drawer on phones
        page.get_by_role("button", name="Contenido").click()
    bar = page.get_by_role("progressbar").first
    value = bar.get_attribute("aria-valuenow") or ""
    if site.name == "mobile":
        page.get_by_role("dialog").get_by_role("button", name="Cerrar").click()
    return value


# ── LRN-01 · navigation follows the admin's order ────────────


def test_navigation_follows_the_admins_order(site: Site) -> None:
    sign_in(site, ADMIN_IA, "/panel/academia")
    admin = token(site)
    detail = route_detail(site, admin)
    module = detail["modules"][0]
    reversed_ids = [lesson["id"] for lesson in module["lessons"]][::-1]
    reordered = api(
        site, "PUT", f"/api/modules/{module['id']}/lessons/order", admin, data={"ids": reversed_ids}
    )
    assert reordered.ok, reordered.text()  # noqa: S101

    sign_in(site, MEMBER, "/a/upiixia/rutas")
    page = site.page
    fake_youtube(page)
    page.get_by_role("link", name=re.compile(detail["title"])).first.click()
    expect(page).to_have_url(re.compile(r"/a/upiixia/clases/\d+"))
    expect(page.get_by_role("heading", level=1)).to_be_visible()  # the player replaced its skeleton
    if site.name == "mobile":
        page.get_by_role("button", name="Contenido").click()
    hrefs = page.evaluate(
        """() => {
          const nav = [...document.querySelectorAll('nav[aria-label="Contenido de la ruta"]')]
            .find((n) => n.getClientRects().length > 0);
          const module = nav && nav.querySelector('details');
          const links = module ? [...module.querySelectorAll("a[href*='/clases/']")] : [];
          return links.map((a) => a.getAttribute('href'));
        }"""
    )
    assert [int(h.rsplit("/", 1)[1]) for h in hrefs] == reversed_ids  # noqa: S101


# ── LRN-02 · the Player loads with its thumbnail ─────────────


def test_player_loads_the_video_with_its_thumbnail(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    bearer = token(site)
    lesson = api(site, "GET", f"/api/lessons/{lesson_ids(route_detail(site, bearer))[0]}", bearer).json()
    page = site.page
    fake_youtube(page)
    page.goto(site.url(f"/a/upiixia/clases/{lesson['id']}"))
    frame = page.locator('iframe[src*="youtube-nocookie.com/embed/"]')
    expect(frame).to_have_attribute(
        "src", re.compile(rf"/embed/{lesson['youtube_video_id']}\?.*enablejsapi=1")
    )
    box = frame.locator("xpath=..")
    expect(box).to_have_attribute("style", re.compile(rf"img\.youtube\.com/vi/{lesson['youtube_video_id']}/"))
    expect(page.get_by_role("status", name="Cargando video")).to_have_count(0)  # the iframe answered


# ── LRN-03 / LRN-04 / LRN-05 · progress ──────────────────────


def test_completing_and_uncompleting_moves_the_route_percent(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    bearer = token(site)
    detail = route_detail(site, bearer)
    pending = [lesson["id"] for m in detail["modules"] for lesson in m["lessons"] if not lesson["completed"]]
    assert pending, "the member should have lessons left"  # noqa: S101
    before = detail["progress"]["percent"]

    complete_in_player(site, pending[0])
    site.page.reload()  # LRN-03: it survives a reload
    raised = percent(site, token(site))
    assert raised > before  # noqa: S101
    assert sidebar_percent(site) == str(raised)  # noqa: S101

    # LRN-04 (human decision 2026-11-12, UPS-052 decision record): a completed lesson stays completed.
    # There is no UI or API to unmark it: the Player offers no such control, and the state survives a reload.
    # Removing the DELETE endpoint is UPS-062; this test does not use it.
    page = site.page
    page.goto(site.url(f"/a/upiixia/clases/{pending[0]}"))
    expect(page.get_by_text("Clase completada").first).to_be_visible()
    unmark = re.compile(r"desmarcar|deshacer|no completada|marcar como pendiente", re.I)
    expect(page.get_by_text(unmark)).to_have_count(0)
    assert percent(site, token(site)) == raised  # noqa: S101
    assert sidebar_percent(site) == str(raised)  # noqa: S101


def test_completing_every_lesson_shows_100_and_a_finished_route(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    detail = route_detail(site, token(site))
    for module in detail["modules"]:
        for lesson in module["lessons"]:
            if not lesson["completed"]:
                complete_in_player(site, lesson["id"])
    assert percent(site, token(site)) == 100  # noqa: S101
    page = site.page
    page.goto(site.url("/a/upiixia/rutas"))
    card = page.get_by_role("link", name=re.compile(detail["title"])).first
    expect(card).to_contain_text(re.compile(r"Repasar|100\s*%"))


# ── LRN-06 · previous / next across modules ──────────────────


def test_previous_and_next_cross_modules(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    detail = route_detail(site, token(site))
    assert len(detail["modules"]) >= 2, "the seed route has two modules"  # noqa: S101
    last_of_first = detail["modules"][0]["lessons"][-1]["id"]
    first_of_second = detail["modules"][1]["lessons"][0]["id"]
    page = site.page
    fake_youtube(page)
    page.goto(site.url(f"/a/upiixia/clases/{last_of_first}"))
    page.get_by_role("link", name="Siguiente").click()
    expect(page).to_have_url(re.compile(rf"/a/upiixia/clases/{first_of_second}$"))
    expect(page.get_by_role("heading", level=1)).to_have_text(detail["modules"][1]["lessons"][0]["title"])
    page.get_by_role("link", name="Anterior").click()
    expect(page).to_have_url(re.compile(rf"/a/upiixia/clases/{last_of_first}$"))
    ids = lesson_ids(detail)
    page.goto(site.url(f"/a/upiixia/clases/{ids[0]}"))
    expect(page.get_by_role("link", name="Anterior")).to_have_attribute("aria-disabled", "true")
    page.goto(site.url(f"/a/upiixia/clases/{ids[-1]}"))
    expect(page.get_by_role("link", name="Siguiente")).to_have_attribute("aria-disabled", "true")


# ── LRN-07 · hostile markdown runs nothing ───────────────────


def test_hostile_lesson_markdown_runs_nothing(site: Site) -> None:
    sign_in(site, ADMIN_IA, "/panel/academia")
    admin = token(site)
    lesson_id = lesson_ids(route_detail(site, admin))[0]
    hostile = (
        "Hola **mundo**\n\n<script>window.__lrn07 = 'script'</script>\n\n"
        '<img src="x" onerror="window.__lrn07 = \'onerror\'">\n\n'
        "[enlace](javascript:window.__lrn07='href')"
    )
    patched = api(site, "PATCH", f"/api/lessons/{lesson_id}", admin, data={"description": hostile})
    assert patched.ok, patched.text()  # noqa: S101

    sign_in(site, MEMBER, "/")
    page = site.page
    fake_youtube(page)
    page.goto(site.url(f"/a/upiixia/clases/{lesson_id}"))
    description = page.get_by_role("region", name="Descripción")
    expect(description.get_by_text("mundo")).to_be_visible()
    page.wait_for_timeout(300)
    if description.get_by_role("link", name="enlace").count():
        description.get_by_role("link", name="enlace").click()
    assert page.evaluate("window.__lrn07") is None  # noqa: S101
    assert description.locator("script, [onerror], a[href^='javascript']").count() == 0  # noqa: S101


# ── LRN-08 · a visitor cannot complete anything ──────────────


@pytest.mark.parametrize("anonymous_call", ["page", "api"])
def test_a_visitor_is_asked_to_log_in_and_nothing_is_saved(site: Site, anonymous_call: str) -> None:
    sign_in(site, MEMBER, "/")
    bearer = token(site)
    detail = route_detail(site, bearer)
    pending = [lesson["id"] for m in detail["modules"] for lesson in m["lessons"] if not lesson["completed"]]
    target = pending[0] if pending else lesson_ids(detail)[0]
    before = detail["progress"]["percent"]

    sign_out(site.page)
    page = site.page
    if anonymous_call == "page":
        page.goto(site.url(f"/a/upiixia/clases/{target}"))
        expect(page).to_have_url(re.compile(r"/login\?next="))
    else:
        response = page.request.post(
            site.url(f"/api/lessons/{target}/complete"), headers={"X-Requested-With": "fetch"}
        )
        assert response.status == 401  # noqa: S101

    sign_in(site, MEMBER, "/")
    assert percent(site, token(site)) == before  # noqa: S101
