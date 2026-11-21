"""Email canvas (UPS-103, spec 005 §Canvas): step 2 edits on a picture of the email. Text blocks are typed in place
with a small format toolbar, "+" inserts any of the seven kinds, blocks move by drag or Alt+↑/↓, duplicate and
delete with undo, buttons/events/images open a properties panel (bottom sheet at 390), and "Ver como llega"
shows the exact server render."""

import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from app.services.mail_templates_builtin import builtin_by_id
from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in

SUPERADMIN = "superadmin1@upiixsol.dev"
DRAFT_KEY = "upiixsol.mail-draft"
SHOTS = Path(".uak-shots/UPS-103")
PREVIEW = "iframe[title='Vista previa del correo']"


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


def open_canvas(site: Site) -> Page:
    """Step 2 of a fresh composer (no stored draft): one empty paragraph."""
    sign_in(site, SUPERADMIN, "/")
    page = site.page
    page.goto(site.url("/admin?tab=correos&paso=contenido"))
    expect(canvas(page)).to_be_visible()  # signed in and settled before the reload
    page.evaluate(f"localStorage.removeItem('{DRAFT_KEY}')")
    page.reload()
    expect(canvas(page)).to_be_visible()
    return page


def canvas(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("region", name="Lienzo del correo")


def blocks(page: Page):  # noqa: ANN201
    return page.get_by_role("list", name="Bloques del correo").get_by_role("listitem")


def block(page: Page, n: int):  # noqa: ANN201
    """The n-th block (1-based)."""
    return blocks(page).nth(n - 1)


def toolbar(page: Page):  # noqa: ANN201
    return page.get_by_role("toolbar", name="Herramientas del bloque")


def properties(page: Page):  # noqa: ANN201
    return page.get_by_label("Propiedades del bloque")


def close_sheet(page: Page) -> None:
    """On phones the properties are a bottom sheet over the email: close it before touching what it covers."""
    close = page.get_by_role("button", name="Cerrar propiedades")
    if page.viewport_size and page.viewport_size["width"] < 1024 and close.count():
        close.click()


def insert_at_end(page: Page, kind: str) -> None:
    close_sheet(page)
    page.get_by_role("button", name="Agregar bloque al final").click()
    page.get_by_role("menu", name="Tipo de bloque").get_by_role("menuitem", name=kind, exact=True).click()


def deselect(page: Page) -> None:
    """Leave the canvas, as tabbing or clicking elsewhere does."""
    page.get_by_label("Asunto").focus()


def keep(site: Site, name: str, focus=None) -> None:  # noqa: ANN001 - playwright Locator
    """Design-review shot: .uak-shots/UPS-103/<1280|390>-<name>.png (viewport around `focus`, or the full page)."""
    SHOTS.mkdir(parents=True, exist_ok=True)
    page = site.page
    if focus is not None:
        focus.scroll_into_view_if_needed()
        page.evaluate("window.scrollBy(0, -160)")
    page.wait_for_timeout(400)
    width = "1280" if site.name == "desktop" else "390"
    page.screenshot(path=SHOTS / f"{width}-{name}.png", full_page=focus is None)


def load_template(page: Page, template_id: str) -> None:
    """A real built-in template in the canvas (the gallery is UPS-104): stored as this user's local draft and
    restored with "Restaurar borrador", which is the composer's own way in."""
    page.get_by_label("Asunto").fill("x")
    page.wait_for_function(f"localStorage.getItem('{DRAFT_KEY}') !== null")
    stored = json.loads(page.evaluate(f"localStorage.getItem('{DRAFT_KEY}')"))
    template = builtin_by_id(template_id)
    assert template is not None
    drafts = []
    for i, b in enumerate(template.blocks):
        base = {"id": f"t{i}", "kind": b["kind"]}
        if b["kind"] in ("heading", "paragraph"):
            drafts.append({**base, "text": b["text"]})
        elif b["kind"] == "list":
            drafts.append({**base, "text": "\n".join(b["items"]), "ordered": bool(b.get("ordered"))})
        elif b["kind"] == "button":
            drafts.append({**base, "label": b["label"], "url": b["url"]})
        elif b["kind"] == "divider":
            drafts.append(base)
    stored["state"].update(subject=template.subject, preheader=template.preheader, drafts=drafts)
    page.evaluate(f"localStorage.setItem('{DRAFT_KEY}', {json.dumps(json.dumps(stored))})")
    page.reload()
    page.get_by_role("button", name="Restaurar borrador").click()
    expect(page.get_by_label("Asunto")).to_have_value(template.subject)


def click_on(page: Page, target) -> None:  # noqa: ANN001 - playwright Locator
    """A real click on formatted text: it turns into the textarea under the pointer, so the node goes away mid-click
    (a locator click would then retry on a detached element)."""
    target.scroll_into_view_if_needed()
    box = target.bounding_box()
    assert box
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def rgb(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgb({r}, {g}, {b})"


def test_canvas_shows_logo_sender_and_theme_like_the_email(site: Site) -> None:
    sign_in(site, SUPERADMIN, "/")
    page = site.page
    page.goto(site.url("/admin?tab=correos&paso=contenido"))
    expect(canvas(page)).to_be_visible()
    page.evaluate(f"localStorage.removeItem('{DRAFT_KEY}')")
    with page.expect_response(lambda r: r.url.endswith("/api/mail/preview") and r.request.method == "POST") as answer:
        page.reload()
    theme = answer.value.json()["theme"]
    load_template(page, "builtin:anuncio")
    email = canvas(page).get_by_test_id("email-card")
    expect(email).to_be_visible()
    expect(email).to_have_css("max-width", f"{theme['spacing']['width']}px")
    expect(email).to_have_css("font-family", re.compile(re.escape(theme["font"].split(",")[0].strip())))
    expect(canvas(page).get_by_text(theme["sender"]["label"]).first).to_be_visible()
    expect(canvas(page).get_by_text(theme["sender"]["name"]).first).to_be_visible()
    if theme["site_logo_url"]:
        expect(canvas(page).get_by_role("img", name=theme["site_name"]).first).to_have_attribute("src", theme["site_logo_url"])
    else:
        expect(canvas(page).get_by_text(theme["site_name"]).first).to_be_visible()
    expect(blocks(page)).to_have_count(5)
    expect(block(page, 1)).to_have_attribute("aria-label", "Bloque 1: Título")
    button = block(page, 3).get_by_text("Quiero saber más")
    expect(button).to_have_css("background-color", rgb(theme["colors"]["secondary"]))
    expect(button).to_have_css("color", rgb(theme["colors"]["on_secondary"]))
    # The paragraph shows its formatting (bold) while it is not being edited.
    deselect(page)
    expect(block(page, 2).locator("strong").first).to_have_text("qué")
    site.shot("canvas-template")
    keep(site, "lienzo-plantilla")
    page.screenshot(path=SHOTS / ("1280.png" if site.name == "desktop" else "390.png"), full_page=True)


def test_click_block_edits_in_place(site: Site) -> None:
    page = open_canvas(site)
    insert_at_end(page, "Título")
    title = block(page, 2).get_by_label("Texto del título")
    expect(title).to_be_focused()
    page.keyboard.type("Primera clase de robótica")
    deselect(page)
    expect(block(page, 2).locator("h3", has_text="Primera clase de robótica")).to_be_visible()
    expect(block(page, 2)).not_to_have_attribute("data-selected", "true")
    click_on(page, block(page, 2).locator("h3", has_text="Primera clase de robótica"))
    expect(block(page, 2)).to_have_attribute("data-selected", "true")
    expect(title).to_be_focused()
    expect(title).to_have_value("Primera clase de robótica")
    # A list is typed in place too: one item per line, shown as bullets once you leave it.
    insert_at_end(page, "Lista")
    items = block(page, 3).get_by_label("Elementos de la lista (uno por línea)")
    expect(items).to_be_focused()
    page.keyboard.type("Laptop")
    page.keyboard.press("Enter")
    page.keyboard.type("Cargador")
    deselect(page)
    expect(block(page, 3).locator("li")).to_have_count(2)


def test_inline_toolbar_bold_italic_link(site: Site) -> None:
    page = open_canvas(site)
    text = block(page, 1).get_by_label("Texto del párrafo")
    block(page, 1).click()
    page.keyboard.type("Trae tu laptop")
    expect(toolbar(page)).to_be_visible()
    text.evaluate("el => el.setSelectionRange(8, 14)")  # "laptop"
    toolbar(page).get_by_role("button", name="Negritas").click()
    expect(text).to_have_value("Trae tu **laptop**")
    text.evaluate("el => el.setSelectionRange(0, 4)")  # "Trae"
    page.keyboard.press("ControlOrMeta+i")
    expect(text).to_have_value("*Trae* tu **laptop**")
    text.evaluate("el => { el.setSelectionRange(el.value.length, el.value.length) }")
    page.keyboard.type(" al salón")
    text.evaluate("el => el.setSelectionRange(el.value.length - 5, el.value.length)")  # "salón"
    toolbar(page).get_by_role("button", name="Enlace").click()
    page.get_by_label("Dirección del enlace").fill("https://www.upiixsol.com/")
    page.get_by_role("button", name="Aplicar enlace").click()
    expect(text).to_have_value("*Trae* tu **laptop** al [salón](https://www.upiixsol.com/)")
    deselect(page)
    expect(block(page, 1).locator("strong")).to_have_text("laptop")
    expect(block(page, 1).locator("em")).to_have_text("Trae")
    expect(block(page, 1).locator("a", has_text="salón")).to_have_attribute("href", "https://www.upiixsol.com/")
    click_on(page, block(page, 1).locator("strong"))
    expect(toolbar(page)).to_be_visible()
    keep(site, "lienzo-texto", block(page, 1))


def test_plus_inserter_adds_selected_focused_block(site: Site) -> None:
    page = open_canvas(site)
    page.get_by_role("button", name="Agregar bloque al final").click()
    menu = page.get_by_role("menu", name="Tipo de bloque")
    expect(menu.get_by_role("menuitem")).to_have_count(7)
    for name in ("Título", "Párrafo", "Lista", "Botón", "Evento", "Imagen", "Separador"):
        expect(menu.get_by_role("menuitem", name=name, exact=True)).to_be_visible()
    expect(menu.get_by_role("menuitem").first).to_be_focused()
    page.wait_for_timeout(500)  # the menu scrolls itself into view
    page.screenshot(path=SHOTS / f"{'1280' if site.name == 'desktop' else '390'}-lienzo-insertar.png")
    page.keyboard.press("Escape")
    expect(menu).to_have_count(0)
    expect(page.get_by_role("button", name="Agregar bloque al final")).to_be_focused()
    insert_at_end(page, "Separador")
    expect(blocks(page)).to_have_count(2)
    # "+" between two blocks inserts there, and the new block is selected with its text focused.
    page.get_by_role("button", name="Insertar bloque después del bloque 1").click()
    page.get_by_role("menuitem", name="Título", exact=True).click()
    expect(blocks(page)).to_have_count(3)
    expect(block(page, 2)).to_have_attribute("aria-label", "Bloque 2: Título")
    expect(block(page, 2)).to_have_attribute("data-selected", "true")
    expect(block(page, 2).get_by_label("Texto del título")).to_be_focused()
    expect(block(page, 3)).to_have_attribute("aria-label", "Bloque 3: Separador")


def test_drag_and_keyboard_reorder(site: Site) -> None:
    page = open_canvas(site)
    block(page, 1).get_by_label("Texto del párrafo").fill("Primero el párrafo")
    insert_at_end(page, "Título")
    page.keyboard.type("Luego el título")
    expect(block(page, 2)).to_have_attribute("aria-label", "Bloque 2: Título")
    if site.name == "desktop":  # native drag needs a mouse; phones use Alt+arrows or the toolbar
        handle = block(page, 2).get_by_label("Arrastrar para mover")
        block(page, 2).hover()
        start, target = handle.bounding_box(), block(page, 1).bounding_box()
        assert start and target
        page.mouse.move(start["x"] + start["width"] / 2, start["y"] + start["height"] / 2)
        page.mouse.down()
        page.mouse.move(target["x"] + target["width"] / 2, target["y"] + 8, steps=8)
        page.mouse.up()
        expect(block(page, 1)).to_have_attribute("aria-label", "Bloque 1: Título")
        expect(block(page, 2)).to_have_attribute("aria-label", "Bloque 2: Párrafo")
        block(page, 2).click()
    else:
        block(page, 2).click()
        toolbar(page).get_by_role("button", name="Mover arriba").click()
        expect(block(page, 1)).to_have_attribute("aria-label", "Bloque 1: Título")
        block(page, 2).click()
    page.keyboard.press("Alt+ArrowUp")
    expect(block(page, 1)).to_have_attribute("aria-label", "Bloque 1: Párrafo")
    expect(block(page, 1)).to_have_attribute("data-selected", "true")
    expect(block(page, 1).get_by_label("Texto del párrafo")).to_be_focused()
    page.keyboard.press("Alt+ArrowDown")
    expect(block(page, 2)).to_have_attribute("aria-label", "Bloque 2: Párrafo")
    expect(page.get_by_role("status").filter(has_text="Bloque movido")).to_have_count(1)


def test_duplicate_and_delete_with_undo(site: Site) -> None:
    page = open_canvas(site)
    block(page, 1).get_by_label("Texto del párrafo").fill("Nos vemos el viernes")
    toolbar(page).get_by_role("button", name="Duplicar bloque").click()
    expect(blocks(page)).to_have_count(2)
    expect(block(page, 2).get_by_label("Texto del párrafo")).to_have_value("Nos vemos el viernes")
    expect(block(page, 2)).to_have_attribute("data-selected", "true")
    block(page, 2).get_by_label("Texto del párrafo").fill("La copia")
    expect(block(page, 1).get_by_label("Texto del párrafo")).to_have_value("Nos vemos el viernes")
    toolbar(page).get_by_role("button", name="Eliminar bloque").click()
    expect(blocks(page)).to_have_count(1)
    notice = page.get_by_role("status").filter(has_text="Bloque eliminado")
    expect(notice).to_be_visible()
    notice.get_by_role("button", name="Deshacer").click()
    expect(blocks(page)).to_have_count(2)
    expect(block(page, 2).get_by_label("Texto del párrafo")).to_have_value("La copia")
    # Without undo the notice leaves after 5 s and the block stays gone.
    block(page, 2).click()
    toolbar(page).get_by_role("button", name="Eliminar bloque").click()
    expect(notice).to_be_visible()
    expect(notice).to_have_count(0, timeout=7_000)
    expect(blocks(page)).to_have_count(1)


def test_button_event_image_open_properties_panel(site: Site) -> None:
    page = open_canvas(site)
    insert_at_end(page, "Botón")
    panel = properties(page)
    expect(panel).to_be_visible()
    expect(panel.get_by_role("heading", name="Botón")).to_be_visible()
    expect(panel.get_by_label("Texto del botón")).to_be_focused()
    panel.get_by_role("button", name="Ir al campus").click()
    expect(block(page, 2).get_by_text("Ir al campus")).to_be_visible()
    expect(panel.get_by_label("Enlace del botón")).to_have_value("https://www.upiixsol.com/")
    if site.name == "desktop":
        keep(site, "lienzo-boton")
    panel.get_by_role("button", name="Cerrar propiedades").click()
    expect(properties(page).get_by_label("Texto del botón")).to_have_count(0)
    insert_at_end(page, "Evento")
    expect(properties(page).get_by_role("radiogroup", name="Origen del evento")).to_be_visible()
    properties(page).get_by_text("Escribir evento").click()
    properties(page).get_by_label("Título del evento").fill("Taller de drones")
    expect(block(page, 3).get_by_text("Taller de drones")).to_be_visible()
    insert_at_end(page, "Imagen")
    expect(properties(page).get_by_label("Texto alternativo de la imagen")).to_be_visible()
    expect(properties(page).get_by_role("button", name="Elegir imagen")).to_be_visible()
    # A text block has no panel: it is edited on the email.
    close_sheet(page)
    block(page, 1).click()
    expect(properties(page).get_by_label("Texto alternativo de la imagen")).to_have_count(0)


def test_bottom_sheet_at_390_wide(site: Site) -> None:
    page = open_canvas(site)
    insert_at_end(page, "Botón")
    panel = properties(page)
    expect(panel).to_be_visible()
    box = panel.bounding_box()
    viewport = page.viewport_size
    assert box and viewport
    if site.name == "mobile":
        assert box["width"] >= viewport["width"] - 1  # full width
        assert abs(box["y"] + box["height"] - viewport["height"]) <= 2  # pinned to the bottom
        keep(site, "lienzo-boton")
        page.keyboard.press("Escape")
        expect(panel.get_by_label("Texto del botón")).to_have_count(0)
    else:
        email = canvas(page).get_by_test_id("email-card").bounding_box()
        assert email and box["x"] >= email["x"] + email["width"]  # a side panel beside the email
    site.shot("canvas-properties")


def test_ver_como_llega_shows_server_render(site: Site) -> None:
    page = open_canvas(site)
    page.get_by_label("Asunto").fill("Primera clase")
    block(page, 1).get_by_label("Texto del párrafo").fill("Trae tu laptop al salón 205.")
    expect(page.locator(PREVIEW)).to_have_count(0)  # the canvas is the editor; the exact render is one click away
    page.get_by_role("button", name="Ver como llega").click()
    dialog = page.get_by_role("dialog", name="Así llega el correo")
    expect(dialog).to_be_visible()
    frame = page.frame_locator(PREVIEW)
    expect(frame.get_by_text("salón 205")).to_be_visible(timeout=10_000)
    assert page.locator(PREVIEW).get_attribute("sandbox") == "allow-same-origin"
    dialog.get_by_role("button", name="Teléfono").click()
    expect(page.locator(PREVIEW)).to_have_css("width", re.compile(r"^(375|3[0-6]\d)px$"))
    keep(site, "ver-como-llega")
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)


def test_limits_and_errors_next_to_the_block(site: Site) -> None:
    page = open_canvas(site)
    insert_at_end(page, "Botón")
    deselect(page)
    expect(block(page, 2).get_by_text("Falta el texto o el enlace del botón.")).to_be_visible()
    insert_at_end(page, "Evento")
    close_sheet(page)
    page.get_by_role("button", name="Agregar bloque al final").click()
    evento = page.get_by_role("menuitem", name="Evento", exact=True)
    expect(evento).to_be_disabled()
    expect(page.get_by_role("menu", name="Tipo de bloque")).to_contain_text("Un correo lleva un solo evento")
    page.keyboard.press("Escape")
    deselect(page)
    expect(block(page, 3).get_by_text("Elige un evento del calendario o escríbelo.")).to_be_visible()
    # Up to 30 blocks: duplicating the paragraph fills the email and "+" turns off.
    block(page, 1).get_by_label("Texto del párrafo").fill("Hola")
    for _ in range(27):
        toolbar(page).get_by_role("button", name="Duplicar bloque").click()
    expect(blocks(page)).to_have_count(30)
    expect(page.get_by_text("Un correo admite hasta 30 bloques.")).to_be_visible()
    expect(page.get_by_role("button", name="Agregar bloque al final")).to_be_disabled()
    expect(toolbar(page).get_by_role("button", name="Duplicar bloque")).to_be_disabled()
