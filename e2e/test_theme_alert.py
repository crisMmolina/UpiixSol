"""Alert color (UPS-064): a club without color_accent_2 shows errors and delete buttons in the site's alert
red, never in its secondary color (UpiixIA's green #04944F read a validation error as success).

Runs at 1280 and 390 (the `site` fixture). The club-color case changes UpiixIA's branding, so it runs last.
"""

import re

from playwright.sync_api import Page, expect

from e2e.conftest import Site
from e2e.test_flow import ADMIN_IA, sign_in

ALERT_RED = "#B4422F"  # SITE.colors.accent2, 5.58:1 on white
CONTENT_TAB = "/panel/academia/upiixia?tab=contenido"
SEGMENT_ERROR = "El fin del tramo debe ser mayor que el inicio."

ACCENT2 = """
  () => getComputedStyle(document.querySelector('[data-academy-theme="upiixia"]'))
    .getPropertyValue('--academy-accent-2').trim().toUpperCase()
"""
# WCAG contrast of an element's text color against the first opaque background behind it.
CONTRAST = """
  (el) => {
    const rgb = (c) => (c.match(/[\\d.]+/g) || []).map(Number);
    const lum = ([r, g, b]) => {
      const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    let node = el, bg = null;
    while (node && node.nodeType === 1) {
      const c = rgb(getComputedStyle(node).backgroundColor);
      if (c.length >= 3 && (c.length === 3 || c[3] > 0.95)) { bg = c; break; }
      node = node.parentElement;
    }
    bg = bg || [255, 255, 255];
    const fg = rgb(getComputedStyle(el).color);
    const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
    return { color: getComputedStyle(el).color, ratio: (a + 0.05) / (b + 0.05) };
  }
"""


def _hex_to_rgb(value: str) -> str:
    value = value.lstrip("#")
    return f"rgb({int(value[0:2], 16)}, {int(value[2:4], 16)}, {int(value[4:6], 16)})"


def _open_lesson_form_error(site: Site) -> Page:
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
    return page


def test_accent2_falls_back_to_alert_red(site: Site) -> None:
    sign_in(site, ADMIN_IA, CONTENT_TAB)
    expect(site.page.locator('[data-academy-theme="upiixia"]').first).to_be_attached()
    assert site.page.evaluate(ACCENT2) == ALERT_RED  # noqa: S101 · UpiixIA has no color_accent_2


def test_error_message_is_red_on_upiixia(site: Site) -> None:
    page = _open_lesson_form_error(site)
    dialog = page.get_by_role("dialog", name="Nueva clase")
    message = dialog.get_by_text(SEGMENT_ERROR).first
    result = message.evaluate(CONTRAST)
    assert result["color"] == _hex_to_rgb(ALERT_RED), result  # noqa: S101
    assert result["ratio"] >= 4.5, result  # noqa: S101
    site.shot("theme-alert-error")
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()


def test_accent2_keeps_a_club_color(site: Site) -> None:
    sign_in(site, ADMIN_IA, CONTENT_TAB)
    page = site.page
    token = page.request.post(site.url("/api/auth/refresh"), headers={"X-Requested-With": "fetch"}).json()[
        "access_token"
    ]
    academy_id = page.request.get(site.url("/api/academies/upiixia")).json()["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Requested-With": "fetch"}
    saved = page.request.patch(
        site.url(f"/api/academies/{academy_id}/branding"), headers=headers, data={"color_accent_2": "#7B1FA2"}
    )
    assert saved.ok, saved.text()  # noqa: S101
    try:
        page.goto(site.url(CONTENT_TAB))
        expect(page.locator('[data-academy-theme="upiixia"]').first).to_be_attached()
        assert page.evaluate(ACCENT2) == "#7B1FA2"  # noqa: S101 · a club that sets its own alert keeps it
        assert re.fullmatch(r"#[0-9A-F]{6}", page.evaluate(ACCENT2))  # noqa: S101
    finally:
        page.request.patch(
            site.url(f"/api/academies/{academy_id}/branding"), headers=headers, data={"color_accent_2": None}
        )
