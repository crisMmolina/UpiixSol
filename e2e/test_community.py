"""Community fixes (UPS-035) in a real browser, per viewport: long words wrap, the composer does not jump,
switching channel keeps the list until the new one is ready, a post made while switching stays in its
channel, authors delete their own posts, and a hidden post's image leaves /media.

Tests run in order on one site per viewport and sign in once per role (login is rate-limited)."""

from playwright.sync_api import Page, expect

from e2e.conftest import Site
from e2e.test_flow import ADMIN_IA, MEMBER, _png_bytes, sign_in

POSTS_PAGE = r"/api/channels/\d+/posts\?"
POST_CREATE = r"/api/channels/\d+/posts$"


def _slow_fetch(page: Page, pattern: str, ms: int) -> None:
    """Delays matching API calls inside the page (a Python route handler would block the test itself)."""
    page.evaluate(
        """([pattern, ms]) => {
          const original = window.__fetch ?? window.fetch;
          window.__fetch = original;
          window.fetch = async (input, init) => {
            const url = typeof input === "string" ? input : input.url;
            if (new RegExp(pattern).test(url)) await new Promise((r) => setTimeout(r, ms));
            return original(input, init);
          };
        }""",
        [pattern, ms],
    )


def _normal_fetch(page: Page) -> None:
    page.evaluate("() => { if (window.__fetch) window.fetch = window.__fetch; }")


def test_long_word_wraps_and_composer_keeps_its_place(site: Site) -> None:
    sign_in(site, MEMBER, "/comunidad?canal=general")
    page = site.page
    word = f"{site.name}" + "x" * 440
    page.get_by_label("Escribe en #general").fill(word)
    page.get_by_role("button", name="Publicar").click()
    expect(page.locator("article", has_text=word[:40])).to_be_visible()
    site.shot("community-long-word")  # fails on any horizontal page scroll

    publish = page.get_by_role("button", name="Publicar")
    before = publish.bounding_box()
    publish.click()  # empty: the error takes its reserved line
    expect(page.get_by_text("Escribe algo antes de publicar.")).to_be_visible()
    assert publish.bounding_box() == before

    page.locator('input[type="file"][name="image"]').set_input_files(
        files=[{"name": "vista.png", "mimeType": "image/png", "buffer": _png_bytes()}]
    )
    expect(page.get_by_alt_text("Vista previa de la imagen")).to_be_visible()
    page.get_by_role("button", name="Quitar imagen").click()
    expect(page.get_by_alt_text("Vista previa de la imagen")).to_have_count(0)


def test_switching_channel_keeps_the_list_and_posts_stay_in_their_channel(site: Site) -> None:
    page = site.page
    page.goto(site.url("/comunidad?canal=general"))
    expect(page.locator("article").first).to_be_visible()
    _slow_fetch(page, POSTS_PAGE, 800)
    page.get_by_role("button", name="upiixia").click()
    # While the new channel loads, the old list stays under its own heading: no skeleton, no collapse.
    expect(page.get_by_role("heading", name="#general")).to_be_visible()
    assert page.locator(".skeleton").count() == 0
    assert page.locator("article").count() > 0
    expect(page.get_by_role("heading", name="#upiixia")).to_be_visible()
    _normal_fetch(page)

    marker = f"Publicado durante el cambio {site.name}"
    page.get_by_label("Escribe en #upiixia").fill(marker)
    _slow_fetch(page, POST_CREATE, 1000)
    page.get_by_role("button", name="Publicar").click()
    page.get_by_role("button", name="General").click()
    expect(page.get_by_role("heading", name="#general")).to_be_visible()
    page.wait_for_timeout(1500)  # the POST has answered by now
    expect(page.locator("article", has_text=marker)).to_have_count(0)
    _normal_fetch(page)
    page.get_by_role("button", name="upiixia").click()
    expect(page.locator("article", has_text=marker)).to_have_count(1)


def test_author_deletes_own_post(site: Site) -> None:
    page = site.page
    post = page.locator("article", has_text=f"Publicado durante el cambio {site.name}")
    page.once("dialog", lambda dialog: dialog.accept())
    post.get_by_role("button", name="Borrar mi publicación").click()
    expect(post).to_have_count(0)
    page.reload()
    expect(page.get_by_role("heading", name="#upiixia")).to_be_visible()
    expect(page.locator("article").first).to_be_visible()
    expect(post).to_have_count(0)


def test_hidden_post_image_is_no_longer_public(site: Site) -> None:
    page = site.page
    text = f"Foto para ocultar {site.name}"
    page.goto(site.url("/comunidad?canal=upiixia"))
    page.get_by_label("Escribe en #upiixia").fill(text)
    page.locator('input[type="file"][name="image"]').set_input_files(
        files=[{"name": "ocultar.png", "mimeType": "image/png", "buffer": _png_bytes()}]
    )
    page.get_by_role("button", name="Publicar").click()
    image = page.locator("article", has_text=text).locator("img[src^='/media/']")
    expect(image).to_be_visible()
    src = image.get_attribute("src")
    assert page.request.get(site.url(src)).status == 200

    sign_in(site, ADMIN_IA, "/comunidad?canal=upiixia")
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("article", has_text=text).get_by_role("button", name="Ocultar publicación").click()
    expect(page.get_by_text("Mensaje oculto por moderación").first).to_be_visible()
    expect(page.locator("article", has_text=text)).to_have_count(0)
    assert page.request.get(site.url(src)).status == 404
    site.shot("community-hidden")


def test_skeletons_have_the_shape_of_the_content(site: Site) -> None:
    """Channel row, heading and composer keep their place when the data arrives (390 and 1280 px)."""
    page = site.page
    page.add_init_script(
        """(() => { const original = window.fetch; window.fetch = async (input, init) => {
          const url = typeof input === "string" ? input : input.url;
          if (/\\/api\\/(channels|posts)/.test(url)) await new Promise((r) => setTimeout(r, 1200));
          return original(input, init); }; })()"""
    )
    page.goto(site.url("/comunidad?canal=upiixia"))
    section = page.locator("section[aria-label^='Canal']")
    measure = """(section) => [...section.children].slice(0, 2).map((c) => {
      const r = c.getBoundingClientRect(); return [Math.round(r.y), Math.round(r.height)]; })"""
    nav = page.locator("aside[aria-label='Canales'] > :last-child")
    expect(section.locator(".skeleton").first).to_be_visible()
    loading = (section.evaluate(measure), nav.bounding_box()["height"])
    expect(page.get_by_role("heading", name="#upiixia")).to_be_visible()
    expect(page.locator("article").first).to_be_visible()
    assert (section.evaluate(measure), nav.bounding_box()["height"]) == loading
