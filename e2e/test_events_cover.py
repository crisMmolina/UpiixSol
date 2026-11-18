"""Event photo (UPS-094), in a real browser at 1280 and 390 wide: publish an event with a photo, see it in the
calendar list and on the home, replace it, remove it, and keep the event when the photo upload fails.

One sign-in per viewport (the module's server is shared by its tests)."""

import io
import re

from PIL import Image
from playwright.sync_api import Page, expect

from e2e.conftest import Site
from e2e.test_content import as_superadmin

TITLE = "Taller con foto"
FAILING = "Taller cuya foto falla"


def photo(color: tuple[int, int, int]) -> dict:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 360), color).save(buffer, "PNG")
    return {"name": "foto.png", "mimeType": "image/png", "buffer": buffer.getvalue()}


def row(page: Page, title: str):
    return page.get_by_role("listitem").filter(has=page.get_by_role("heading", name=title))


def open_form(page: Page, name: str):
    dialog = page.get_by_role("dialog", name=name)
    expect(dialog).to_be_visible()
    return dialog


def test_publish_with_photo_replace_and_remove(site: Site) -> None:
    page = as_superadmin(site, "/calendario?vista=lista")
    expect(page.get_by_role("heading", name="Próximos eventos")).to_be_visible()
    page.get_by_role("button", name="Nuevo evento").click()
    dialog = open_form(page, "Nuevo evento")
    dialog.get_by_label("Título").fill(TITLE)
    expect(dialog.get_by_text("Sin foto")).to_be_visible()
    dialog.locator("input[type=file]").set_input_files(photo((0, 191, 99)))
    expect(dialog.get_by_alt_text("Vista previa de la foto del evento")).to_be_visible()
    dialog.get_by_text("PNG, JPG o WebP de hasta 5 MB.").scroll_into_view_if_needed()
    site.shot("events-cover-form")
    dialog.get_by_role("button", name="Publicar evento").click()
    expect(dialog).to_be_hidden()

    # The calendar list shows it: a /media/ url, alt="" and a real decoded image.
    image = row(page, TITLE).locator("img")
    expect(image).to_have_attribute("src", re.compile(r"^/media/cover/.+\.webp$"))
    expect(image).to_have_attribute("alt", "")
    image.scroll_into_view_if_needed()
    page.wait_for_function("el => el.complete && el.naturalWidth > 0", arg=image.element_handle())
    site.shot("events-cover-list")
    first = image.get_attribute("src")

    # Replace it.
    page.get_by_role("button", name=f"Editar {TITLE}").click()
    dialog = open_form(page, "Editar evento")
    expect(dialog.get_by_alt_text("Vista previa de la foto del evento")).to_be_visible()
    dialog.locator("input[type=file]").set_input_files(photo((255, 120, 0)))
    dialog.get_by_role("button", name="Guardar cambios").click()
    expect(dialog).to_be_hidden()
    expect(row(page, TITLE).locator("img")).not_to_have_attribute("src", first or "")
    expect(row(page, TITLE).locator("img")).to_have_attribute("src", re.compile(r"^/media/cover/"))
    assert page.request.get(site.url(first or "/media/none")).status == 404  # the old file is gone

    # Remove it: the row goes back to the layout without a photo.
    page.get_by_role("button", name=f"Editar {TITLE}").click()
    dialog = open_form(page, "Editar evento")
    dialog.get_by_role("button", name="Quitar foto").click()
    expect(dialog.get_by_text("Sin foto")).to_be_visible()
    dialog.get_by_role("button", name="Guardar cambios").click()
    expect(dialog).to_be_hidden()
    expect(row(page, TITLE)).to_be_visible()
    expect(row(page, TITLE).locator("img")).to_have_count(0)


def test_event_stays_when_the_photo_upload_fails(site: Site) -> None:
    page = as_superadmin(site, "/calendario?vista=lista")
    expect(page.get_by_role("heading", name="Próximos eventos")).to_be_visible()
    page.route("**/api/events/*/cover", lambda route: route.fulfill(status=500, json={"error": {"message": "x"}}))
    page.get_by_role("button", name="Nuevo evento").click()
    dialog = open_form(page, "Nuevo evento")
    dialog.get_by_label("Título").fill(FAILING)
    dialog.locator("input[type=file]").set_input_files(photo((10, 20, 200)))
    dialog.get_by_role("button", name="Publicar evento").click()
    expect(dialog.get_by_text("El evento se publicó, pero la foto no se pudo subir. Intenta de nuevo.")).to_be_visible()
    expect(row(page, FAILING)).to_be_visible()  # the event exists and the list was refreshed
    site.shot("events-cover-failed")

    # Trying again edits the same event (no duplicate) and now the upload works.
    page.unroute("**/api/events/*/cover")
    dialog.get_by_role("button", name="Guardar cambios").click()
    expect(dialog).to_be_hidden()
    expect(row(page, FAILING)).to_have_count(1)
    expect(row(page, FAILING).locator("img")).to_have_attribute("src", re.compile(r"^/media/cover/"))


def test_photo_shows_on_the_home(site: Site) -> None:
    page = as_superadmin(site, "/")
    card = page.get_by_role("listitem").filter(has=page.get_by_text(FAILING))
    expect(card.locator("img")).to_have_attribute("src", re.compile(r"^/media/cover/"))
    expect(card.locator("img")).to_have_attribute("alt", "")
    site.shot("events-cover-home")
