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


# The player marks a lesson complete when the YouTube embed reports "ended" over postMessage (UPS-024).
# The test plays that message from the YouTube origin and from the player's own iframe.
VIDEO_ENDED = """
  () => {
    const frame = document.querySelector('iframe[src*="youtube-nocookie.com/embed/"]');
    window.dispatchEvent(new MessageEvent("message", {
      data: JSON.stringify({ event: "onStateChange", info: 0 }),
      origin: "https://www.youtube-nocookie.com",
      source: frame.contentWindow,
    }));
  }
"""


def test_step3_player_complete_lesson(site: Site) -> None:
    page = site.page
    page.get_by_role("link", name=re.compile(r"Continuar: Clase 3")).click()
    expect(page).to_have_url(re.compile(r"/a/upiixia/clases/\d+"))
    expect(page.get_by_text("Se marca como completada al terminar el video")).to_be_visible()
    page.locator('iframe[src*="youtube-nocookie.com/embed/"]').wait_for(state="attached")
    page.evaluate(VIDEO_ENDED.replace("https://www.youtube-nocookie.com", "https://evil.example"))
    page.wait_for_timeout(300)
    expect(page.get_by_text("Se marca como completada al terminar el video")).to_be_visible()  # ignored
    page.evaluate(VIDEO_ENDED)
    expect(page.get_by_text("Clase completada").first).to_be_visible()
    page.reload()  # the progress persists
    if site.name == "mobile":  # the route sidebar lives in a drawer on phones
        page.get_by_role("button", name="Contenido").click()
    expect(page.get_by_role("progressbar").first).to_have_attribute("aria-valuenow", "75")
    site.shot("3-player")


def test_step4_community_post_with_image(site: Site) -> None:
    page = site.page
    text = f"Hallazgo e2e {site.name}: una red neuronal aprende XOR"
    page.goto(site.url("/comunidad?canal=upiixia"))
    page.get_by_label("Escribe en #upiixia").fill(text)
    page.locator('input[type="file"][name="image"]').set_input_files(
        files=[{"name": "hallazgo.png", "mimeType": "image/png", "buffer": _png_bytes()}]
    )
    page.get_by_role("button", name="Publicar").click()
    post = page.locator("article", has_text=text)
    expect(post).to_be_visible()
    expect(post.locator("img[src^='/media/']")).to_be_visible()
    site.shot("4-community")
    page.goto(site.url("/comunidad?canal=feed"))
    expect(page.locator("article", has_text=text)).to_be_visible()


def test_step5_academy_admin_adds_lesson_and_changes_accent(site: Site) -> None:
    sign_in(site, ADMIN_IA, "/panel/academia/upiixia")
    page = site.page
    module_title = f"Módulo e2e {site.name}"
    lesson_title = f"Clase e2e {site.name}"
    page.goto(site.url("/panel/academia/upiixia?tab=contenido"))
    page.get_by_role("button", name="Agregar módulo").first.click()
    page.get_by_label("Título del nuevo módulo").fill(module_title)
    page.get_by_role("dialog").get_by_role("button", name="Guardar").click()
    module = page.locator("li", has_text=module_title).first
    expect(module).to_be_visible()
    module.get_by_role("button", name="Agregar clase").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Título de la clase").fill(lesson_title)
    dialog.get_by_label("URL de YouTube").fill("https://youtu.be/aircAruvnKk")
    dialog.get_by_label("Descripción (markdown)").fill("Repaso de **redes neuronales**.")
    for i, (label, url) in enumerate(
        [("Notas", "https://upiixsol.dev/notas"), ("Ejercicios", "https://upiixsol.dev/ejercicios")], start=1
    ):
        dialog.get_by_role("button", name="Agregar link").click()
        dialog.get_by_label(f"Etiqueta del link {i}").fill(label)
        dialog.get_by_label(f"URL del link {i}").fill(url)
    dialog.get_by_role("button", name="Agregar clase").click()
    expect(page.get_by_text(lesson_title)).to_be_visible()

    page.goto(site.url("/panel/academia/upiixia?tab=identidad"))
    page.get_by_label("Acento", exact=True).fill("#FFB400")
    page.get_by_role("button", name="Guardar identidad").click()
    expect(page.get_by_text("Identidad guardada")).to_be_visible()
    site.shot("5-panel")

    # The new lesson shows in the player's sidebar and the academy uses the new accent.
    page.goto(site.url("/a/upiixia/rutas"))
    page.locator('main a[href^="/a/upiixia/rutas/"]').first.click()  # same first route as in the panel
    if site.name == "mobile":
        page.get_by_role("button", name="Contenido").click()
    sidebar = page.get_by_role("navigation", name="Contenido de la ruta")
    sidebar.get_by_placeholder("Buscar por el título de la lección").fill(lesson_title)  # opens its module
    expect(sidebar.get_by_text(lesson_title)).to_be_visible()
    assert page.evaluate(THEMED_ACCENT).strip().upper() == "#FFB400"  # noqa: S101


def test_step6_superadmin_creates_academy_admin_and_global_event(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/admin")
    page = site.page
    event_title = f"Noche de robótica e2e {site.name}"

    page.goto(site.url("/admin?tab=academias"))
    page.get_by_role("button", name="Nuevo club").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Nombre", exact=True).fill("UpiixRobótica")
    dialog.get_by_label("Identificador (slug)").fill("upiixrobotica")
    dialog.get_by_label("Descripción corta").fill("Robots, sensores y competencias.")
    dialog.get_by_label("Acento", exact=True).fill("#ff6b00")
    dialog.locator('input[type="file"][name="logo"]').set_input_files(
        files=[{"name": "logo.png", "mimeType": "image/png", "buffer": _png_bytes()}]
    )
    dialog.get_by_role("button", name="Crear club").click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_text("UpiixRobótica").first).to_be_visible()

    page.goto(site.url("/admin?tab=usuarios"))
    page.get_by_role("button", name="Nuevo usuario").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Rol").select_option("academy_admin")
    dialog.get_by_label("Club").select_option(label="UpiixRobótica")
    dialog.get_by_label("Nombre completo").fill("Rocío Robótica")
    dialog.get_by_label("Correo").fill("admin.robotica@upiixsol.dev")
    dialog.get_by_label("Contraseña temporal").fill("temporal-robot-1")
    dialog.get_by_role("button", name="Crear usuario").click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_text("admin.robotica@upiixsol.dev")).to_be_visible()

    page.goto(site.url("/calendario?vista=lista"))
    page.get_by_role("button", name="Nuevo evento").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Título").fill(event_title)
    dialog.get_by_label("Academia").select_option("")  # global event
    dialog.get_by_label("Lugar").fill("UPIIZ · Auditorio")
    dialog.get_by_role("button", name="Publicar evento").click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_text(event_title)).to_be_visible()
    site.shot("6-calendar")

    # The academy shows on the campus home and its channel exists in the community.
    page.goto(site.url("/"))
    expect(page.get_by_role("link", name="Entrar a UpiixRobótica")).to_be_visible()
    page.goto(site.url("/comunidad"))
    expect(page.get_by_role("complementary", name="Canales").get_by_text("upiixrobotica")).to_be_visible()
    site.shot("6-home-community")
