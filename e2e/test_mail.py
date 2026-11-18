"""Superadmin "Correos" tab (UPS-078, UPS-090): audience picker, block composer with live preview, confirm
modal, disabled notice and history. The server runs with the console backend (no Mailgun) and the seed's own domain unblocked."""

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in

SUPERADMIN = "superadmin1@upiixsol.dev"
CLUB_SUBJECT = "Junta semanal de UpiixIA"
MIX_SUBJECT = "Aviso para invitados"
OUTSIDE = "invitado@example.com"


@pytest.fixture(scope="module")
def mail_env() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SEED_DEFAULT_PASSWORD", SEED_PASSWORD)  # the local .env may set another one
        patch.setenv("MAIL_ENABLED", "true")
        patch.setenv("MAIL_BACKEND", "console")
        patch.setenv("MAIL_BLOCKED_DOMAINS", "blocked.invalid")  # the seed accounts are @upiixsol.dev
        yield


@pytest.fixture(scope="module")
def site(mail_env: None, site: Site) -> Site:  # noqa: ARG001 - overrides conftest's `site` with mail enabled
    return site


def open_mail(site: Site) -> Page:
    sign_in(site, SUPERADMIN, "/admin?tab=correos")
    page = site.page
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    return page


BODY = "Hola, esta semana nos vemos el viernes.\n\nhttps://upiixsol.com"
PREVIEW = "iframe[title='Vista previa del correo']"


def compose(page: Page, subject: str, body: str = BODY) -> None:
    """Subject plus the composer's first (paragraph) block."""
    page.get_by_label("Asunto").fill(subject)
    page.get_by_label("Texto del párrafo").first.fill(body)


def blocks(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("list", name="Bloques del correo").get_by_role("listitem")


def review_and_confirm(page: Page, people: str) -> None:
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_text(re.compile(rf"Se enviará a {people}"))).to_be_visible()
    expect(dialog.get_by_text(re.compile(r"Te quedan [\d,]+ de [\d,]+ correos este mes"))).to_be_visible()
    dialog.get_by_role("button", name="Enviar ahora").click()
    expect(dialog).to_be_hidden()


def test_superadmin_sends_to_a_club_after_preview_and_confirm(site: Site) -> None:
    page = open_mail(site)
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    compose(page, CLUB_SUBJECT)
    expect(page.frame_locator(PREVIEW).get_by_text("Hola, esta semana")).to_be_visible(timeout=10_000)
    site.shot("mail-composer")
    review_and_confirm(page, r"\d+ personas?")
    history = page.get_by_role("region", name="Historial")
    expect(history.get_by_text(CLUB_SUBJECT)).to_be_visible()
    site.shot("mail-sent")


def test_superadmin_mixes_users_and_outside_addresses(site: Site) -> None:
    page = open_mail(site)
    page.get_by_role("radio", name="Personas").check()
    expect(page.get_by_text("Personas 0/50")).to_be_visible()
    expect(page.get_by_text("Correos externos 0/20")).to_be_visible()
    page.get_by_label("Buscar personas por nombre o apodo").fill("alumno")
    page.get_by_role("button", name="Agregar Alumno Demo").click()
    expect(page.get_by_text("Personas 1/50")).to_be_visible()
    expect(page.get_by_role("button", name="Quitar a Alumno Demo")).to_be_visible()
    page.get_by_label("Correo externo").fill("no-es-un-correo")
    page.get_by_role("button", name="Agregar correo").click()
    expect(page.get_by_text("Escribe un correo válido.")).to_be_visible()
    page.get_by_label("Correo externo").fill(OUTSIDE)
    page.get_by_role("button", name="Agregar correo").click()
    expect(page.get_by_text("Correos externos 1/20")).to_be_visible()
    expect(page.get_by_role("button", name=f"Quitar {OUTSIDE}")).to_be_visible()
    compose(page, MIX_SUBJECT)
    site.shot("mail-individual")
    review_and_confirm(page, "2 personas")
    expect(page.get_by_role("region", name="Historial").get_by_text(MIX_SUBJECT)).to_be_visible()


def test_composer_builds_title_paragraph_button_and_previews(site: Site) -> None:
    page = open_mail(site)
    page.get_by_label("Asunto").fill("Primera clase")
    page.get_by_role("button", name="Agregar Título").click()
    page.get_by_label("Texto del título").fill("Bienvenidos a la primera clase")
    page.get_by_label("Texto del párrafo").first.fill("Trae tu **laptop** al salón 205.")
    page.get_by_role("button", name="Agregar Botón").click()
    page.get_by_role("button", name="Ir al campus").click()
    frame = page.frame_locator(PREVIEW)
    expect(frame.get_by_text("Bienvenidos a la primera clase")).to_be_visible(timeout=10_000)
    expect(frame.locator("strong", has_text="laptop")).to_be_visible()
    expect(frame.get_by_role("link", name="Ir al campus").first).to_be_visible()
    site.shot("mail-blocks-preview")


def test_preview_iframe_is_sandboxed(site: Site) -> None:
    page = open_mail(site)
    compose(page, "Aviso", "Hola <script>alert(1)</script>")  # shown as text, never run
    frame = page.locator(PREVIEW)
    expect(frame).to_have_attribute("sandbox", "")
    expect(frame).to_have_attribute("srcdoc", re.compile(r"<html|<!DOCTYPE", re.IGNORECASE), timeout=10_000)
    expect(page.frame_locator(PREVIEW).get_by_text("alert(1)")).to_be_visible()


def test_preview_switches_desktop_and_phone(site: Site) -> None:
    page = open_mail(site)
    compose(page, "Aviso")
    frame = page.locator(PREVIEW)
    desktop = page.get_by_role("button", name="Escritorio")
    phone = page.get_by_role("button", name="Teléfono")
    desktop.click()
    expect(desktop).to_have_attribute("aria-pressed", "true")
    expect(frame).to_have_css("width", "600px")
    phone.click()
    expect(phone).to_have_attribute("aria-pressed", "true")
    expect(frame).to_have_css("width", "375px")
    site.shot("mail-preview-phone")


def test_blocks_reorder_and_delete(site: Site) -> None:
    page = open_mail(site)
    expect(blocks(page)).to_have_count(1)
    page.get_by_role("button", name="Agregar Título").click()
    page.get_by_role("button", name="Agregar Separador").click()
    expect(blocks(page)).to_have_count(3)
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Párrafo")
    expect(blocks(page).nth(1)).to_have_attribute("aria-label", "Bloque 2: Título")
    expect(blocks(page).nth(0).get_by_role("button", name="Mover arriba")).to_be_disabled()
    expect(blocks(page).nth(2).get_by_role("button", name="Mover abajo")).to_be_disabled()
    blocks(page).nth(1).get_by_role("button", name="Mover arriba").click()
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Título")
    expect(blocks(page).nth(1)).to_have_attribute("aria-label", "Bloque 2: Párrafo")
    blocks(page).nth(0).get_by_role("button", name="Mover abajo").click()
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Párrafo")
    blocks(page).nth(2).get_by_role("button", name="Eliminar bloque").click()
    blocks(page).nth(0).get_by_role("button", name="Eliminar bloque").click()
    expect(blocks(page)).to_have_count(1)
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Título")
    # Event and image blocks arrive with UPS-091: offered, not usable yet.
    expect(page.get_by_role("button", name="Agregar Evento")).to_be_disabled()
    expect(page.get_by_role("button", name="Agregar Imagen")).to_be_disabled()


def test_button_presets_campus_and_club(site: Site) -> None:
    page = open_mail(site)
    page.get_by_role("button", name="Agregar Botón").click()
    button = blocks(page).nth(1)
    expect(button.get_by_role("button", name="Ver el club")).to_be_disabled()  # no club chosen yet
    button.get_by_role("button", name="Ir al campus").click()
    expect(button.get_by_label("Texto del botón")).to_have_value("Ir al campus")
    expect(button.get_by_label("Enlace del botón")).to_have_value("https://www.upiixsol.com/")
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    button.get_by_role("button", name="Ver el club").click()
    expect(button.get_by_label("Texto del botón")).to_have_value("Ver el club")
    expect(button.get_by_label("Enlace del botón")).to_have_value("https://www.upiixsol.com/a/upiixia")


def test_sender_selector_for_superadmin_and_fixed_for_club_admin(site: Site) -> None:
    page = open_mail(site)
    sender = page.get_by_label("Enviado por")
    expect(sender).to_have_value("")  # the board
    expect(sender.locator("option", has_text="UpiixIA")).to_have_count(1)
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    expect(sender.locator("option:checked")).to_have_text("UpiixIA")  # follows the audience's club
    compose(page, "Aviso del club")
    expect(page.frame_locator(PREVIEW).get_by_text("UpiixIA").first).to_be_visible(timeout=10_000)
    page.get_by_role("radio", name="Todo UpiixSol").check()
    expect(sender.locator("option:checked")).to_have_text("La mesa directiva de UpiixSol")
    expect(page.frame_locator(PREVIEW).get_by_text("mesa directiva de UpiixSol").first).to_be_visible(timeout=10_000)
    sender.select_option(label="UpiixIA")
    expect(page.frame_locator(PREVIEW).get_by_text("UpiixIA").first).to_be_visible(timeout=10_000)
    site.shot("mail-sender")


def test_no_test_send_button(site: Site) -> None:
    page = open_mail(site)
    expect(page.get_by_role("button", name="Revisar y enviar")).to_be_visible()
    expect(page.get_by_role("button", name="Enviarme una prueba")).to_have_count(0)


def test_composer_at_390_wide(site: Site) -> None:
    page = open_mail(site)
    compose(page, "Revisión de pantalla")
    page.get_by_role("button", name="Agregar Título").click()
    page.get_by_role("button", name="Agregar Botón").click()
    page.get_by_role("button", name="Agregar Separador").click()
    editor = page.get_by_role("list", name="Bloques del correo").bounding_box()
    preview = page.locator(PREVIEW).bounding_box()
    assert editor and preview
    if site.name == "mobile":
        assert preview["y"] >= editor["y"] + editor["height"] - 1  # below the editor on phones
    else:
        assert preview["x"] >= editor["x"] + editor["width"] - 1  # beside the editor on desktop
    expect(page.frame_locator(PREVIEW).get_by_text("Hola, esta semana")).to_be_visible(timeout=10_000)
    site.shot("mail-composer-blocks")


def test_mail_disabled_shows_the_notice(site: Site) -> None:
    page = site.page
    status = {
        "enabled": False,
        "monthly_limit": 3000,
        "sent_this_period": 0,
        "remaining": 3000,
        "period_start": "2026-11-01T00:00:00Z",
        "period_end": "2026-12-01T00:00:00Z",
    }
    page.route("**/api/mail/status", lambda route: route.fulfill(json=status))
    page.goto(site.url("/admin?tab=correos"))
    expect(page.get_by_text("El correo está desactivado")).to_be_visible()
    expect(page.get_by_role("button", name="Revisar y enviar")).to_be_disabled()
    site.shot("mail-disabled")
    page.unroute("**/api/mail/status")


def test_history_lists_the_campaign_with_counts(site: Site) -> None:
    page = open_mail(site)
    row = page.get_by_role("region", name="Historial").get_by_role("listitem").filter(has_text=CLUB_SUBJECT)
    expect(row).to_have_count(1)
    expect(row.get_by_text("Un club")).to_be_visible()
    expect(row).not_to_contain_text("undefined")
    expect(row.get_by_text("superadmin1")).to_be_visible()
    expect(row.get_by_text(re.compile(r"Enviado|Enviando"))).to_be_visible()
    expect(row.get_by_text(re.compile(r"\d+ (aceptados?|entregados?|pendientes?)"))).to_be_visible()
    mixed = page.get_by_role("region", name="Historial").get_by_role("listitem").filter(has_text=MIX_SUBJECT)
    expect(mixed.get_by_text("Personas")).to_be_visible()
    expect(mixed).to_contain_text("1 externo")
    expect(mixed).not_to_contain_text("undefined")
    site.shot("mail-history")


def test_mail_tab_at_390_wide(site: Site) -> None:
    page = open_mail(site)
    expect(page.get_by_role("tab", name="Correos")).to_be_visible()
    for name in ("Todo UpiixSol", "Un club", "Un rol", "Personas"):
        expect(page.get_by_role("radio", name=name)).to_be_visible()
    compose(page, "Revisión de pantalla")
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_text(re.compile(r"Se enviará a"))).to_be_visible()
    expect(dialog.get_by_role("button", name="Enviar ahora")).to_be_visible()
    page.wait_for_timeout(500)  # the modal finishes opening before the shot
    site.shot("mail-modal")
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()
