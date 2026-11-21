"""Rich emails in the web composer (UPS-091, spec 004): event block (campus calendar or typed), image block
with upload, Reply-To field. Same server setup as test_mail.py; PUBLIC_BASE_URL points at the e2e server so
uploaded images load inside the preview iframe."""

import io
import re
import socket
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import Page, expect

import e2e.conftest as base
from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in

SUPERADMIN = "superadmin1@upiixsol.dev"
CLUB_ADMIN = "admin.ia@upiixsol.dev"
CLUB_EVENT = "Taller: tu primera red neuronal"  # seed: UpiixIA
GLOBAL_EVENT = "Noche de proyectos UpiixSol"  # seed: global
OTHER_EVENT = "Torneo secreto de otro club"
PREVIEW = "iframe[title='Vista previa del correo']"
ARTIFACTS = Path("e2e/artifacts")
SHOTS = Path(".uak-shots/UPS-091")


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def mail_env() -> Iterator[None]:
    port = _port()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SEED_DEFAULT_PASSWORD", SEED_PASSWORD)
        patch.setenv("MAIL_ENABLED", "true")
        patch.setenv("MAIL_BACKEND", "console")
        patch.setenv("MAIL_BLOCKED_DOMAINS", "blocked.invalid")
        patch.setenv("MAIL_REPLY_TO", "mesa@upiixsol.com")
        patch.setenv("PUBLIC_BASE_URL", f"http://127.0.0.1:{port}")
        patch.setattr(base, "_free_port", lambda: port)  # the server must answer where PUBLIC_BASE_URL says
        yield


@pytest.fixture(scope="module")
def site(mail_env: None, site: Site) -> Site:  # noqa: ARG001 - overrides conftest's `site` with the mail env
    return site


HIDE_TOAST = """
  [...document.querySelectorAll('body *')]
    .filter((el) => el.children.length === 0 && el.textContent.includes('Cambia tu contraseña'))
    .forEach((el) => { let n = el; while (n && getComputedStyle(n).position !== 'fixed') n = n.parentElement; if (n) n.style.display = 'none'; })
"""


def shot(site: Site, step: str, focus=None) -> None:  # noqa: ANN001 - playwright Locator
    """Full-page layout check plus viewport shots for the design review (iframes below the fold are not in
    full-page shots). `focus` is scrolled into view first; the composer overview is saved as 1280/390.png."""
    page = site.page
    size = "1280" if site.name == "desktop" else "390"
    page.evaluate(HIDE_TOAST)
    site.shot(step)
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.wait_for_timeout(1000)
    page.screenshot(path=SHOTS / f"{step}-{size}.png", full_page=True)
    if focus is not None:
        focus.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        page.screenshot(path=SHOTS / f"{step}-focus-{size}.png")


def open_composer(site: Site, email: str = SUPERADMIN) -> Page:
    path = "/admin?tab=correos" if email == SUPERADMIN else "/panel/academia?tab=correos"
    sign_in(site, email, "/")
    page = site.page
    page.goto(site.url(f"{path}&paso=envio"))  # the audience first (last step), then the content (UPS-102)
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    if email == SUPERADMIN:
        page.get_by_role("radio", name="Un club").check()
        page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    else:
        page.get_by_role("radio", name="Mi club").check()
    go(page, "Contenido")
    page.get_by_label("Asunto").fill("Prueba de bloques")
    return page


def go(page: Page, step: str) -> None:
    """Jump to a step through the stepper (state is kept): `Contenido` or `Destinatarios`."""
    page.get_by_role("navigation", name="Pasos del correo").get_by_role("button", name=re.compile(step)).click()


def add_block(page: Page, kind: str):  # noqa: ANN201 - playwright Locator
    items = page.get_by_role("list", name="Bloques del correo").get_by_role("listitem")
    before = items.count()
    page.get_by_role("button", name=f"Agregar {kind}").click()
    expect(items).to_have_count(before + 1)
    return items.nth(before)


def card(page: Page):  # noqa: ANN201
    return page.frame_locator(PREVIEW)


def png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 360), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def test_event_block_from_campus_calendar_shows_card_and_calendar_links(site: Site) -> None:
    page = open_composer(site)
    block = add_block(page, "Evento")
    block.get_by_role("radio", name="Del calendario").check()
    block.get_by_label("Buscar evento").fill("red neuronal")
    expect(block.get_by_role("button", name=re.compile(GLOBAL_EVENT))).to_have_count(0)
    block.get_by_role("button", name=re.compile(CLUB_EVENT)).click()
    expect(block.get_by_role("button", name=re.compile(CLUB_EVENT))).to_have_attribute("aria-pressed", "true")
    expect(card(page).get_by_text(CLUB_EVENT)).to_be_visible(timeout=10_000)
    for label in ("Google Calendar", "Outlook", "Apple / .ics"):
        expect(card(page).get_by_role("link", name=label)).to_be_visible()
    expect(card(page).get_by_role("link", name="Google Calendar")).to_have_attribute(
        "href", re.compile(r"^https://calendar\.google\.com/")
    )
    shot(site, "mail-event-calendar", block)
    page.screenshot(path=SHOTS / f"{'1280' if site.name == 'desktop' else '390'}.png", full_page=True)


def test_event_block_typed_by_hand(site: Site) -> None:
    page = open_composer(site)
    block = add_block(page, "Evento")
    block.get_by_role("radio", name="Escribir evento").check()
    block.get_by_label("Título del evento").fill("Primera clase de robótica")
    block.get_by_label("Inicio").fill("2030-03-05T15:00")
    block.get_by_label("Fin").fill("2030-03-05T17:00")
    block.get_by_label("Lugar").fill("Salón 205")
    block.get_by_label("Descripción del evento").fill("Trae tu laptop.")
    block.get_by_label("Enlace del evento").fill("https://www.upiixsol.com/")
    expect(card(page).get_by_text("Primera clase de robótica")).to_be_visible(timeout=10_000)
    expect(card(page).get_by_text("Salón 205")).to_be_visible()
    # Mexico City time as typed, whatever the browser's zone.
    expect(card(page).get_by_text(re.compile(r"3:00\s*(p\.?\s*m\.?|PM)|15:00"))).to_be_visible()
    expect(card(page).get_by_role("link", name="Apple / .ics")).to_be_visible()
    # An end before the start is said in Spanish and keeps the preview from breaking.
    block.get_by_label("Fin").fill("2030-03-05T14:00")
    expect(block.get_by_text("La hora de fin debe ser posterior a la de inicio.")).to_be_visible()
    block.get_by_label("Fin").fill("2030-03-05T17:00")
    # Only one event per email.
    expect(page.get_by_role("button", name="Agregar Evento")).to_be_disabled()
    shot(site, "mail-event-typed")


def test_image_block_uploads_and_previews(site: Site, tmp_path: Path) -> None:
    page = open_composer(site)
    block = add_block(page, "Imagen")
    notes = tmp_path / "notas.txt"
    notes.write_text("no soy una imagen")
    block.get_by_label("Subir imagen").set_input_files(notes)
    expect(block.get_by_role("alert")).to_contain_text("PNG, JPG o WebP")
    cartel = tmp_path / "cartel.png"
    cartel.write_bytes(png())
    block.get_by_label("Subir imagen").set_input_files(cartel)
    expect(block.get_by_role("img", name="Imagen subida")).to_be_visible(timeout=10_000)
    # Alt text is required: without it the block is unfinished and the send is refused in Spanish.
    page.get_by_label("Texto del párrafo").first.fill("Hola")
    go(page, "Destinatarios")
    page.get_by_role("button", name="Revisar y enviar").click()
    expect(page.get_by_text("Completa o elimina los bloques vacíos.")).to_be_visible()  # sent back to the content step
    block.get_by_label("Texto alternativo de la imagen").fill("Cartel del taller")
    block.get_by_label("Enlace de la imagen (opcional)").fill("https://www.upiixsol.com/a/upiixia")
    image = card(page).get_by_role("img", name="Cartel del taller")
    expect(image).to_be_visible(timeout=10_000)
    expect(card(page).get_by_role("link").filter(has=image)).to_have_attribute("href", "https://www.upiixsol.com/a/upiixia")
    assert image.evaluate("(el) => el.complete && el.naturalWidth > 0")  # noqa: S101 - the upload really loads
    shot(site, "mail-image", block)


def test_reply_to_prefilled_and_editable(site: Site) -> None:
    page = open_composer(site)
    page.get_by_label("Texto del párrafo").first.fill("Hola")
    go(page, "Destinatarios")
    reply = page.get_by_label("Responder a")
    expect(reply).to_have_value("mesa@upiixsol.com")
    reply.fill("no-es-un-correo")
    expect(page.get_by_text("Escribe un correo válido.")).to_be_visible()
    page.get_by_role("button", name="Revisar y enviar").click()
    expect(page.get_by_text("Escribe un correo válido.").first).to_be_visible()
    reply.fill("junta@upiixsol.com")
    expect(page.get_by_text("Escribe un correo válido.")).to_have_count(0)
    expect(card(page).get_by_text("Responde este correo")).to_be_visible(timeout=10_000)
    shot(site, "mail-reply-to", reply)


def test_club_admin_sees_only_global_and_own_club_events(site: Site) -> None:
    page = site.page
    sign_in(site, SUPERADMIN, "/")
    token = page.request.post(
        site.url("/api/auth/login"),
        headers={"X-Requested-With": "fetch"},
        data={"email": SUPERADMIN, "password": SEED_PASSWORD},
    ).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    club = page.request.post(
        site.url("/api/admin/academies"),
        headers=auth,
        data={
            "name": "UpiixOtro",
            "slug": "upiixotro",
            "short_description": "Club de prueba",
            "color_primary": "#1F4FD8",
            "color_secondary": "#0B1F5C",
            "color_accent": "#F2B705",
        },
    )
    assert club.ok, club.text()  # noqa: S101
    created = page.request.post(
        site.url("/api/events"),
        headers=auth,
        data={
            "academy_id": club.json()["id"],
            "title": OTHER_EVENT,
            "starts_at": "2030-01-10T23:00:00Z",
            "ends_at": "2030-01-11T01:00:00Z",
        },
    )
    assert created.ok, created.text()  # noqa: S101
    page = open_composer(site, CLUB_ADMIN)
    block = add_block(page, "Evento")
    block.get_by_role("radio", name="Del calendario").check()
    expect(block.get_by_role("button", name=re.compile(CLUB_EVENT))).to_be_visible()
    expect(block.get_by_role("button", name=re.compile(GLOBAL_EVENT))).to_be_visible()
    expect(block.get_by_role("button", name=re.compile(OTHER_EVENT))).to_have_count(0)
    block.get_by_label("Buscar evento").fill("Torneo")
    expect(block.get_by_text("No hay eventos que coincidan.")).to_be_visible()
    shot(site, "mail-event-club-admin")
