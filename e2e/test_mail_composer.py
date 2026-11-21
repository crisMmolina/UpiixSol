"""Composer in three steps (UPS-102, spec 005 §Flow): Plantilla → Contenido → Destinatarios y envío, the step in the
URL (merged into the panel's `?tab=`), one state kept across steps and a local draft keyed by user."""

import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in

SUPERADMIN = "superadmin1@upiixsol.dev"
CLUB_ADMIN = "admin.ia@upiixsol.dev"
DRAFT_KEY = "upiixsol.mail-draft"
ADMIN = "/admin?tab=correos"
STEPS = ("Plantilla", "Contenido", "Destinatarios y envío")


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


def open_composer(site: Site, path: str = ADMIN, email: str = SUPERADMIN) -> Page:
    sign_in(site, email, "/")
    page = site.page
    page.goto(site.url(path))
    expect(page.get_by_role("navigation", name="Pasos del correo")).to_be_visible()
    return page


def stepper(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("navigation", name="Pasos del correo")


def current_step(page: Page):  # noqa: ANN201
    return stepper(page).locator("[aria-current='step']")


def forget_draft(page: Page) -> None:
    page.evaluate(f"localStorage.removeItem('{DRAFT_KEY}')")


def stored_draft(page: Page) -> str | None:
    return page.evaluate(f"localStorage.getItem('{DRAFT_KEY}')")


def test_three_steps_with_back_and_next_keep_state(site: Site) -> None:
    page = open_composer(site)
    forget_draft(page)
    page.reload()
    for name in STEPS:
        expect(stepper(page).get_by_role("button", name=re.compile(name))).to_be_visible()
    expect(current_step(page)).to_contain_text("Plantilla")
    expect(page.get_by_role("button", name=re.compile("En blanco"))).to_be_visible()
    page.get_by_role("button", name="Siguiente").click()
    expect(current_step(page)).to_contain_text("Contenido")
    page.get_by_label("Asunto").fill("Aviso de prueba")
    page.get_by_label("Texto del párrafo").first.fill("Hola, nos vemos el viernes.")
    page.get_by_role("button", name="Siguiente").click()
    expect(current_step(page)).to_contain_text("Destinatarios")
    page.get_by_role("radio", name="Un club").check()
    page.get_by_label("Club", exact=True).select_option(label="UpiixIA")
    page.get_by_role("button", name="Atrás").click()
    expect(current_step(page)).to_contain_text("Contenido")
    expect(page.get_by_label("Asunto")).to_have_value("Aviso de prueba")
    expect(page.get_by_label("Texto del párrafo").first).to_have_value("Hola, nos vemos el viernes.")
    stepper(page).get_by_role("button", name=re.compile("Destinatarios")).click()
    expect(page.get_by_role("radio", name="Un club")).to_be_checked()
    expect(page.get_by_label("Club", exact=True).locator("option:checked")).to_have_text("UpiixIA")
    stepper(page).get_by_role("button", name=re.compile("Plantilla")).click()
    expect(page.get_by_role("button", name="Atrás")).to_have_count(0)  # nothing before the first step
    site.shot("composer-keeps-state")


def test_step_in_url_keeps_the_admin_tab(site: Site) -> None:
    page = open_composer(site)
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    page.get_by_role("button", name="Siguiente").click()
    expect(page).to_have_url(re.compile(r"[?&]tab=correos"))
    expect(page).to_have_url(re.compile(r"[?&]paso=contenido"))
    page.get_by_role("button", name="Siguiente").click()
    expect(page).to_have_url(re.compile(r"[?&]paso=envio"))
    expect(page).to_have_url(re.compile(r"[?&]tab=correos"))
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    page.reload()
    expect(current_step(page)).to_contain_text("Destinatarios")
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    page.get_by_role("button", name="Atrás").click()
    expect(page).to_have_url(re.compile(r"[?&]paso=contenido"))
    expect(page).to_have_url(re.compile(r"[?&]tab=correos"))
    page.goto(site.url("/admin?tab=correos&paso=nada"))
    expect(current_step(page)).to_contain_text("Plantilla")  # an unknown step falls back to the first


def test_local_draft_restore_and_discard(site: Site) -> None:
    page = open_composer(site, f"{ADMIN}&paso=contenido")
    forget_draft(page)
    page.reload()
    expect(page.get_by_role("button", name="Restaurar borrador")).to_have_count(0)
    page.get_by_label("Asunto").fill("Borrador guardado")
    page.get_by_label("Texto del párrafo").first.fill("Texto a medias")
    page.wait_for_function(f"localStorage.getItem('{DRAFT_KEY}') !== null")
    page.reload()
    restore = page.get_by_role("button", name="Restaurar borrador")
    expect(restore).to_be_visible()
    expect(page.get_by_label("Asunto")).to_have_value("")
    site.shot("composer-draft-prompt")
    restore.click()
    expect(page.get_by_label("Asunto")).to_have_value("Borrador guardado")
    expect(page.get_by_label("Texto del párrafo").first).to_have_value("Texto a medias")
    expect(page.get_by_role("button", name="Restaurar borrador")).to_have_count(0)
    page.reload()
    page.get_by_role("button", name="Descartar").click()
    expect(page.get_by_role("button", name="Restaurar borrador")).to_have_count(0)
    assert stored_draft(page) is None
    page.reload()
    expect(page.get_by_role("button", name="Restaurar borrador")).to_have_count(0)
    expect(page.get_by_label("Asunto")).to_have_value("")


def test_draft_cleared_on_send_and_logout(site: Site) -> None:
    page = open_composer(site, f"{ADMIN}&paso=contenido")
    forget_draft(page)
    page.reload()
    page.get_by_label("Asunto").fill("Se envía y se borra")
    page.get_by_label("Texto del párrafo").first.fill("Contenido listo.")
    page.wait_for_function(f"localStorage.getItem('{DRAFT_KEY}') !== null")
    page.get_by_role("button", name="Siguiente").click()
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    dialog.get_by_role("button", name="Enviar ahora").click()
    expect(dialog).to_be_hidden()
    expect(page.get_by_role("region", name="Historial").get_by_text("Se envía y se borra")).to_be_visible()
    assert stored_draft(page) is None
    expect(current_step(page)).to_contain_text("Plantilla")  # a fresh email after sending
    # A draft left by another user (shared computer, logout) is deleted when the next person opens the composer.
    page.evaluate(
        f"localStorage.setItem('{DRAFT_KEY}', JSON.stringify({{userId: -1, savedAt: Date.now(), step: 'contenido', state: {{}}}}))"
    )
    sign_in(site, CLUB_ADMIN, "/")
    page.goto(site.url("/panel/academia?tab=correos"))
    expect(stepper(page)).to_be_visible()
    expect(page.get_by_role("button", name="Restaurar borrador")).to_have_count(0)
    assert stored_draft(page) is None


def test_send_step_has_audience_sender_reply_to_and_quota(site: Site) -> None:
    page = open_composer(site, f"{ADMIN}&paso=envio")
    expect(page.get_by_role("radio", name="Todo UpiixSol")).to_be_visible()
    expect(page.get_by_label("Enviado por")).to_be_visible()
    expect(page.get_by_label("Responder a")).to_be_visible()
    expect(page.get_by_text(re.compile(r"Te quedan [\d,]+ de [\d,]+ correos este mes"))).to_be_visible()
    expect(page.get_by_role("button", name="Revisar y enviar")).to_be_visible()
    expect(page.get_by_role("button", name="Siguiente")).to_have_count(0)  # the last step's one action is sending
    expect(page.get_by_label("Asunto")).to_have_count(0)  # the subject belongs to the content step
    page.get_by_role("button", name="Atrás").click()
    expect(page.get_by_label("Asunto")).to_be_visible()
    expect(page.get_by_role("radio", name="Todo UpiixSol")).to_have_count(0)
    expect(page.get_by_label("Responder a")).to_have_count(0)


def test_composer_steps_at_390_wide(site: Site) -> None:
    page = open_composer(site)
    for name in STEPS:
        expect(stepper(page).get_by_role("button", name=re.compile(name))).to_be_visible()
    box = stepper(page).bounding_box()
    viewport = page.viewport_size
    assert box and viewport and box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 1
    site.shot("composer-step-1")
    page.get_by_role("button", name="Siguiente").click()
    expect(page.get_by_label("Asunto")).to_be_visible()
    site.shot("composer-step-2")
    page.get_by_role("button", name="Siguiente").click()
    expect(page.get_by_role("button", name="Revisar y enviar")).to_be_visible()
    site.shot("composer-step-3")
    if site.name == "mobile":
        action = page.get_by_role("button", name="Revisar y enviar").bounding_box()
        assert action and action["width"] >= 160 and action["height"] >= 44
