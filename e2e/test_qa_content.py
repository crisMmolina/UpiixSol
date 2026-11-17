"""QA content, events and account in a real browser (UPS-056): PRUEBAS-CAMPUS.md §RES, §EVT, §ACC and §BLG.

The academy admin uploads a resource file and opens it, and sees the seed events on the calendar and the home
card; the member changes nickname, photo, email (errors) and password (then restores it); the superadmin
creates, edits and deletes a blog entry and a gallery project with covers, opens an unknown slug and checks
that hostile markdown never runs. Tests run in order on one site per viewport and sign in once per role
(login is rate-limited).
"""

from datetime import UTC, datetime, timedelta

from playwright.sync_api import APIRequestContext, Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import ADMIN_IA, MEMBER, SUPERADMIN, _png_bytes, sign_in, sign_out

WORKSHOP = "Taller: tu primera red neuronal"
CAMPUS_NIGHT = "Noche de proyectos UpiixSol"
PAST_EVENT = "Evento pasado QA"
FETCH = {"X-Requested-With": "fetch"}
HOSTILE = '<script>window.__qa_xss = 1</script><img src=x onerror="window.__qa_xss = 2">**seguro**'


def _login(request: APIRequestContext, site: Site, email: str, password: str = SEED_PASSWORD) -> str:
    credentials = {"email": email, "password": password}
    response = request.post(site.url("/api/auth/login"), data=credentials, headers=FETCH)
    assert response.ok, response.text()  # noqa: S101
    return response.json()["access_token"]


def _png(name: str = "qa.png") -> list[dict]:
    return [{"name": name, "mimeType": "image/png", "buffer": _png_bytes()}]


# ── RES-01 · an uploaded resource file opens as the image it is ──


def test_res01_resource_file_upload_and_open(site: Site) -> None:
    sign_in(site, ADMIN_IA, "/a/upiixia/recursos")
    page = site.page
    title = f"Recurso QA {site.name}"
    page.get_by_role("button", name="Agregar recurso").first.click()
    dialog = page.get_by_role("dialog", name="Nuevo recurso")
    dialog.get_by_label("Título").fill(title)
    dialog.get_by_label("Archivo (opcional)").set_input_files(files=_png())
    dialog.get_by_role("button", name="Agregar recurso").click()
    expect(dialog).to_have_count(0)

    card = page.locator("article, li", has_text=title).last
    link = card.get_by_role("link", name="Ver archivo")
    expect(link).to_have_attribute("target", "_blank")
    href = link.get_attribute("href") or ""
    assert href.startswith("/media/")  # noqa: S101
    response = page.request.get(site.url(href))
    body = response.body()
    # Stored as WebP: check the bytes, since /media/ serves it as application/octet-stream (followup).
    assert response.ok and body[:4] == b"RIFF" and body[8:12] == b"WEBP"  # noqa: S101
    site.shot("qa-content-resource")


# ── EVT-01/02 · the calendar shows every club's events and the home card the next ones ──


def test_evt01_calendar_lists_events_from_several_clubs(site: Site) -> None:
    page = site.page
    page.goto(site.url("/calendario?vista=lista"))
    workshop = page.locator("article, li", has_text=WORKSHOP).first
    expect(workshop).to_be_visible()
    expect(workshop).to_contain_text("5:00 p.m.")
    expect(page.get_by_text(CAMPUS_NIGHT).first).to_be_visible()
    site.shot("qa-content-calendar")


def test_evt02_home_card_shows_next_events_not_past_ones(site: Site) -> None:
    page = site.page
    api = page.context.browser.new_context()
    try:
        token = _login(api.request, site, ADMIN_IA)
        auth = {"Authorization": f"Bearer {token}"}
        academy = api.request.get(site.url("/api/academies/upiixia"), headers=auth).json()
        start = datetime.now(UTC) - timedelta(days=1)
        created = api.request.post(
            site.url("/api/events"),
            headers=auth,
            data={
                "academy_id": academy["id"],
                "title": f"{PAST_EVENT} {site.name}",
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(hours=2)).isoformat(),
            },
        )
        assert created.ok, created.text()  # noqa: S101
    finally:
        api.close()
    page.goto(site.url("/"))
    expect(page.get_by_text("Próximos eventos").first).to_be_visible()
    expect(page.get_by_text(WORKSHOP).first).to_be_visible()
    expect(page.get_by_text(f"{PAST_EVENT} {site.name}")).to_have_count(0)
    expect(page.get_by_role("link", name="Calendario").first).to_be_visible()


# ── ACC-01/02/03 · profile, email and password from "Mi cuenta" ──


def test_acc01_nickname_and_photo_update(site: Site) -> None:
    sign_in(site, MEMBER, "/cuenta")
    page = site.page
    nickname = f"QA{site.name[:3]}"
    page.get_by_label("Apodo").fill(nickname)
    page.get_by_role("button", name="Guardar perfil").click()
    expect(page.get_by_text("Perfil actualizado.")).to_be_visible()
    page.locator("label", has_text="Cambiar foto").locator('input[type="file"]').set_input_files(files=_png())
    expect(page.get_by_text("Foto actualizada.")).to_be_visible()

    page.reload()
    expect(page.get_by_label("Apodo")).to_have_value(nickname)
    menu = page.locator('button[aria-haspopup="menu"]')
    expect(menu.get_by_text(nickname)).to_be_attached()  # hidden below sm, shown in the desktop header
    if site.name == "desktop":
        expect(menu.get_by_text(nickname)).to_be_visible()
    site.shot("qa-content-profile")

    page.goto(site.url("/a/upiixia/comunidad"))  # the seed has two member posts in this channel
    expect(page.locator("article", has_text=nickname).first).to_be_visible()
    page.wait_for_load_state("networkidle")  # let the token refresh land before the next navigation


def _email_form(page: Page):
    return page.locator("form").filter(has=page.get_by_role("heading", name="Correo"))


def _password_form(page: Page):
    return page.locator("form").filter(has=page.get_by_role("heading", name="Contraseña"))


def test_acc02_email_change_rejects_wrong_password_and_duplicate(site: Site) -> None:
    page = site.page
    page.goto(site.url("/cuenta?tab=seguridad"))
    form = _email_form(page)
    form.get_by_label("Nuevo correo").fill(f"qa.nuevo.{site.name}@upiixsol.dev")
    form.get_by_label("Contraseña actual").fill("no-es-la-clave")
    form.get_by_role("button", name="Cambiar correo").click()
    expect(form.get_by_text("La contraseña actual no es correcta.")).to_be_visible()

    form.get_by_label("Nuevo correo").fill(ADMIN_IA)
    form.get_by_label("Contraseña actual").fill(SEED_PASSWORD)
    form.get_by_role("button", name="Cambiar correo").click()
    expect(form.get_by_text("Ese correo ya está registrado.")).to_be_visible()
    site.shot("qa-content-email")


def test_acc03_password_change_then_restore(site: Site) -> None:
    page = site.page
    original = SEED_PASSWORD
    temporary = f"{original}-qa-{site.name}"
    other = page.context.browser.new_context()  # a second device with its own session
    try:
        _login(other.request, site, MEMBER)
        assert other.request.post(site.url("/api/auth/refresh"), headers=FETCH).ok  # noqa: S101
        _change_password(page, original, temporary)
        assert other.request.post(site.url("/api/auth/refresh"), headers=FETCH).status == 401  # noqa: S101
    finally:
        other.close()
    _change_password(page, temporary, original)
    expect(page).to_have_url(site.url("/cuenta?tab=seguridad"))  # this session survives its own change


def _change_password(page: Page, current: str, new: str) -> None:
    form = _password_form(page)
    form.get_by_label("Contraseña actual").fill(current)
    form.get_by_label("Nueva contraseña", exact=True).fill(new)
    form.get_by_label("Confirma la nueva contraseña").fill(new)
    form.get_by_role("button", name="Cambiar contraseña").click()
    # Hashing twice (check + new) can take a few seconds on a busy machine.
    done = page.get_by_text("Contraseña actualizada. Cerramos tus otras sesiones.")
    expect(done).to_be_visible(timeout=15_000)
    page.reload()


# ── BLG-01 · blog entry: create with cover, edit, delete ──


def test_blg01_blog_entry_crud_with_cover(site: Site) -> None:
    sign_out(site.page)  # the member session from ACC-03 is still open
    sign_in(site, SUPERADMIN, "/blog")
    page = site.page
    title = f"Entrada QA {site.name}"
    page.get_by_role("button", name="Nueva entrada").click()
    page.get_by_label("Título").fill(title)
    page.get_by_label("Identificador en la URL (slug)").fill(f"entrada-qa-{site.name}")
    page.get_by_label("Contenido (markdown)").fill("Texto de **prueba**.")
    page.get_by_label("Portada (opcional)").set_input_files(files=_png())
    page.get_by_label("Publicada (visible para todos)").check()
    page.get_by_role("button", name="Crear entrada").click()
    expect(page).to_have_url(site.url(f"/blog/entrada-qa-{site.name}"))  # moves on after the cover upload
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    expect(page.get_by_alt_text(f"Portada de {title}")).to_be_visible()
    site.shot("qa-content-blog")

    page.get_by_role("button", name="Editar").click()
    page.get_by_label("Título").fill(f"{title} editada")
    page.get_by_role("button", name="Guardar cambios").click()
    expect(page.get_by_role("heading", name=f"{title} editada")).to_be_visible()

    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Eliminar").click()
    page.goto(site.url(f"/blog/entrada-qa-{site.name}"))
    expect(page.get_by_text("Esta entrada no existe o aún no se publica")).to_be_visible()


# ── BLG-02 · gallery project: create with cover, edit, delete ──


def test_blg02_gallery_project_crud_with_cover(site: Site) -> None:
    page = site.page
    title = f"Proyecto QA {site.name}"
    slug = f"proyecto-qa-{site.name}"
    page.goto(site.url("/galeria"))
    page.get_by_role("button", name="Nuevo proyecto").click()
    page.get_by_label("Título").fill(title)
    page.get_by_label("Identificador en la URL (slug)").fill(slug)
    page.get_by_label("Resumen").fill("Resumen del proyecto QA.")
    page.get_by_label("Autores").fill("Equipo QA")
    page.get_by_label("Etiquetas (separadas por coma)").fill("qa, e2e")
    page.get_by_label("Descripción (markdown)").fill("Descripción **QA**.")
    page.get_by_label("Estado").select_option(label="Publicado")
    page.get_by_label("Portada (opcional)").set_input_files(files=_png())
    page.get_by_role("button", name="Crear proyecto").click()
    expect(page).to_have_url(site.url(f"/galeria/{slug}"))  # the app moves on after the cover upload
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    expect(page.locator("img[src^='/media/']").first).to_be_visible()
    site.shot("qa-content-gallery")

    page.get_by_role("button", name="Editar").click()
    dialog = page.get_by_role("dialog", name="Editar proyecto")
    dialog.get_by_label("Título").fill(f"{title} editado")
    dialog.get_by_role("button", name="Guardar cambios").click()
    expect(page.get_by_role("heading", name=f"{title} editado")).to_be_visible()

    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Eliminar").click()
    page.goto(site.url(f"/galeria/{slug}"))
    expect(page.get_by_text("Este proyecto no existe o aún no se publica")).to_be_visible()


# ── BLG-03 · an unknown slug gets a friendly page, not a crash ──


def test_blg03_unknown_slugs_show_friendly_not_found(site: Site) -> None:
    page = site.page
    page.goto(site.url("/blog/no-existe-qa"))
    expect(page.get_by_text("Esta entrada no existe o aún no se publica")).to_be_visible()
    expect(page.get_by_role("link", name="Ver el blog")).to_be_visible()
    page.goto(site.url("/galeria/no-existe-qa"))
    expect(page.get_by_text("Este proyecto no existe o aún no se publica")).to_be_visible()
    expect(page.get_by_role("link", name="Ver la galería")).to_be_visible()
    site.shot("qa-content-not-found")


# ── BLG-04 · hostile markdown is shown, never run ──


def test_blg04_markdown_never_runs_scripts(site: Site) -> None:
    page = site.page
    slug = f"entrada-xss-{site.name}"
    page.goto(site.url("/blog"))
    page.get_by_role("button", name="Nueva entrada").click()
    page.get_by_label("Título").fill(f"XSS QA {site.name}")
    page.get_by_label("Identificador en la URL (slug)").fill(slug)
    page.get_by_label("Contenido (markdown)").fill(HOSTILE)
    page.get_by_label("Publicada (visible para todos)").check()
    page.get_by_role("button", name="Crear entrada").click()
    expect(page).to_have_url(site.url(f"/blog/{slug}"))
    expect(page.get_by_text("seguro").first).to_be_visible()
    article = page.locator("main")
    expect(article.locator("script")).to_have_count(0)
    expect(article.locator("img[onerror]")).to_have_count(0)
    assert page.evaluate("window.__qa_xss") is None  # noqa: S101
    site.shot("qa-content-xss")
