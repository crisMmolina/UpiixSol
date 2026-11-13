"""Calendar, blog and gallery (UPS-034): switching month, view or drafts never leaves the previous data under
the new heading, `?dia=` and the visible month stay in sync, the month grid keeps its height, the day detail
comes into view, "Ver borradores" lists only drafts and the event form shows field errors in reserved space.

One sign-in per viewport (the module's server is shared by its tests). Seed events are relative to today
(club time): "Taller: tu primera red neuronal" in 3 days at 17:00 and "Noche de proyectos" in 10 days."""

import contextlib
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import Locator, Page, Route, expect

from e2e.conftest import Site
from e2e.test_flow import sign_in
from e2e.test_layout_stability import TOLERANCE, box, stable_box

SUPERADMIN = "superadmin1@upiixsol.dev"
WORKSHOP = "Taller: tu primera red neuronal"
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre"]  # fmt: skip
_signed_in: set[str] = set()


def club_today() -> date:
    return datetime.now(ZoneInfo("America/Mexico_City")).date()


def month_heading(day: date) -> re.Pattern[str]:
    return re.compile(rf"^{MONTHS[day.month - 1]} de {day.year}$", re.IGNORECASE)


def as_superadmin(site: Site, path: str) -> Page:
    """Signs in once per viewport (login is rate limited), then just navigates."""
    if site.base_url not in _signed_in:
        sign_in(site, SUPERADMIN, path)
        _signed_in.add(site.base_url)
    site.page.goto(site.url(path))
    return site.page


def grid(page: Page) -> Locator:
    return page.locator("[aria-busy]").first


def loaded(page: Page) -> None:
    expect(grid(page)).to_have_attribute("aria-busy", "false")


class Held:
    """Holds matching API requests until released, like a slow network."""

    def __init__(self, page: Page, pattern: str) -> None:
        self.page, self.pattern = page, pattern
        self.routes: list[Route] = []
        page.route(pattern, lambda route: self.routes.append(route))

    def release(self) -> None:
        self.page.unroute(self.pattern)
        for route in self.routes:
            with contextlib.suppress(Exception):  # the request may have been cancelled meanwhile
                route.continue_()


def test_month_switch_shows_skeleton_never_the_previous_month(site: Site) -> None:
    workshop = club_today() + timedelta(days=3)
    page = as_superadmin(site, f"/calendario?dia={workshop.isoformat()}")
    loaded(page)
    page.get_by_role("button", name="Quitar filtro").click()
    month_list = page.get_by_role("region", name="Eventos del mes")
    expect(month_list.get_by_text(WORKSHOP)).to_be_visible()
    before = stable_box(grid(page))

    held = Held(page, "**/api/events?**")
    page.get_by_role("button", name="Mes siguiente").click()
    nxt = (workshop.replace(day=1) + timedelta(days=32)).replace(day=1)
    expect(page.get_by_role("heading", name=month_heading(nxt))).to_be_visible()
    expect(grid(page)).to_have_attribute("aria-busy", "true")
    expect(page.get_by_text(WORKSHOP)).to_have_count(0)  # not in the grid, not in the list below
    assert box(grid(page)) == pytest.approx(before, abs=TOLERANCE)  # noqa: S101

    page.get_by_role("button", name="Lista").click()
    expect(page.get_by_role("heading", name="Próximos eventos")).to_be_visible()
    expect(page.get_by_text(WORKSHOP)).to_have_count(0)  # the month's rows never show under "Lista"
    held.release()
    expect(page.locator("main li").get_by_text(WORKSHOP)).to_be_visible()

    page.get_by_role("button", name="Mes", exact=True).click()
    loaded(page)
    assert box(grid(page)) == pytest.approx(before, abs=TOLERANCE)  # noqa: S101 (fixed cell height)
    site.shot("content-1-month-switch")


def test_selected_day_and_url_keep_the_month_in_sync(site: Site) -> None:
    workshop = club_today() + timedelta(days=3)
    page = as_superadmin(site, f"/calendario?dia={workshop.isoformat()}")
    expect(page.get_by_role("heading", name=month_heading(workshop))).to_be_visible()
    detail = page.get_by_role("region", name="Eventos del día seleccionado")
    expect(detail.get_by_text(WORKSHOP)).to_be_visible()

    # Leaving the month drops the day (it is no longer in the grid): no "Sin eventos este día" for a
    # day that has events, and the URL matches what is shown.
    page.get_by_role("button", name="Mes siguiente").click()
    expect(page).not_to_have_url(re.compile(r"dia="))
    expect(page.get_by_role("region", name="Eventos del mes")).to_be_visible()
    page.get_by_role("button", name="Mes anterior").click()
    expect(page.get_by_role("heading", name=month_heading(workshop))).to_be_visible()

    # A day of another month (link, back button) moves the grid to that month.
    far = (workshop.replace(day=1) + timedelta(days=70)).replace(day=15)
    page.goto(site.url(f"/calendario?dia={far.isoformat()}"))
    expect(page.get_by_role("heading", name=month_heading(far))).to_be_visible()
    page.goto(site.url(f"/calendario?dia={workshop.isoformat()}"))
    expect(page.get_by_role("heading", name=month_heading(workshop))).to_be_visible()
    expect(detail.get_by_text(WORKSHOP)).to_be_visible()


def test_picking_a_day_brings_its_events_into_view(site: Site) -> None:
    workshop = club_today() + timedelta(days=3)
    page = as_superadmin(site, f"/calendario?dia={workshop.isoformat()}")
    page.get_by_role("button", name="Quitar filtro").click()
    loaded(page)
    page.evaluate("window.scrollTo(0, 0)")
    page.get_by_role("button", name=re.compile(r", 1 evento$")).first.click()
    detail = page.get_by_role("region", name="Eventos del día seleccionado")
    expect(detail).to_be_visible()
    expect(detail).to_be_in_viewport()
    site.shot("content-2-day-detail")


def test_event_form_shows_a_field_error_for_a_bad_link(site: Site) -> None:
    page = as_superadmin(site, "/calendario")
    page.get_by_role("button", name="Nuevo evento").click()
    dialog = page.get_by_role("dialog", name="Nuevo evento")
    form = dialog.locator("form")
    dialog.get_by_label("Título").fill("Charla AUD-link")
    height = stable_box(form)[1]
    dialog.get_by_label("Link (opcional)").fill("no es un enlace")
    dialog.get_by_role("button", name="Publicar evento").click()
    expect(dialog.get_by_text("Escribe un enlace que empiece con https://.")).to_be_visible()
    expect(dialog.get_by_label("Link (opcional)")).to_have_attribute("aria-invalid", "true")
    assert stable_box(form)[1] == pytest.approx(height, abs=TOLERANCE)  # noqa: S101 (reserved lines)
    dialog.get_by_label("Link (opcional)").fill("https://upiixsol.dev/charla")
    expect(dialog.get_by_text("Escribe un enlace que empiece con https://.")).to_have_count(0)
    dialog.get_by_role("button", name="Cerrar").click()
    expect(dialog).to_be_hidden()


def test_drafts_toggle_lists_only_drafts(site: Site) -> None:
    page = as_superadmin(site, "/blog")
    page.get_by_role("button", name="Nueva entrada").click()
    dialog = page.get_by_role("dialog", name="Nueva entrada")
    dialog.get_by_label("Título").fill(f"Borrador AUD {site.name}")
    dialog.get_by_label("Contenido (markdown)").fill("Aún sin publicar.")
    dialog.get_by_role("button", name="Crear entrada").click()
    expect(page).to_have_url(re.compile(r"/blog/borrador-aud-"))

    page.goto(site.url("/blog"))
    expect(page.get_by_role("heading", name="Más recientes")).to_be_visible()
    featured = page.locator("main a[href^='/blog/'] h2").first.inner_text()
    held = Held(page, "**/api/blog?**")
    page.get_by_role("button", name="Ver borradores").click()
    expect(page.get_by_role("button", name="Ver publicadas")).to_be_visible()
    expect(page.locator("main a[href^='/blog/']")).to_have_count(0)  # skeleton, not the published posts
    held.release()
    posts = page.locator("main a[href^='/blog/']")
    expect(posts).to_have_count(1)
    expect(posts.first).to_contain_text(f"Borrador AUD {site.name}")
    expect(page.get_by_text(featured, exact=True)).to_have_count(0)
    site.shot("content-3-blog-drafts")

    page.goto(site.url("/galeria?borradores=1"))
    expect(page.get_by_text("No hay borradores")).to_be_visible()  # the seed has only published projects
