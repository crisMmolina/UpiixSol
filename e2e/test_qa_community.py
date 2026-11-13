"""QA community and reactions in a real browser (UPS-054): docs/PRUEBAS-CAMPUS.md §7 and §8, per viewport.

A fresh account (not in any club) sees the channel list and the "Unirme al club" notice; the member posts
with an image, comments, reacts (state survives a reload, a double click never duplicates) and the
superadmin hides the post (General belongs to no academy, so no academy admin moderates it). Tests run
in order on one site per viewport and sign in once per role (login is rate-limited); registration signs
the new account in by itself.
"""

from playwright.sync_api import Page, expect

from e2e.conftest import Site
from e2e.test_flow import MEMBER, SUPERADMIN, _png_bytes, sign_in, sign_out

TEXT = "Publicación QA {name}"


def _post(page: Page, site: Site):
    return page.locator("article", has_text=TEXT.format(name=site.name))


def _like(page: Page, site: Site):
    return _post(page, site).get_by_role("group", name="Reacciones").get_by_role("button", name="Me gusta")


def test_com01_04_new_account_sees_channels_and_join_notice(site: Site) -> None:
    sign_out(site.page)
    page = site.page
    page.goto(site.url("/login"))
    page.get_by_role("tab", name="Crear cuenta").click()
    page.get_by_label("Nombre completo").fill("Quique QA Comunidad")
    page.get_by_label("Número de boleta").fill("2026888001" if site.name == "desktop" else "2026888002")
    page.get_by_role("textbox", name="Correo", exact=True).fill(f"qa.com.{site.name}@upiixsol.dev")
    page.get_by_label("Contraseña", exact=True).fill("una-clave-segura")
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Crear cuenta").last.click()
    expect(page).to_have_url(site.url("/"))

    page.goto(site.url("/comunidad?canal=upiixia"))
    for name in ("Feed", "General", "UpiixIA"):
        expect(page.get_by_role("button", name=name).first).to_be_attached()
    notice = page.get_by_text("únete al club")
    expect(notice).to_be_visible()
    expect(page.get_by_label("Escribe en #upiixia")).to_have_count(0)
    site.shot("qa-community-join")
    page.get_by_role("button", name="Unirme al club").click()
    expect(page.get_by_label("Escribe en #upiixia")).to_be_visible()
    expect(notice).to_have_count(0)


def test_com05_member_posts_with_image_and_comments(site: Site) -> None:
    sign_in(site, MEMBER, "/comunidad?canal=general")
    page = site.page
    page.get_by_label("Escribe en #general").fill(TEXT.format(name=site.name))
    page.locator('input[type="file"][name="image"]').set_input_files(
        files=[{"name": "qa.png", "mimeType": "image/png", "buffer": _png_bytes()}]
    )
    page.get_by_role("button", name="Publicar").click()
    post = _post(page, site)
    expect(post.locator("img[src^='/media/']")).to_be_visible()

    post.get_by_role("button", name="0 comentarios").click()
    post.get_by_label("Escribe un comentario").fill("Comentario QA")
    post.get_by_role("button", name="Comentar", exact=True).click()
    expect(post.get_by_text("Comentario QA")).to_be_visible()
    expect(post.get_by_role("button", name="1 comentario")).to_be_visible()
    site.shot("qa-community-post")


def test_rea01_03_reaction_persists_and_never_duplicates(site: Site) -> None:
    page = site.page
    post = _post(page, site)
    post.get_by_role("button", name="Agregar reacción").click()
    page.get_by_role("button", name="Me gusta").first.click()
    like = _like(page, site)
    expect(like).to_have_attribute("aria-pressed", "true")
    expect(like).to_have_attribute("aria-label", "Me gusta: 1")

    page.reload()
    like = _like(page, site)
    expect(like).to_have_attribute("aria-pressed", "true")  # REA-03: marked as mine after reload
    expect(like).to_have_attribute("aria-label", "Me gusta: 1")

    like.click()  # un-react
    expect(like).to_have_attribute("aria-pressed", "false")
    page.reload()
    expect(_post(page, site)).to_be_visible()
    expect(_like(page, site)).to_have_count(0)  # nobody reacts: the kind goes back behind "+"

    _post(page, site).get_by_role("button", name="Agregar reacción").click()
    page.get_by_role("button", name="Me gusta").first.click()
    like = _like(page, site)
    expect(like).to_be_enabled()
    like.dblclick()  # REA-02: the toggle locks while saving, so a double click never makes two
    expect(like).to_be_enabled()
    expect(_post(page, site).get_by_role("button", name="Me gusta: 2")).to_have_count(0)
    page.reload()
    expect(_post(page, site)).to_be_visible()
    expect(_post(page, site).get_by_role("button", name="Me gusta: 2")).to_have_count(0)
    site.shot("qa-community-reactions")


def test_com06_07_moderator_hides_the_post(site: Site) -> None:
    # General has no academy: only the superadmin moderates it.
    sign_in(site, SUPERADMIN, "/comunidad?canal=general")
    page = site.page
    page.once("dialog", lambda dialog: dialog.accept())
    _post(page, site).get_by_role("button", name="Ocultar publicación").click()
    expect(page.get_by_text("Mensaje oculto por moderación").first).to_be_visible()
    expect(page.get_by_text(TEXT.format(name=site.name))).to_have_count(0)
    site.shot("qa-community-hidden")
