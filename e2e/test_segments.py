"""Video segments (UPS-048): the player keeps a lesson's ?start=&end= when it enables the JS API, and the
lesson form reads the start from a pasted `t=` and refuses an end before the start."""

import json
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Route, expect

from e2e.conftest import Site
from e2e.test_flow import ADMIN_IA, MEMBER, sign_in

FIRST_LESSON = "/a/upiixia/clases/1"
CONTENT_TAB = "/panel/academia/upiixia?tab=contenido"
SEGMENT_ERROR = "El fin del tramo debe ser mayor que el inicio."


def _with_segment(route: Route) -> None:
    """The lesson as the API returns it once it has a 14:10–48:58 segment (UPS-045 builds embed_url)."""
    response = route.fetch()
    lesson = response.json()
    lesson.update(start_s=850, end_s=2938, embed_url=f"{lesson['embed_url'].split('?')[0]}?start=850&end=2938")
    route.fulfill(response=response, body=json.dumps(lesson))


def test_player_src_keeps_segment_params(site: Site) -> None:
    page = site.page
    page.route("**/api/lessons/1", _with_segment)
    try:
        sign_in(site, MEMBER, FIRST_LESSON)
        frame = page.locator('iframe[src*="youtube-nocookie.com/embed/"]')
        frame.wait_for(state="attached")
        src = frame.get_attribute("src") or ""
        assert src.count("?") == 1  # noqa: S101 · one query, merged
        query = parse_qs(urlsplit(src).query)
        assert query["start"] == ["850"]  # noqa: S101
        assert query["end"] == ["2938"]  # noqa: S101
        assert query["enablejsapi"] == ["1"]  # noqa: S101
    finally:
        page.unroute("**/api/lessons/1")


def test_admin_form_prefills_start_from_url(site: Site) -> None:
    page = site.page
    sign_in(site, ADMIN_IA, CONTENT_TAB)
    page.get_by_role("button", name="Agregar clase").first.click()
    dialog = page.get_by_role("dialog", name="Nueva clase")
    dialog.get_by_label("URL de YouTube").fill("https://youtu.be/dQw4w9WgXcQ?t=850")
    expect(dialog.get_by_label("Inicio del tramo")).to_have_value("14:10")
    site.shot("segment-prefill")
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()


def test_admin_form_rejects_end_before_start(site: Site) -> None:
    page = site.page
    sign_in(site, ADMIN_IA, CONTENT_TAB)
    page.get_by_role("button", name="Agregar clase").first.click()
    dialog = page.get_by_role("dialog", name="Nueva clase")
    dialog.get_by_label("Título de la clase").fill("Tramo al revés")
    dialog.get_by_label("URL de YouTube").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    dialog.get_by_label("Inicio del tramo").fill("10:00")
    dialog.get_by_label("Fin del tramo").fill("5:00")
    dialog.get_by_role("button", name="Agregar clase").click()
    expect(dialog.get_by_text(SEGMENT_ERROR).first).to_be_visible()
    expect(dialog).to_be_visible()  # nothing saved
    site.shot("segment-error")
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()
