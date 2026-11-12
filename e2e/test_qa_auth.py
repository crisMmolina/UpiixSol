"""QA auth and session (UPS-053): docs/PRUEBAS-CAMPUS.md §1, AUTH-01…07, in a real browser.

The access token lives only in memory and the refresh token in an HttpOnly cookie (lib/api.ts), so "expired
or removed access token" is a reload (memory wiped) or a 401 answered by the server once.
"""

import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Page, Route, expect

from e2e.conftest import ROOT, SEED_PASSWORD, Site, _free_port, _wait_ready
from e2e.test_flow import ADMIN_IA, MEMBER, SUPERADMIN, sign_in, sign_out

HOMES = {MEMBER: r"/$", ADMIN_IA: r"/panel/academia(/upiixia)?$", SUPERADMIN: r"/admin$"}
GENERIC = "Boleta, correo o contraseña incorrectos."
# The account menu (the club switcher also has aria-haspopup, but it carries an aria-label).
USER_MENU = 'header button[aria-haspopup="menu"]:not([aria-label])'


def user_menu(page: Page) -> None:
    page.locator(USER_MENU).click()


def log_out(page: Page) -> None:
    user_menu(page)
    page.get_by_role("menuitem", name="Cerrar sesión").click()
    expect(page).to_have_url(re.compile(r"/login"))


def signed_in(page: Page) -> None:
    """The private screen is there and not blank: the account menu (the course player is an immersive view
    with its own top bar instead) and some content in <main>."""
    expect(page).not_to_have_url(re.compile(r"/login"))
    if "/clases/" in page.url:
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        return
    expect(page.locator(USER_MENU)).to_be_visible()
    expect(page.locator("main")).not_to_be_empty()
    assert page.locator("main").inner_text().strip()  # noqa: S101


# ── AUTH-01 · every seed role lands on its home ──────────────


@pytest.mark.parametrize("email", [MEMBER, ADMIN_IA, SUPERADMIN])
def test_each_role_lands_on_its_home(site: Site, email: str) -> None:
    sign_out(site.page)
    site.page.goto(site.url("/login"))
    site.page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(email)
    site.page.get_by_label("Contraseña", exact=True).fill(SEED_PASSWORD)
    site.page.get_by_role("button", name="Entrar").click()
    expect(site.page).to_have_url(re.compile(HOMES[email]))
    signed_in(site.page)


# ── AUTH-03 / AUTH-07 · the session survives a lost access token and F5 ─


@pytest.mark.parametrize(
    "path", ["/cuenta", "/comunidad", "/a/upiixia/rutas", "/a/upiixia/clases/1", "/calendario"]
)
def test_reload_keeps_the_session_without_a_blank_screen(site: Site, path: str) -> None:
    sign_in(site, MEMBER, path)
    expect(site.page).to_have_url(re.compile(re.escape(path)))
    site.page.reload()  # wipes the in-memory access token: the refresh cookie must restore it silently
    expect(site.page).to_have_url(re.compile(re.escape(path)))
    signed_in(site.page)


def test_an_expired_access_token_is_renewed_silently(site: Site) -> None:
    sign_in(site, MEMBER, "/cuenta")
    page = site.page
    signed_in(page)
    answered = {"401": 0}

    def expire_once(route: Route) -> None:
        if answered["401"]:
            route.continue_()
            return
        answered["401"] += 1
        route.fulfill(
            status=401,
            content_type="application/json",
            body='{"error": {"code": "invalid_token", "message": "Tu sesión expiró.", "details": null}}',
        )

    page.route("**/api/home", expire_once)
    with page.expect_response("**/api/auth/refresh") as refresh:
        page.get_by_role("link", name="Inicio").first.click()
    assert answered["401"] == 1 and refresh.value.status == 200  # noqa: S101
    expect(page).to_have_url(re.compile(r"/$"))
    signed_in(page)
    expect(page.get_by_text("Tu sesión expiró")).to_have_count(0)


# ── AUTH-04 / AUTH-05 · logout ───────────────────────────────


def test_back_after_logout_shows_no_private_data(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    page = site.page
    signed_in(page)
    user_menu(page)
    page.get_by_role("menuitem", name="Mi cuenta").click()  # a private page in the history
    expect(page.get_by_text("alumno.demo@upiixsol.dev").first).to_be_visible()
    log_out(page)
    page.go_back()
    expect(page).to_have_url(re.compile(r"/login"))
    expect(page.get_by_text("alumno.demo@upiixsol.dev")).to_have_count(0)
    expect(page.locator(USER_MENU)).to_have_count(0)


def test_a_refresh_token_reused_after_logout_is_401(site: Site) -> None:
    sign_in(site, MEMBER, "/")
    page = site.page
    signed_in(page)
    old = next(c for c in page.context.cookies() if "refresh" in c["name"])
    log_out(page)
    page.context.add_cookies([old])  # an attacker replays the cookie captured before the logout
    reused = page.request.post(site.url("/api/auth/refresh"), headers={"X-Requested-With": "fetch"})
    assert reused.status == 401, reused.text()  # noqa: S101


# ── AUTH-06 · private routes redirect to login and come back ─


@pytest.mark.parametrize(
    ("path", "email"), [("/admin", SUPERADMIN), ("/panel/academia", ADMIN_IA), ("/cuenta", MEMBER)]
)
def test_private_routes_redirect_to_login_and_back(site: Site, path: str, email: str) -> None:
    sign_out(site.page)
    page = site.page
    page.goto(site.url(path))
    expect(page).to_have_url(
        re.compile(
            r"/login\?next=" + re.escape(path.replace("/", "%2F")) + "|/login\\?next=" + re.escape(path)
        )
    )
    page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(email)
    page.get_by_label("Contraseña", exact=True).fill(SEED_PASSWORD)
    page.get_by_role("button", name="Entrar").click()
    expect(page).to_have_url(re.compile(re.escape(path) + r"(/[a-z]+)?$"))
    signed_in(page)


# ── AUTH-02 · wrong passwords: generic error, then 429 ───────


@pytest.fixture(scope="module")
def rate_limited_server() -> Iterator[str]:
    """Its own server with the rate limit ON (the shared e2e server turns it off to log in many times)."""
    workdir = tempfile.TemporaryDirectory(prefix="upiixsol-e2e-rl-", ignore_cleanup_errors=True)
    env = {
        **os.environ,
        "ENV": "dev",
        "DATABASE_URL": f"sqlite:///{workdir.name}/e2e.db",
        "MEDIA_DIR": f"{workdir.name}/media",
        "COOKIE_SECURE": "false",
        "RATELIMIT_ENABLED": "true",
        "REQUIRE_PASSWORD_CHANGE": "false",
    }
    for module in (["alembic", "upgrade", "head"], ["app.seed"]):
        subprocess.run([sys.executable, "-m", *module], cwd=ROOT, env=env, check=True, capture_output=True)  # noqa: S603
    port = _free_port()
    server = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_ready(url, server)
        yield url
    finally:
        server.terminate()
        server.wait(timeout=10)
        workdir.cleanup()


def test_wrong_passwords_get_a_generic_error_then_429(browser: Browser, rate_limited_server: str) -> None:
    """5 failed logins per IP and minute: an unknown account and a wrong password get the same generic
    message (no enumeration), and the 6th try is rate limited."""
    context = browser.new_context(reduced_motion="reduce", locale="es-MX")
    page = context.new_page()
    try:
        page.goto(f"{rate_limited_server}/login")
        statuses: list[int] = []
        for email in ["nadie@upiixsol.dev"] + [MEMBER] * 5:
            page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(email)
            page.get_by_label("Contraseña", exact=True).fill("no-es-la-clave")
            with page.expect_response("**/api/auth/login") as answer:
                page.get_by_role("button", name="Entrar").click()
            statuses.append(answer.value.status)
            if len(statuses) <= 5:
                expect(page.get_by_text(GENERIC)).to_be_visible()
        assert statuses == [401] * 5 + [429], statuses  # noqa: S101
        expect(page.get_by_text(re.compile("Demasiados intentos"))).to_be_visible()
    finally:
        context.close()
