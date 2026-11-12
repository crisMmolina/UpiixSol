"""Layout stability and motion (UPS-033): messages never resize what holds them, the login card keeps its
top edge, tab switches animate the height, guards change the URL and drawers do not pop the phone keyboard.
Boxes are measured in page coordinates (viewport box + scroll), so focusing a field that scrolls the page
does not count as a jump."""

import re
import time
from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Locator, Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in, sign_out

MEMBER = "alumno.demo@upiixsol.dev"
ADMIN_IA = "admin.ia@upiixsol.dev"
TOLERANCE = 0.5  # px: subpixel rounding only

# Card top/height on every animation frame for `ms` after the click (runs inside the page).
SAMPLE_FRAMES = """
  ([selector, ms]) => new Promise((resolve) => {
    const card = document.querySelector(selector);
    const samples = [];
    const start = performance.now();
    const tick = () => {
      const box = card.getBoundingClientRect();
      samples.push([box.top + window.scrollY, box.height]);
      if (performance.now() - start < ms) requestAnimationFrame(tick); else resolve(samples);
    };
    requestAnimationFrame(tick);
  })
"""


def box(locator: Locator) -> tuple[float, float]:
    """(top in page coordinates, height) once the element has settled."""
    rect = locator.evaluate(
        "(el) => { const b = el.getBoundingClientRect(); return [b.top + window.scrollY, b.height]; }"
    )
    return rect[0], rect[1]


def settled(page: Page) -> None:
    """Reduced motion makes transitions instant; one more frame lets ResizeObserver report."""
    page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")


def stable_box(locator: Locator, timeout: float = 3.0) -> tuple[float, float]:
    """The box once two measurements 100 ms apart agree (ResizeObserver → React → motion can take a few
    frames on a busy machine)."""
    page = locator.page
    previous = box(locator)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        page.wait_for_timeout(100)
        current = box(locator)
        if current == pytest.approx(previous, abs=TOLERANCE):
            return current
        previous = current
    return previous


def assert_box(locator: Locator, expected: tuple[float, float], timeout: float = 3.0) -> None:
    """Waits (like expect) for the box to match: a message that resized it would keep it resized."""
    deadline = time.monotonic() + timeout
    current = box(locator)
    while current != pytest.approx(expected, abs=TOLERANCE) and time.monotonic() < deadline:
        locator.page.wait_for_timeout(50)
        current = box(locator)
    assert current == pytest.approx(expected, abs=TOLERANCE)  # noqa: S101


def login_card(page: Page) -> Locator:
    return page.get_by_role("region", name="Tu cuenta")


def test_login_card_keeps_top_and_size(site: Site) -> None:
    page = site.page
    sign_out(page)
    page.goto(site.url("/login"))
    card = login_card(page)
    expect(card).to_be_visible()
    top, login_height = stable_box(card)

    # Client checks in Spanish, without moving the card.
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_text("Escribe tu boleta o correo.")).to_be_visible()
    expect(page.get_by_text("Escribe tu contraseña.")).to_be_visible()
    assert_box(card, (top, login_height))

    # Wrong password: the API's error fills the reserved line under the button.
    page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(MEMBER)
    page.get_by_label("Contraseña", exact=True).fill("no-es-la-clave")
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_text("Boleta, correo o contraseña incorrectos.")).to_be_visible()
    assert_box(card, (top, login_height))
    site.shot("layout-login-error")

    # Tab switch: only the height changes (it grows downward), the top stays.
    page.get_by_role("tab", name="Crear cuenta").click()
    expect(page.get_by_label("Nombre completo")).to_be_visible()
    deadline = time.monotonic() + 3
    while box(card)[1] <= login_height + 1 and time.monotonic() < deadline:
        page.wait_for_timeout(50)
    register_top, register_height = stable_box(card)
    assert register_top == pytest.approx(top, abs=TOLERANCE)  # noqa: S101
    assert register_height > login_height  # noqa: S101

    # Every required field is checked locally, in Spanish, and the errors do not resize the card.
    page.get_by_role("button", name="Crear cuenta").last.click()
    for text in (
        "Escribe tu nombre completo.",
        "Escribe tu número de boleta.",
        "Escribe tu correo.",
        "Escribe una contraseña.",
        "Debes aceptar el aviso de privacidad.",
    ):
        expect(page.get_by_text(text)).to_be_visible()
    assert_box(card, (top, register_height))
    site.shot("layout-register-errors")

    # Back to Entrar: same box as the first visit.
    page.get_by_role("tab", name="Entrar").click()
    expect(page.get_by_label("Nombre completo")).to_have_count(0)
    assert_box(card, (top, login_height))


def test_register_conflict_keeps_card_size(site: Site) -> None:
    """A 409 (email or boleta already registered) fits its reserved lines, also at 390 px."""
    page = site.page
    sign_out(page)
    page.goto(site.url("/login?tab=registro"))
    card = login_card(page)
    expect(page.get_by_label("Nombre completo")).to_be_visible()
    start = stable_box(card)
    page.get_by_label("Nombre completo").fill("Cuenta Repetida")
    page.get_by_label("Número de boleta").fill("2026999900" if site.name == "desktop" else "2026999901")
    page.get_by_role("textbox", name="Correo", exact=True).fill(MEMBER)  # already registered
    page.get_by_label("Contraseña", exact=True).fill("una-clave-segura")
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Crear cuenta").last.click()
    expect(page.get_by_text("Ese correo o esa boleta ya tienen cuenta.")).to_be_visible()
    assert_box(card, start)
    site.shot("layout-register-conflict")


@pytest.fixture
def animated_page(browser: Browser, site: Site) -> Iterator[Page]:
    """Same viewport as the site, but with motion on."""
    width, height = site.page.viewport_size["width"], site.page.viewport_size["height"]
    context = browser.new_context(
        viewport={"width": width, "height": height}, reduced_motion="no-preference", locale="es-MX"
    )
    try:
        yield context.new_page()
    finally:
        context.close()


def test_login_tab_switch_animates_height(site: Site, animated_page: Page) -> None:
    page = animated_page
    page.goto(site.url("/login"))
    card = login_card(page)
    expect(card).to_be_visible()
    top, start_height = stable_box(card)
    page.evaluate("document.querySelector('[aria-label=\"Tu cuenta\"]').setAttribute('data-probe', '')")

    page.get_by_role("tab", name="Crear cuenta").click()
    samples = page.evaluate(SAMPLE_FRAMES, ["[data-probe]", 700])
    end_height = samples[-1][1]
    assert end_height > start_height  # noqa: S101
    assert all(abs(sample_top - top) <= TOLERANCE for sample_top, _ in samples)  # noqa: S101
    # Animated: at least one frame sits strictly between the two heights, and it never shrinks on the way.
    between = [h for _, h in samples if start_height + 1 < h < end_height - 1]
    assert between, f"no intermediate frame: {samples[:5]}…"  # noqa: S101
    heights = [h for _, h in samples]
    assert all(b >= a - TOLERANCE for a, b in zip(heights, heights[1:], strict=False))  # noqa: S101


def test_role_guard_changes_the_url(site: Site) -> None:
    page = site.page
    sign_out(page)
    page.goto(site.url("/admin"))
    expect(page).to_have_url(site.url("/login?next=%2Fadmin"))

    sign_in(site, MEMBER)
    page.goto(site.url("/admin"))
    expect(page).to_have_url(site.url("/"))
    expect(page.get_by_role("link", name="Entrar a UpiixIA")).to_be_visible()

    sign_in(site, ADMIN_IA)
    page.goto(site.url("/admin"))
    expect(page).to_have_url(site.url("/panel/academia"))


def test_account_messages_replace_each_other_without_growing(site: Site) -> None:
    sign_in(site, MEMBER, "/cuenta?tab=seguridad")
    page = site.page
    panel = page.get_by_role("tabpanel")
    expect(page.get_by_role("heading", name="Contraseña", exact=True)).to_be_visible()
    start = stable_box(panel)

    password_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Contraseña", exact=True)
    )
    email_form = page.locator("form").filter(has=page.get_by_role("heading", name="Correo", exact=True))
    # Disabled buttons say why.
    expect(password_form.get_by_role("button", name="Cambiar contraseña")).to_be_disabled()
    expect(password_form.get_by_text("Escribe tu contraseña actual.")).to_be_visible()
    expect(email_form.get_by_text("Escribe el nuevo correo.")).to_be_visible()

    password_form.get_by_label("Contraseña actual").fill("no-es-la-clave")
    password_form.get_by_label("Nueva contraseña", exact=True).fill("clave-nueva-1")
    password_form.get_by_label("Confirma la nueva contraseña").fill("clave-nueva-2")
    expect(password_form.get_by_text("Las contraseñas no coinciden.")).to_be_visible()
    assert_box(panel, start)

    password_form.get_by_label("Confirma la nueva contraseña").fill("clave-nueva-1")
    password_form.get_by_role("button", name="Cambiar contraseña").click()
    expect(password_form.get_by_text("La contraseña actual no es correcta.")).to_be_visible()
    assert_box(panel, start)

    email_form.get_by_label("Nuevo correo").fill(ADMIN_IA)
    email_form.get_by_label("Contraseña actual").fill(SEED_PASSWORD)
    email_form.get_by_role("button", name="Cambiar correo").click()
    expect(email_form.get_by_text("Ese correo ya está registrado.")).to_be_visible()
    # One status line per tab: the password form's message was replaced, not stacked.
    expect(password_form.get_by_text("Revisa los campos marcados.")).to_have_count(0)
    assert_box(panel, start)
    site.shot("layout-account-security")

    # Perfil: a too-short nickname is explained in Spanish before any request.
    page.get_by_role("tab", name="Perfil").click()
    page.get_by_label("Apodo").fill("A")
    page.get_by_role("button", name="Guardar perfil").click()
    expect(page.get_by_text("Usa al menos 2 caracteres.")).to_be_visible()
    expect(page.get_by_text(re.compile("String should have"))).to_have_count(0)


def test_account_invalid_email_and_tab_bar_do_not_move(site: Site) -> None:
    # Still signed in as MEMBER from the previous test: the API allows 5 logins per minute per IP.
    page = site.page
    page.goto(site.url("/cuenta"))
    tablist = page.get_by_role("tablist", name="Secciones")
    expect(page.get_by_role("heading", name="Datos del perfil")).to_be_visible()
    # The provisional-password notice keeps its height on both tabs: the tab bar does not jump.
    expect(page.get_by_text("Estás usando una contraseña provisional")).to_be_visible()
    bar = stable_box(tablist)
    page.get_by_role("tab", name="Seguridad").click()
    expect(page.get_by_role("heading", name="Contraseña", exact=True)).to_be_visible()
    assert_box(tablist, bar)

    panel = page.get_by_role("tabpanel")
    start = stable_box(panel)
    email_form = page.locator("form").filter(has=page.get_by_role("heading", name="Correo", exact=True))
    email_form.get_by_label("Nuevo correo").fill("nombre@dominio")
    email_form.get_by_label("Contraseña actual").fill(SEED_PASSWORD)
    email_form.get_by_role("button", name="Cambiar correo").click()
    expect(email_form.get_by_text("Escribe un correo válido.")).to_be_visible()
    assert_box(panel, start)
    site.shot("layout-account-invalid-email")


def test_drawer_does_not_focus_a_text_field_on_phones(site: Site) -> None:
    if site.name != "mobile":
        pytest.skip("the lesson drawer exists only below lg")
    page = site.page  # still signed in as MEMBER (login rate limit, see above)
    page.goto(site.url("/a/upiixia/clases/3"))
    page.get_by_role("button", name="Contenido").click()
    drawer = page.get_by_role("dialog", name="Contenido de la ruta")
    expect(drawer).to_be_visible()
    settled(page)
    assert page.evaluate("document.activeElement?.tagName") != "INPUT"  # noqa: S101
    page.keyboard.press("Escape")
    expect(drawer).to_be_hidden()
