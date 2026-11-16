"""A superadmin deletes anyone's comment; a member sees no delete button on other people's (UPS-070)."""

from playwright.sync_api import expect

from e2e.conftest import ROOT, VIEWPORTS, Site
from e2e.test_flow import MEMBER, SUPERADMIN, sign_in

POST = "Publicación para moderar {name}"
COMMENT = "Comentario ajeno {name}"


def test_superadmin_deletes_a_members_comment(site: Site) -> None:
    sign_in(site, MEMBER, "/comunidad?canal=general")
    page = site.page
    page.get_by_label("Escribe en #general").fill(POST.format(name=site.name))
    page.get_by_role("button", name="Publicar").click()
    post = page.locator("article", has_text=POST.format(name=site.name))
    post.get_by_role("button", name="0 comentarios").click()
    post.get_by_label("Escribe un comentario").fill(COMMENT.format(name=site.name))
    post.get_by_role("button", name="Comentar", exact=True).click()
    expect(post.get_by_text(COMMENT.format(name=site.name))).to_be_visible()
    expect(post.get_by_role("button", name="Borrar mi comentario")).to_be_visible()

    sign_in(site, SUPERADMIN, "/comunidad?canal=general")
    post = page.locator("article", has_text=POST.format(name=site.name))
    post.get_by_role("button", name="1 comentario").click()
    delete = post.get_by_role("button", name="Borrar comentario", exact=True)
    expect(delete).to_be_visible()
    shots = ROOT / ".uak-shots" / "UPS-070"
    shots.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=shots / f"{VIEWPORTS[site.name][0]}.png", full_page=True)
    page.once("dialog", lambda dialog: dialog.accept())
    delete.click()
    expect(post.get_by_text(COMMENT.format(name=site.name))).to_have_count(0)
    page.reload()
    post = page.locator("article", has_text=POST.format(name=site.name))
    expect(post.get_by_role("button", name="0 comentarios")).to_be_visible()
