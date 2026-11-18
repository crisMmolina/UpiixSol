"""Club "Correos" tab, the Mi cuenta switch and the public /baja page (UPS-079, spec 003 §Stories, §Opt-out).
Same server setup as test_mail.py: console backend, the seed's own domain unblocked."""

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in

CLUB_ADMIN = "admin.ia@upiixsol.dev"
MEMBER = "alumno.demo@upiixsol.dev"
SUBJECT = "Junta de UpiixIA del viernes"
BODY = "Hola, nos vemos el viernes.\n\nhttps://upiixsol.com"
GONE = "Listo, ya no recibirás correos del club"


@pytest.fixture(scope="module")
def mail_env() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SEED_DEFAULT_PASSWORD", SEED_PASSWORD)
        patch.setenv("MAIL_ENABLED", "true")
        patch.setenv("MAIL_BACKEND", "console")
        patch.setenv("MAIL_BLOCKED_DOMAINS", "blocked.invalid")
        yield


@pytest.fixture(scope="module")
def site(mail_env: None, site: Site) -> Site:  # noqa: ARG001 - overrides conftest's `site` with mail enabled
    return site


def view(site: Site, step: str) -> None:
    """Viewport-sized shot (what a person sees, fixed bars and modal included), for the design review."""
    site.page.wait_for_timeout(600)  # let the modal and height animations settle
    site.page.screenshot(path=f"e2e/artifacts/view-{site.name}-{step}.png")


def open_club_mail(site: Site) -> Page:
    sign_in(site, CLUB_ADMIN, "/panel/academia?tab=correos")
    page = site.page
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    return page


def test_club_admin_mails_their_club_only(site: Site) -> None:
    page = open_club_mail(site)
    expect(page.get_by_role("radio", name="Mi club")).to_be_visible()
    expect(page.get_by_role("radio", name="Personas")).to_be_visible()
    for name in ("Todo UpiixSol", "Un club", "Un rol"):
        expect(page.get_by_role("radio", name=name)).to_have_count(0)
    page.get_by_role("radio", name="Mi club").check()
    page.get_by_label("Asunto").fill(SUBJECT)
    page.get_by_label("Texto del párrafo").first.fill(BODY)
    site.shot("club-mail-composer")
    view(site, "club-mail")
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_text(re.compile(r"Se enviará a \d+ personas?"))).to_be_visible()
    dialog.get_by_role("button", name="Enviar ahora").click()
    expect(dialog).to_be_hidden()
    history = page.get_by_role("region", name="Historial")
    row = history.get_by_role("listitem").filter(has_text=SUBJECT)
    expect(row).to_have_count(1)
    expect(row.get_by_text("Mi club")).to_be_visible()
    expect(row).not_to_contain_text("undefined")
    site.shot("club-mail-sent")


def test_sender_selector_for_superadmin_and_fixed_for_club_admin(site: Site) -> None:
    page = open_club_mail(site)
    expect(page.get_by_label("Enviado por")).to_have_count(0)  # not editable
    expect(page.get_by_text("Enviado por UpiixIA", exact=True)).to_be_visible()
    page.get_by_label("Asunto").fill("Aviso del club")
    page.get_by_label("Texto del párrafo").first.fill("Hola club")
    page.get_by_role("radio", name="Mi club").check()
    preview = page.frame_locator("iframe[title='Vista previa del correo']")
    expect(preview.get_by_text("UpiixIA").first).to_be_visible(timeout=10_000)
    page.locator("iframe[title='Vista previa del correo']").scroll_into_view_if_needed()
    view(site, "club-mail-preview")
    expect(page.get_by_role("button", name="Enviarme una prueba")).to_have_count(0)
    page.get_by_role("button", name="Agregar Botón").click()
    page.get_by_role("button", name="Ver el club").click()
    expect(page.get_by_label("Enlace del botón")).to_have_value("https://www.upiixsol.com/a/upiixia")


def test_club_admin_picker_lists_only_their_enrollees(site: Site) -> None:
    page = open_club_mail(site)
    page.get_by_role("radio", name="Personas").check()
    search = page.get_by_label("Buscar personas por nombre o apodo")
    search.fill("superadmin")
    expect(page.get_by_role("list", name="Resultados").get_by_text("Sin resultados.")).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"^Agregar Superadmin"))).to_have_count(0)
    search.fill("alumno")
    page.get_by_role("button", name="Agregar Alumno Demo").click()
    page.get_by_label("Correo externo").fill("invitado@example.com")
    page.get_by_role("button", name="Agregar correo").click()
    expect(page.get_by_text("Personas 2/50")).to_be_visible()
    expect(page.get_by_text("Correos externos 1/20")).to_be_visible()
    view(site, "club-mail-individual")
    site.shot("club-mail-individual")


def test_member_turns_off_club_email_in_mi_cuenta(site: Site) -> None:
    sign_in(site, MEMBER, "/cuenta")
    page = site.page
    switch = page.get_by_role("switch", name="Recibir correos del club")
    expect(switch).to_be_checked()
    expect(page.get_by_text(re.compile(r"Los avisos de tus clubes llegan a tu correo"))).to_be_visible()
    switch.scroll_into_view_if_needed()
    view(site, "account-mail-on")
    site.shot("account-mail-on")
    switch.click()
    expect(page.get_by_text("Ya no recibirás correos del club.")).to_be_visible()
    expect(switch).not_to_be_checked()
    page.reload()
    expect(page.get_by_role("switch", name="Recibir correos del club")).not_to_be_checked()
    site.shot("account-mail-off")
    page.get_by_role("switch", name="Recibir correos del club").click()
    expect(page.get_by_text("Volverás a recibir correos del club.")).to_be_visible()
    page.reload()
    expect(page.get_by_role("switch", name="Recibir correos del club")).to_be_checked()


def test_baja_page_confirms_and_unsubscribes(site: Site) -> None:
    page = site.page
    sent: list[str] = []

    def spy(route) -> None:  # noqa: ANN001 - playwright Route
        sent.append(f"{route.request.method} {route.request.url}")
        route.continue_()

    page.route("**/api/mail/unsubscribe*", spy)
    page.goto(site.url("/baja?t=token-de-prueba"))
    expect(page.get_by_text(GONE)).to_have_count(0)
    view(site, "baja-ask")
    site.shot("baja-ask")
    page.get_by_role("button", name="Darme de baja").click()
    expect(page.get_by_text(GONE)).to_be_visible()
    expect(page.get_by_role("button", name="Darme de baja")).to_have_count(0)
    assert len(sent) == 1 and sent[0].startswith("POST ") and sent[0].endswith("/api/mail/unsubscribe?t=token-de-prueba")
    view(site, "baja-done")
    site.shot("baja-done")
    page.unroute("**/api/mail/unsubscribe*")


def test_baja_page_with_bad_token_shows_the_same_message(site: Site) -> None:
    page = site.page
    page.goto(site.url("/baja?t=no-existe"))
    page.get_by_role("button", name="Darme de baja").click()
    expect(page.get_by_text(GONE)).to_be_visible()
    page.goto(site.url("/baja"))  # no token at all
    page.get_by_role("button", name="Darme de baja").click()
    expect(page.get_by_text(GONE)).to_be_visible()


def test_club_mail_tab_at_390_wide(site: Site) -> None:
    page = open_club_mail(site)
    expect(page.get_by_role("tab", name="Correos")).to_be_visible()
    expect(page.get_by_role("radio", name="Mi club")).to_be_visible()
    expect(page.get_by_role("radio", name="Personas")).to_be_visible()
    page.get_by_label("Asunto").fill("Revisión de pantalla")
    page.get_by_label("Texto del párrafo").first.fill(BODY)
    page.get_by_role("radio", name="Mi club").check()
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_role("button", name="Enviar ahora")).to_be_visible()
    expect(dialog.get_by_role("button", name="Cancelar")).to_be_visible()
    view(site, "club-mail-modal")
    site.shot("club-mail-390")
