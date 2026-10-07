"""Acceptance flow, steps 1–6 (IDEA §4), in a real browser. Tests run in order and share one site per
viewport: each step starts from the state the previous one left."""

import io
import re

from PIL import Image
from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site

MEMBER = "alumno.demo@upiixsol.dev"
ADMIN_IA = "admin.ia@upiixsol.dev"
SUPERADMIN = "superadmin1@upiixsol.dev"
# --academy-accent of the outermost themed wrapper (AcademyTheme sets it inline; cards inside are themed too).
THEMED_ACCENT = """
  [...document.querySelectorAll('[style*="--academy-accent"]')].map((el) =>
    getComputedStyle(el).getPropertyValue('--academy-accent'))[0]
  ?? getComputedStyle(document.documentElement).getPropertyValue('--academy-accent')
"""


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (320, 200), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def sign_out(page: Page) -> None:
    """Drops the session: the access token lives in memory and the refresh token in a cookie."""
    page.context.clear_cookies()
    page.goto("about:blank")


def sign_in(site: Site, email: str, path: str = "/") -> None:
    sign_out(site.page)
    page = site.page
    page.goto(site.url(f"/login?next={path}"))
    page.get_by_role("textbox", name="Correo", exact=True).fill(email)
    page.get_by_label("Contraseña", exact=True).fill(SEED_PASSWORD)
    page.get_by_role("button", name="Entrar").click()
    expect(page).not_to_have_url(re.compile(r"/login"))


def test_step1_register_and_campus_home(site: Site) -> None:
    page = site.page
    page.goto(site.url("/login"))
    page.get_by_role("tab", name="Crear cuenta").click()
    page.get_by_label("Nombre completo").fill("Ana Prueba Pérez")
    page.get_by_label("Número de boleta").fill("2026999001" if site.name == "desktop" else "2026999002")
    page.get_by_role("textbox", name="Correo", exact=True).fill(f"ana.{site.name}@upiixsol.dev")
    page.get_by_label("Contraseña", exact=True).fill("una-clave-segura")
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Crear cuenta").last.click()
    expect(page).to_have_url(site.url("/"))
    expect(page.get_by_role("link", name="Entrar a UpiixIA")).to_be_visible()
    site.shot("1-home")


def test_step2_academy_retheme_and_continue(site: Site) -> None:
    sign_in(site, MEMBER)
    page = site.page
    campus_accent = page.evaluate(THEMED_ACCENT)
    page.get_by_role("link", name="Entrar a UpiixIA").click()
    expect(page).to_have_url(site.url("/a/upiixia"))
    continue_link = page.get_by_role("link", name=re.compile(r"Continuar: Clase 3 · 50 %"))
    expect(continue_link).to_be_visible()
    academy_accent = page.evaluate(THEMED_ACCENT)
    # Campus orange → UpiixIA lime green, and the header shows the UpiixIA logo.
    assert academy_accent.strip().upper() == "#7ED957" != campus_accent.strip().upper()  # noqa: S101
    expect(page.get_by_role("banner").get_by_role("img", name="UpiixIA")).to_be_visible()
    site.shot("2-academy-home")


def test_step3_player_complete_lesson(site: Site) -> None:
    page = site.page
    page.get_by_role("link", name=re.compile(r"Continuar: Clase 3")).click()
    expect(page).to_have_url(re.compile(r"/a/upiixia/clases/\d+"))
    complete = page.get_by_role("button", name="Marcar como completada")
    expect(complete).to_be_visible()
    lesson_url = page.url
    complete.click()
    # Completing jumps to the next lesson; the progress persists after a reload.
    expect(page).not_to_have_url(lesson_url)
    page.reload()
    if site.name == "mobile":  # the route sidebar lives in a drawer on phones
        page.get_by_role("button", name="Contenido").click()
    expect(page.get_by_role("progressbar").first).to_have_attribute("aria-valuenow", "75")
    site.shot("3-player")
