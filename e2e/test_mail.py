"""Superadmin "Correos" tab (UPS-078): audience picker, preview and confirm modal, test send, disabled notice
and history. The server runs with the console backend (no Mailgun) and the seed's own domain unblocked."""

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


def compose(page: Page, subject: str, body: str = BODY) -> None:
    page.get_by_label("Asunto").fill(subject)
    page.get_by_label("Mensaje").fill(body)


def review_and_confirm(page: Page, people: str) -> None:
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    expect(dialog.get_by_text(re.compile(rf"Se enviará a {people}"))).to_be_visible()
    expect(dialog.get_by_text(re.compile(r"Hoy puedes enviar \d+ correos? más"))).to_be_visible()
    dialog.get_by_role("button", name="Enviar ahora").click()
    expect(dialog).to_be_hidden()


def test_superadmin_sends_to_a_club_after_preview_and_confirm(site: Site) -> None:
    page = open_mail(site)
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    compose(page, CLUB_SUBJECT)
    expect(page.get_by_text(re.compile(r"\d+ / 20[,\s\u00a0\u202f]?000"))).to_be_visible()
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


def test_test_send_reports_sent_to_me(site: Site) -> None:
    page = open_mail(site)
    page.get_by_role("button", name="Enviarme una prueba").click()
    expect(page.get_by_text("Escribe un asunto y un mensaje para enviar la prueba.")).to_be_visible()
    compose(page, "Prueba de formato")
    page.get_by_role("button", name="Enviarme una prueba").click()
    expect(page.get_by_text("Prueba enviada a tu correo.")).to_be_visible()
    site.shot("mail-test-sent")


def test_mail_disabled_shows_the_notice(site: Site) -> None:
    page = site.page
    status = {"enabled": False, "daily_limit": 100, "sent_today": 0, "remaining": 100}
    page.route("**/api/mail/status", lambda route: route.fulfill(json=status))
    page.goto(site.url("/admin?tab=correos"))
    expect(page.get_by_text("El correo está desactivado")).to_be_visible()
    expect(page.get_by_role("button", name="Revisar y enviar")).to_be_disabled()
    expect(page.get_by_role("button", name="Enviarme una prueba")).to_be_disabled()
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
    expect(mixed).to_contain_text("1 externos")
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
