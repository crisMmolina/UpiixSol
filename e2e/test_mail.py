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


def open_mail(site: Site, step: str = "contenido") -> Page:
    """The "Correos" tab at a composer step (UPS-102): `contenido` has the subject and blocks, `envio` the audience."""
    sign_in(site, SUPERADMIN, "/")
    page = site.page
    page.goto(site.url(f"/admin?tab=correos&paso={step}"))
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    return page


def go(page: Page, step: str) -> None:
    """Jump to a step through the stepper (state is kept): `Contenido` or `Destinatarios`."""
    page.get_by_role("navigation", name="Pasos del correo").get_by_role("button", name=re.compile(step)).click()


BODY = "Hola, esta semana nos vemos el viernes.\n\nhttps://upiixsol.com"
PREVIEW = "iframe[title='Vista previa del correo']"


def compose(page: Page, subject: str, body: str = BODY) -> None:
    """Subject plus the composer's first (paragraph) block."""
    page.get_by_label("Asunto").fill(subject)
    page.get_by_label("Texto del párrafo").first.fill(body)


def preview_view(site: Site, step: str) -> None:
    """Viewport shot of the preview once its images are in (full-page shots do not paint iframes below the fold)."""
    page = site.page
    page.locator(PREVIEW).scroll_into_view_if_needed()
    page.wait_for_timeout(1200)
    page.screenshot(path=f"e2e/artifacts/view-{site.name}-{step}.png")


def blocks(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("list", name="Bloques del correo").get_by_role("listitem")


def properties(page: Page):  # noqa: ANN201 - playwright Locator
    """The selected button/event/image's fields (UPS-103): side panel on desktop, bottom sheet on phones."""
    return page.get_by_label("Propiedades del bloque")


def add_block(page: Page, kind: str) -> None:
    """The canvas "+" at the end of the email (UPS-103), closing a phone's bottom sheet first."""
    close = page.get_by_role("button", name="Cerrar propiedades")
    if page.viewport_size and page.viewport_size["width"] < 1024 and close.count():
        close.click()
    page.get_by_role("button", name="Agregar bloque al final").click()
    page.get_by_role("menu", name="Tipo de bloque").get_by_role("menuitem", name=kind, exact=True).click()


def see_as_sent(page: Page) -> None:
    """Step 2's exact server render is behind "Ver como llega" (UPS-103)."""
    page.get_by_role("button", name="Ver como llega").click()
    expect(page.get_by_role("dialog", name="Así llega el correo")).to_be_visible()


def close_preview(page: Page) -> None:
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog", name="Así llega el correo")).to_have_count(0)


def review_and_confirm(page: Page, people: str) -> None:
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_text(re.compile(rf"Se enviará a {people}"))).to_be_visible()
    expect(dialog.get_by_text(re.compile(r"Te quedan [\d,]+ de [\d,]+ correos este mes"))).to_be_visible()
    dialog.get_by_role("button", name="Enviar ahora").click()
    expect(dialog).to_be_hidden()


def test_superadmin_sends_to_a_club_after_preview_and_confirm(site: Site) -> None:
    page = open_mail(site, "envio")
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    go(page, "Contenido")
    compose(page, CLUB_SUBJECT)
    see_as_sent(page)
    expect(page.frame_locator(PREVIEW).get_by_text("Hola, esta semana")).to_be_visible(timeout=10_000)
    site.shot("mail-composer")
    close_preview(page)
    go(page, "Destinatarios")
    review_and_confirm(page, r"\d+ personas?")
    history = page.get_by_role("region", name="Historial")
    expect(history.get_by_text(CLUB_SUBJECT)).to_be_visible()
    site.shot("mail-sent")


def test_superadmin_mixes_users_and_outside_addresses(site: Site) -> None:
    page = open_mail(site, "envio")
    page.get_by_role("radio", name="Personas").check()
    expect(page.get_by_text("Personas 0/50")).to_be_visible()
    expect(page.get_by_text("Correos externos 0")).to_be_visible()
    page.get_by_label("Buscar personas por nombre o apodo").fill("alumno")
    page.get_by_role("button", name="Agregar Alumno Demo").click()
    expect(page.get_by_text("Personas 1/50")).to_be_visible()
    expect(page.get_by_role("button", name="Quitar a Alumno Demo")).to_be_visible()
    page.get_by_label("Correo externo").fill("no-es-un-correo")
    page.get_by_role("button", name="Agregar correo").click()
    expect(page.get_by_text("Escribe un correo válido.")).to_be_visible()
    page.get_by_label("Correo externo").fill(OUTSIDE)
    page.get_by_role("button", name="Agregar correo").click()
    expect(page.get_by_text("Correos externos 1")).to_be_visible()
    expect(page.get_by_role("button", name=f"Quitar {OUTSIDE}")).to_be_visible()
    go(page, "Contenido")
    compose(page, MIX_SUBJECT)
    go(page, "Destinatarios")
    site.shot("mail-individual")
    review_and_confirm(page, "2 personas")
    expect(page.get_by_role("region", name="Historial").get_by_text(MIX_SUBJECT)).to_be_visible()


def test_composer_builds_title_paragraph_button_and_previews(site: Site) -> None:
    page = open_mail(site)
    page.get_by_label("Asunto").fill("Primera clase")
    add_block(page, "Título")
    page.get_by_label("Texto del título").fill("Bienvenidos a la primera clase")
    page.get_by_label("Texto del párrafo").first.fill("Trae tu **laptop** al salón 205.")
    add_block(page, "Botón")
    properties(page).get_by_role("button", name="Ir al campus").click()
    see_as_sent(page)
    frame = page.frame_locator(PREVIEW)
    expect(frame.get_by_text("Bienvenidos a la primera clase")).to_be_visible(timeout=10_000)
    expect(frame.locator("strong", has_text="laptop")).to_be_visible()
    expect(frame.get_by_role("link", name="Ir al campus").first).to_be_visible()
    site.shot("mail-blocks-preview")
    preview_view(site, "mail-blocks-preview")


def test_preview_iframe_is_sandboxed(site: Site) -> None:
    page = open_mail(site)
    compose(page, "Aviso", "Hola <script>alert(1)</script>")  # shown as text, never run
    see_as_sent(page)
    frame = page.locator(PREVIEW)
    expect(frame).to_have_attribute("sandbox", "allow-same-origin")  # UPS-091: no allow-scripts, so no code runs; same-origin only lets the page fit the height
    expect(frame).to_have_attribute("srcdoc", re.compile(r"<html|<!DOCTYPE", re.IGNORECASE), timeout=10_000)
    expect(page.frame_locator(PREVIEW).get_by_text("alert(1)")).to_be_visible()


def test_preview_switches_desktop_and_phone(site: Site) -> None:
    page = open_mail(site)
    compose(page, "Aviso")
    see_as_sent(page)
    frame = page.locator(PREVIEW)
    desktop = page.get_by_role("button", name="Escritorio")
    phone = page.get_by_role("button", name="Teléfono")
    desktop.click()
    expect(desktop).to_have_attribute("aria-pressed", "true")
    expect(frame).to_have_css("max-width", "100%")  # 600 px, shrunk to fit a narrow column, never scrolls the page
    wide = frame.evaluate("el => el.getBoundingClientRect().width")
    assert 280 <= wide <= 600
    phone.click()
    expect(phone).to_have_attribute("aria-pressed", "true")
    expect(frame).to_have_css("max-width", "100%")
    if site.name == "desktop":
        expect(frame).to_have_css("width", "375px")
    else:
        page.wait_for_function("document.querySelector('iframe').getBoundingClientRect().width <= 375")
    site.shot("mail-preview-phone")


def test_blocks_reorder_and_delete(site: Site) -> None:
    page = open_mail(site)
    expect(blocks(page)).to_have_count(1)
    add_block(page, "Título")
    add_block(page, "Separador")
    expect(blocks(page)).to_have_count(3)
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Párrafo")
    expect(blocks(page).nth(1)).to_have_attribute("aria-label", "Bloque 2: Título")
    # The move buttons are on the selected block's toolbar (UPS-103): click a block to select it. The toolbar floats
    # over the block above, so leave the selected one first (as clicking anywhere else does).
    leave = page.get_by_label("Asunto").focus
    leave()
    blocks(page).nth(0).click()
    expect(blocks(page).nth(0).get_by_role("button", name="Mover arriba")).to_be_disabled()
    blocks(page).nth(2).click()
    expect(blocks(page).nth(2).get_by_role("button", name="Mover abajo")).to_be_disabled()
    leave()
    blocks(page).nth(1).click()
    blocks(page).nth(1).get_by_role("button", name="Mover arriba").click()
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Título")
    expect(blocks(page).nth(1)).to_have_attribute("aria-label", "Bloque 2: Párrafo")
    blocks(page).nth(0).get_by_role("button", name="Mover abajo").click()  # the moved block stays selected
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Párrafo")
    blocks(page).nth(2).click()
    blocks(page).nth(2).get_by_role("button", name="Eliminar bloque").click()
    leave()
    blocks(page).nth(0).click()
    blocks(page).nth(0).get_by_role("button", name="Eliminar bloque").click()
    expect(blocks(page)).to_have_count(1)
    expect(blocks(page).nth(0)).to_have_attribute("aria-label", "Bloque 1: Título")
    # Event and image blocks (UPS-091) are offered by the "+" inserter.
    page.get_by_role("button", name="Agregar bloque al final").click()
    expect(page.get_by_role("menuitem", name="Evento", exact=True)).to_be_enabled()  # UPS-091
    expect(page.get_by_role("menuitem", name="Imagen", exact=True)).to_be_enabled()  # UPS-091
    page.keyboard.press("Escape")


def test_button_presets_campus_and_club(site: Site) -> None:
    page = open_mail(site)
    add_block(page, "Botón")
    button = properties(page)  # UPS-103: the button's fields are in the properties panel
    expect(button.get_by_role("button", name="Ver el club")).to_be_disabled()  # no club chosen yet
    button.get_by_role("button", name="Ir al campus").click()
    expect(button.get_by_label("Texto del botón")).to_have_value("Ir al campus")
    expect(button.get_by_label("Enlace del botón")).to_have_value("https://www.upiixsol.com/")
    go(page, "Destinatarios")
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    go(page, "Contenido")
    blocks(page).nth(1).click()  # select the button again to open its properties
    button.get_by_role("button", name="Ver el club").click()
    expect(button.get_by_label("Texto del botón")).to_have_value("Ver el club")
    expect(button.get_by_label("Enlace del botón")).to_have_value("https://www.upiixsol.com/a/upiixia")


def test_sender_selector_for_superadmin_and_fixed_for_club_admin(site: Site) -> None:
    page = open_mail(site)
    compose(page, "Aviso del club")  # the preview needs content; the sender lives in the last step
    go(page, "Destinatarios")
    sender = page.get_by_label("Enviado por")
    expect(sender).to_have_value("")  # the board
    expect(sender.locator("option", has_text="UpiixIA")).to_have_count(1)
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    expect(sender.locator("option:checked")).to_have_text("UpiixIA")  # follows the audience's club
    expect(page.frame_locator(PREVIEW).get_by_text("UpiixIA").first).to_be_visible(timeout=10_000)
    page.get_by_role("radio", name="Todo UpiixSol").check()
    expect(sender.locator("option:checked")).to_have_text("La mesa directiva de UpiixSol")
    expect(page.frame_locator(PREVIEW).get_by_text("mesa directiva de UpiixSol").first).to_be_visible(timeout=10_000)
    sender.select_option(label="UpiixIA")
    expect(page.frame_locator(PREVIEW).get_by_text("UpiixIA").first).to_be_visible(timeout=10_000)
    site.shot("mail-sender")
    preview_view(site, "mail-sender")


def test_no_test_send_button(site: Site) -> None:
    page = open_mail(site, "envio")
    expect(page.get_by_role("button", name="Revisar y enviar")).to_be_visible()
    expect(page.get_by_role("button", name="Enviarme una prueba")).to_have_count(0)


def test_composer_at_390_wide(site: Site) -> None:
    page = open_mail(site)
    compose(page, "Revisión de pantalla")
    add_block(page, "Título")
    add_block(page, "Botón")
    editor = page.get_by_role("list", name="Bloques del correo").bounding_box()
    panel = properties(page).bounding_box()
    assert editor and panel
    if site.name == "mobile":
        assert panel["y"] + panel["height"] >= (page.viewport_size or {"height": 0})["height"] - 2  # a bottom sheet on phones
    else:
        assert panel["x"] >= editor["x"] + editor["width"] - 1  # beside the email on desktop
    add_block(page, "Separador")
    see_as_sent(page)
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
    page.goto(site.url("/admin?tab=correos&paso=envio"))
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
    page = open_mail(site, "envio")
    expect(page.get_by_role("tab", name="Correos")).to_be_visible()
    for name in ("Todo UpiixSol", "Un club", "Un rol", "Personas"):
        expect(page.get_by_role("radio", name=name)).to_be_visible()
    go(page, "Contenido")
    compose(page, "Revisión de pantalla")
    go(page, "Destinatarios")
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_text(re.compile(r"Se enviará a"))).to_be_visible()
    expect(dialog.get_by_role("button", name="Enviar ahora")).to_be_visible()
    page.wait_for_timeout(500)  # the modal finishes opening before the shot
    site.shot("mail-modal")
    dialog.get_by_role("button", name="Cancelar").click()
    expect(dialog).to_be_hidden()
