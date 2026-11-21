"""Paste many outside addresses at once (UPS-097, spec 003 §Audiences): one box takes a block copied from
Gmail, Outlook or a spreadsheet; no per-campaign cap, only the monthly quota. Same server setup as test_mail.py."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in
from e2e.test_mail_recipients import add_source

SUPERADMIN = "superadmin1@upiixsol.dev"
SHOTS = Path(".uak-shots/UPS-097")


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


def open_persons(site: Site) -> Page:
    sign_in(site, SUPERADMIN, "/")
    page = site.page
    page.goto(site.url("/admin?tab=correos&paso=envio"))  # the audience lives in the last step (UPS-102)
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")
    add_source(page, "Correos de fuera")
    return page


def chip(page: Page, text: str):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("list", name="Fuentes de destinatarios").get_by_text(text, exact=True)


def paste(page: Page, text: str) -> None:
    page.get_by_label("Pegar varios correos").fill(text)
    page.get_by_role("button", name="Agregar todos").click()


def test_paste_many_addresses_separated_by_commas_spaces_and_lines(site: Site) -> None:
    page = open_persons(site)
    paste(page, "a1@example.com, a2@example.com;a3@example.com a4@example.com\na5@example.com\n\ta6@example.com")
    expect(page.get_by_role("status").filter(has_text="Se agregaron 6")).to_be_visible()
    expect(chip(page, "Correos de fuera · 6")).to_be_visible()
    block = "\n".join(f"masivo{i}@example.com" for i in range(150))
    paste(page, block)
    expect(chip(page, "Correos de fuera · 156")).to_be_visible()
    # The list pages the addresses (50 at a time) and the search finds one.
    page.get_by_label("Buscar en la lista").fill("a1@example.com")
    expect(page.get_by_role("button", name="Quitar a1@example.com")).to_be_visible()
    page.get_by_label("Buscar en la lista").fill("")
    site.shot("paste-many")
    page.get_by_role("button", name="Quitar fuente Correos de fuera").click()
    expect(page.get_by_role("list", name="Fuentes de destinatarios")).to_have_count(0)


def test_paste_name_and_angle_bracket_format(site: Site) -> None:
    page = open_persons(site)
    paste(
        page,
        'Ana López <ana@example.com>, "Pérez, Juan" <juan@example.com>\nBeto <BETO@Example.com>; carla@example.com',
    )
    expect(page.get_by_role("status").filter(has_text="Se agregaron 4")).to_be_visible()
    for address in ("ana@example.com", "juan@example.com", "beto@example.com", "carla@example.com"):
        expect(page.get_by_role("button", name=f"Quitar {address}")).to_be_visible()


def test_paste_reports_added_repeated_and_invalid(site: Site) -> None:
    page = open_persons(site)
    paste(page, "uno@example.com")
    paste(page, "uno@example.com, DOS@example.com, dos@example.com, sin-arroba, otro@, tres@example.com")
    expect(page.get_by_role("status").filter(has_text="Se agregaron 2 · 2 repetidos · 2 inválidos")).to_be_visible()
    expect(chip(page, "Correos de fuera · 3")).to_be_visible()
    # The invalid ones stay in the box so they can be fixed.
    box = page.get_by_label("Pegar varios correos")
    expect(box).to_have_value("sin-arroba\notro@")
    box.fill("sin-arroba@example.com")
    page.get_by_role("button", name="Agregar todos").click()
    expect(chip(page, "Correos de fuera · 4")).to_be_visible()
    site.shot("paste-report")


def test_paste_box_at_390_wide(site: Site) -> None:
    page = open_persons(site)
    paste(page, "\n".join(f"fila{i}@example.com" for i in range(40)) + "\nmal-correo")
    expect(page.get_by_role("status").filter(has_text="Se agregaron 40")).to_be_visible()
    box = page.get_by_label("Pegar varios correos")
    button = page.get_by_role("button", name="Agregar todos")
    for control in (box, button):
        control.scroll_into_view_if_needed()
        bounds = control.bounding_box()
        assert bounds is not None
        assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= page.viewport_size["width"]
    assert button.bounding_box()["height"] >= 44
    page.screenshot(path=SHOTS / f"paste-{site.name}.png", full_page=True)
    site.shot("paste-box")
