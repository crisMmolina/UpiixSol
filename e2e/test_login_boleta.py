"""Sign in with boleta or email (UPS-044): a member registers, signs out and signs in with the boleta; a
superadmin (no boleta) signs in with the email in the same field; a wrong boleta gets the generic error."""

import re

from playwright.sync_api import expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import SUPERADMIN, sign_out

PASSWORD = "boleta-segura-1"  # noqa: S105 · created by this test


def fill_login(site: Site, identifier: str, password: str) -> None:
    page = site.page
    page.goto(site.url("/login"))
    page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(identifier)
    page.get_by_label("Contraseña", exact=True).fill(password)
    page.get_by_role("button", name="Entrar").click()


def test_member_registers_and_signs_in_with_the_boleta(site: Site) -> None:
    page = site.page
    boleta = "2026055501" if site.name == "desktop" else "2026055502"
    sign_out(page)
    page.goto(site.url("/login?tab=registro"))
    page.get_by_label("Nombre completo").fill("Bruno Boleta Díaz")
    page.get_by_label("Número de boleta").fill(boleta)
    page.get_by_role("textbox", name="Correo", exact=True).fill(f"bruno.{site.name}@alumno.ipn.mx")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_label(re.compile("aviso de privacidad", re.I)).check()
    page.get_by_role("button", name="Crear cuenta").last.click()
    expect(page).not_to_have_url(re.compile(r"/login"))

    sign_out(page)
    fill_login(site, boleta, PASSWORD)
    expect(page).not_to_have_url(re.compile(r"/login"))
    site.shot("login-boleta")


def test_superadmin_signs_in_with_the_email_in_the_same_field(site: Site) -> None:
    sign_out(site.page)
    fill_login(site, SUPERADMIN, SEED_PASSWORD)
    expect(site.page).not_to_have_url(re.compile(r"/login"))


def test_a_wrong_boleta_gets_the_generic_error(site: Site) -> None:
    sign_out(site.page)
    fill_login(site, "2026999999", SEED_PASSWORD)
    expect(site.page.get_by_text("Boleta, correo o contraseña incorrectos.")).to_be_visible()
    expect(site.page).to_have_url(re.compile(r"/login"))
