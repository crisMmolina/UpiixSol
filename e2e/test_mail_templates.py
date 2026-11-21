"""Template gallery (UPS-104, spec 005 §Templates, spec 006 §Decisions): built-in, saved, recent sent and blank;
"Guardar como plantilla" in step 2; save on send (checked by default); "Enviados recientes" and `?reusar=<id>`."""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in
from e2e.test_mail_composer import ADMIN, CLUB_ADMIN, SUPERADMIN, current_step, forget_draft, open_composer, stepper
from e2e.test_mail_recipients import add_source

CLUB_PANEL = "/panel/academia?tab=correos"
SHOTS = Path(".uak-shots/UPS-104")
SIGNED_IN: dict[str, str] = {}
BUILTINS = ("Anuncio", "Invitación a evento", "Recordatorio", "Nueva clase / boletín")


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


def fresh(site: Site, path: str = ADMIN, email: str = SUPERADMIN) -> Page:
    """The composer at step 1 with no local draft."""
    # Signing in again for every test trips the login rate limit: only when the account changes.
    if SIGNED_IN.get(site.name) == email:
        page = site.page
        page.goto(site.url(path))
        expect(stepper(page)).to_be_visible(timeout=20_000)
    else:
        page = open_composer(site, path, email)
        SIGNED_IN[site.name] = email
    forget_draft(page)
    page.reload()
    expect(current_step(page)).to_contain_text("Plantilla")
    return page


def keep(site: Site, name: str, full: bool = True) -> None:
    """Shot for the design review. `full` makes the viewport as tall as the page (so every frame is on screen and the
    fixed bottom bar sits at the end instead of over the content); else the current viewport, for dialogs."""
    SHOTS.mkdir(parents=True, exist_ok=True)
    page = site.page
    wide = "1280" if site.name == "desktop" else "390"
    original = page.viewport_size
    assert original is not None
    if full:
        page.evaluate("window.scrollTo(0, 0)")
        page.set_viewport_size({"width": original["width"], "height": min(8000, page.evaluate("document.documentElement.scrollHeight"))})
    if page.locator("[data-thumb]").count():  # live thumbnails render a moment after the gallery shows
        page.wait_for_function("[...document.querySelectorAll('[data-thumb]')].every(e => e.dataset.thumb === 'loaded')", timeout=30_000)
    page.wait_for_timeout(1000)
    if full:  # the page grew while the thumbnails and lists loaded: measure again
        page.set_viewport_size({"width": original["width"], "height": min(8000, page.evaluate("document.documentElement.scrollHeight"))})
        page.wait_for_timeout(500)
    page.screenshot(path=SHOTS / f"{wide}-{name}.png")
    if name == "gallery":
        page.screenshot(path=SHOTS / f"{wide}.png")
    page.set_viewport_size(original)


def card(page: Page, name: str):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("button", name=re.compile("^" + re.escape(name).replace("/", r"\/")))


def write_email(page: Page, subject: str, text: str = "Hola a todos: este jueves nos vemos en el salón 205 para repasar lo de la semana.") -> None:
    """From step 1 (blank) to a filled step 2."""
    page.get_by_role("button", name=re.compile("^En blanco")).click()
    expect(current_step(page)).to_contain_text("Contenido")
    page.get_by_label("Asunto").fill(subject)
    page.get_by_label("Texto del párrafo").first.fill(text)


def save_as_template(page: Page, name: str, description: str | None = "Para correos frecuentes") -> None:
    page.get_by_role("button", name="Guardar como plantilla").click()
    dialog = page.get_by_role("dialog", name="Guardar como plantilla")
    dialog.get_by_label("Nombre de la plantilla").fill(name)
    if description:
        dialog.get_by_label("Descripción (opcional)").fill(description)
    dialog.get_by_role("button", name="Guardar", exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Plantilla guardada")).to_be_visible()
    expect(dialog).to_be_hidden()  # the closing dialog must be gone before the next one opens


def next_step(page: Page) -> None:
    """"Siguiente" at the very end of the page: on a phone the fixed bottom bar must not sit on top of it."""
    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    page.get_by_role("button", name="Siguiente").click(timeout=30_000)


def go_to_gallery(page: Page) -> None:
    stepper(page).get_by_role("button", name=re.compile("Plantilla")).click()
    expect(current_step(page)).to_contain_text("Plantilla")


def send_email(page: Page, subject: str, save: bool = False) -> int:
    """Writes, sends to everyone and returns the campaign id. Leaves the composer on step 1."""
    write_email(page, subject)
    next_step(page)
    add_source(page, "Todo UpiixSol")
    box = page.get_by_role("checkbox", name="Guardar como plantilla")
    if not save and box.count():
        box.uncheck()
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    with page.expect_response(lambda r: r.url.endswith("/api/mail/campaigns") and r.request.method == "POST") as created:
        dialog.get_by_role("button", name="Enviar ahora").click()
    expect(dialog).to_be_hidden()
    expect(current_step(page)).to_contain_text("Plantilla")
    return int(created.value.json()["id"])


def test_gallery_shows_builtins_saved_and_blank_with_thumbnails(site: Site) -> None:
    page = fresh(site)
    upiixsol = page.get_by_role("region", name="Plantillas de UpiixSol")
    for name in BUILTINS:
        expect(card(upiixsol, name)).to_be_visible()
        thumb = page.locator(f"iframe[title='Miniatura de {name}']")
        expect(thumb).to_have_attribute("srcdoc", re.compile("<"))
        assert "allow-scripts" not in (thumb.get_attribute("sandbox") or "")
    expect(upiixsol.get_by_text("Una noticia breve con un botón para saber más.")).to_be_visible()
    blank = page.get_by_role("region", name="En blanco")
    expect(card(blank, "En blanco")).to_be_visible()
    expect(page.get_by_role("region", name="Plantillas de mi club")).to_have_count(0)  # a superadmin has no club
    keep(site, "gallery")


def test_pick_template_loads_subject_preheader_and_blocks(site: Site) -> None:
    page = fresh(site)
    card(page, "Anuncio").click()
    expect(current_step(page)).to_contain_text("Contenido")
    expect(page.get_by_label("Asunto")).to_have_value("Escribe aquí el asunto del anuncio")
    expect(page.get_by_label("Texto de vista previa (opcional)")).to_have_value("Una línea que se ve junto al asunto en la bandeja de entrada")
    expect(page.get_by_label("Texto del párrafo").first).to_have_value(re.compile("Cuenta la novedad"))
    # Loading over unsaved work asks first.
    go_to_gallery(page)
    card(page, "Recordatorio").click()
    dialog = page.get_by_role("dialog", name="¿Reemplazar tu correo?")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="Cancelar").click()
    expect(current_step(page)).to_contain_text("Plantilla")
    card(page, "Recordatorio").click()
    page.get_by_role("dialog", name="¿Reemplazar tu correo?").get_by_role("button", name="Reemplazar").click()
    expect(current_step(page)).to_contain_text("Contenido")
    expect(page.get_by_label("Asunto")).not_to_have_value("Escribe aquí el asunto del anuncio")


def test_event_placeholder_asks_to_complete_the_event(site: Site) -> None:
    page = fresh(site)
    card(page, "Invitación a evento").click()
    expect(current_step(page)).to_contain_text("Contenido")
    expect(page.get_by_text("Completa el evento").first).to_be_visible()
    site.shot("template-event-placeholder")


def test_save_as_template_and_find_it_in_the_gallery(site: Site) -> None:
    page = fresh(site)
    write_email(page, "Boletín de octubre", "Resumen de lo que pasó este mes.")
    page.get_by_role("button", name="Guardar como plantilla").click()
    dialog = page.get_by_role("dialog", name="Guardar como plantilla")
    expect(dialog.get_by_text("Se guardará en UpiixSol")).to_be_visible()
    dialog.get_by_label("Nombre de la plantilla").fill("x" * 70)
    assert len(dialog.get_by_label("Nombre de la plantilla").input_value()) == 60
    dialog.get_by_label("Nombre de la plantilla").fill("Boletín mensual")
    dialog.get_by_label("Descripción (opcional)").fill("Para anuncios del club")
    keep(site, "save-dialog", full=False)
    dialog.get_by_role("button", name="Guardar", exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Plantilla guardada")).to_be_visible()
    go_to_gallery(page)
    saved = card(page.get_by_role("region", name="Plantillas de UpiixSol"), "Boletín mensual")
    expect(saved).to_be_visible()
    expect(saved).to_contain_text("Para anuncios del club")
    saved.click()
    page.get_by_role("dialog", name="¿Reemplazar tu correo?").get_by_role("button", name="Reemplazar").click()
    expect(page.get_by_label("Asunto")).to_have_value("Boletín de octubre")


def test_rename_and_delete_own_template(site: Site) -> None:
    page = fresh(site)
    write_email(page, "Para renombrar")
    save_as_template(page, "Aviso de junta")
    save_as_template(page, "Borrador de convocatoria")
    go_to_gallery(page)
    expect(page.get_by_role("button", name=re.compile("^(Renombrar|Eliminar) Anuncio"))).to_have_count(0)  # built-ins are read-only
    page.get_by_role("button", name="Renombrar Aviso de junta").click()
    dialog = page.get_by_role("dialog", name="Renombrar plantilla")
    dialog.get_by_label("Nombre de la plantilla").fill("Citatorio general")
    dialog.get_by_role("button", name="Guardar", exact=True).click()
    expect(card(page, "Citatorio general")).to_be_visible()
    expect(card(page, "Aviso de junta")).to_have_count(0)
    page.get_by_role("button", name="Eliminar Borrador de convocatoria").click()
    confirm = page.get_by_role("dialog", name="Eliminar plantilla")
    confirm.get_by_role("button", name="Cancelar").click()
    expect(card(page, "Borrador de convocatoria")).to_be_visible()
    page.get_by_role("button", name="Eliminar Borrador de convocatoria").click()
    page.get_by_role("dialog", name="Eliminar plantilla").get_by_role("button", name="Eliminar", exact=True).click()
    expect(card(page, "Borrador de convocatoria")).to_have_count(0)


def test_club_admin_sees_site_and_own_club_templates_only(site: Site) -> None:
    page = fresh(site)
    write_email(page, "Plantilla del sitio")
    save_as_template(page, "Bienvenida UpiixSol")
    page = fresh(site, CLUB_PANEL, CLUB_ADMIN)
    write_email(page, "Plantilla del club")
    page.get_by_role("button", name="Guardar como plantilla").click()
    expect(page.get_by_role("dialog", name="Guardar como plantilla").get_by_text("Se guardará en tu club")).to_be_visible()
    page.get_by_role("dialog", name="Guardar como plantilla").get_by_label("Nombre de la plantilla").fill("Convocatoria del club")
    page.get_by_role("dialog", name="Guardar como plantilla").get_by_role("button", name="Guardar", exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Plantilla guardada")).to_be_visible()
    go_to_gallery(page)
    mine = page.get_by_role("region", name="Plantillas de mi club")
    expect(card(mine, "Convocatoria del club")).to_be_visible()
    expect(card(mine, "Bienvenida UpiixSol")).to_have_count(0)
    shared = page.get_by_role("region", name="Plantillas de UpiixSol")
    expect(card(shared, "Bienvenida UpiixSol")).to_be_visible()
    expect(card(shared, "Anuncio")).to_be_visible()
    expect(card(shared, "Convocatoria del club")).to_have_count(0)
    # A club admin cannot rename or delete the UpiixSol ones.
    expect(page.get_by_role("button", name="Renombrar Bienvenida UpiixSol")).to_have_count(0)
    expect(page.get_by_role("button", name="Renombrar Convocatoria del club")).to_be_visible()
    keep(site, "club-gallery")


def test_save_on_send_checked_by_default_and_saved(site: Site) -> None:
    page = fresh(site)
    write_email(page, "Cierre de inscripciones")
    next_step(page)
    add_source(page, "Todo UpiixSol")
    box = page.get_by_role("checkbox", name="Guardar como plantilla")
    expect(box).to_be_checked()
    expect(page.get_by_label("Nombre de la plantilla")).to_have_value("Cierre de inscripciones")
    keep(site, "save-on-send", full=False)
    page.get_by_role("button", name="Revisar y enviar").click()
    dialog = page.get_by_role("dialog", name="Revisar envío")
    dialog.get_by_role("button", name="Enviar ahora").click()
    expect(dialog).to_be_hidden()
    expect(current_step(page)).to_contain_text("Plantilla")
    expect(card(page.get_by_role("region", name="Plantillas de UpiixSol"), "Cierre de inscripciones")).to_be_visible()


def test_save_on_send_hidden_for_unchanged_template(site: Site) -> None:
    page = fresh(site)
    card(page, "Anuncio").click()
    expect(current_step(page)).to_contain_text("Contenido")
    next_step(page)
    expect(current_step(page)).to_contain_text("Destinatarios")
    expect(page.get_by_role("checkbox", name="Guardar como plantilla")).to_have_count(0)
    page.get_by_role("button", name="Atrás").click()
    page.get_by_label("Asunto").fill("Anuncio con cambios")
    next_step(page)
    expect(page.get_by_role("checkbox", name="Guardar como plantilla")).to_be_checked()


def test_recent_sent_section_reuses_an_email(site: Site) -> None:
    page = fresh(site)
    send_email(page, "Convocatoria a la reunión")
    recent = page.get_by_role("region", name="Enviados recientes")
    expect(recent).to_be_visible()
    assert recent.get_by_role("button", name=re.compile("^Usar de nuevo")).count() <= 6
    recent.scroll_into_view_if_needed()
    keep(site, "recent-sent", full=False)
    recent.get_by_role("button", name=re.compile("^Usar de nuevo.*Convocatoria a la reunión")).first.click()
    expect(current_step(page)).to_contain_text("Contenido")
    expect(page.get_by_label("Asunto")).to_have_value("Convocatoria a la reunión")
    expect(page.get_by_label("Texto del párrafo").first).to_have_value("Hola a todos: este jueves nos vemos en el salón 205 para repasar lo de la semana.")
    next_step(page)
    expect(page.get_by_role("list", name="Fuentes de destinatarios")).to_have_count(0)  # never the recipients
    keep(site, "reuse-recent")


def test_reusar_param_loads_a_sent_email(site: Site) -> None:
    page = fresh(site)
    campaign_id = send_email(page, "Cambio de salón")
    forget_draft(page)
    page.goto(site.url(f"{ADMIN}&paso=plantilla&reusar={campaign_id}"))
    expect(current_step(page)).to_contain_text("Contenido")
    expect(page.get_by_label("Asunto")).to_have_value("Cambio de salón")
    expect(page).not_to_have_url(re.compile("reusar="))
    page.goto(site.url(f"{ADMIN}&paso=plantilla&reusar=999999"))
    expect(page.get_by_role("alert").filter(has_text="No pudimos cargar ese correo")).to_be_visible()
    expect(current_step(page)).to_contain_text("Plantilla")


def test_gallery_at_390_wide(site: Site) -> None:
    page = fresh(site)
    page.set_viewport_size({"width": 390, "height": 844})
    expect(card(page.get_by_role("region", name="Plantillas de UpiixSol"), "Anuncio")).to_be_visible()
    expect(page.locator("iframe[title='Miniatura de Anuncio']")).to_have_attribute("srcdoc", re.compile("<"))
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    for name in BUILTINS:
        box = card(page, name).bounding_box()
        assert box is not None and box["width"] <= 390 and box["height"] >= 44
    keep(site, "gallery-390")
    site.shot("templates-390")
