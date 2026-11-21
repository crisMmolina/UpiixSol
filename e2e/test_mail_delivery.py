"""Delivery detail in the history (UPS-108, spec 006 §Delivery detail): who got each sent email, per status,
and "Usar de nuevo". The campaign endpoints are faked in the browser so every status (bounces, spam, purged
rows) shows up without Mailgun; the rest of the panel talks to the real server."""

import json
import re
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Page, Route, expect

from e2e.conftest import SEED_PASSWORD, Site
from e2e.test_flow import sign_in

SUPERADMIN = "superadmin1@upiixsol.dev"
SENT = 901
PURGED = 902
SUBJECT = "Taller de Python del sábado"
OLD_SUBJECT = "Bienvenida al semestre 2025"
WHEN = "2026-11-19T18:30:00Z"


def _row(i: int, status: str, reason_code: str | None = None, reason: str | None = None) -> dict:
    return {
        "user_id": 100 + i,
        "name": f"Persona {status} {i:02d}",
        "email": f"persona.{status}.{i:02d}@upiixsol.dev",
        "status": status,
        "reason_code": reason_code,
        "reason": reason,
        "updated_at": WHEN,
    }


ROWS = (
    [_row(i, "delivered") for i in range(23)]
    + [
        {**_row(0, "bounced", "bounce", "El buzón no existe o no acepta correo"), "name": "Rita Rebote"},
        {**_row(1, "bounced", "suppress-bounce", "Dirección suprimida por rebotes previos"), "user_id": None, "name": "invitado@example.com", "email": "invitado@example.com"},
        {**_row(0, "failed", "timeout", "El servicio de envío no respondió a tiempo"), "name": "Fabián Fallo"},
        {**_row(0, "complained"), "name": "Sara Spam"},
        {**_row(0, "accepted"), "name": "Camilo Camino"},
    ]
)
COUNTS = {"delivered": 23, "bounced": 2, "failed": 1, "complained": 1, "accepted": 1}


def _campaign(cid: int, subject: str, counts: dict) -> dict:
    return {
        "id": cid,
        "subject": subject,
        "audience": {"kind": "all"},
        "sender": {"id": 1, "nickname": "superadmin1", "avatar_url": None},
        "status": "partial",
        "recipient_count": sum(counts.values()),
        "counts_by_status": counts,
        "created_at": WHEN,
        "sent_at": WHEN,
    }


CAMPAIGNS = {
    SENT: _campaign(SENT, SUBJECT, COUNTS),
    PURGED: _campaign(PURGED, OLD_SUBJECT, {"delivered": 40, "bounced": 3}),
}
CONTENT = {"preheader": "Trae tu laptop", "blocks": [{"type": "paragraph", "text": "Nos vemos el sábado."}]}


def _fake(route: Route) -> None:
    request = route.request
    url = urlparse(request.url)
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    if request.method != "GET":
        route.continue_()
        return
    if url.path == "/api/mail/campaigns":
        route.fulfill(json={"items": list(CAMPAIGNS.values()), "next_cursor": None})
        return
    detail = re.fullmatch(r"/api/mail/campaigns/(\d+)", url.path)
    if detail:
        cid = int(detail.group(1))
        route.fulfill(json={**CAMPAIGNS[cid], "content": CONTENT, "details_purged": cid == PURGED})
        return
    people = re.fullmatch(r"/api/mail/campaigns/(\d+)/recipients", url.path)
    if people:
        rows = [] if int(people.group(1)) == PURGED else ROWS
        if query.get("status"):
            rows = [r for r in rows if r["status"] == query["status"]]
        if query.get("q"):
            q = query["q"].lower()
            rows = [r for r in rows if q in r["name"].lower() or q in r["email"].lower()]
        start = int(query.get("cursor") or 0)
        limit = int(query.get("limit") or 50)
        page = rows[start : start + limit]
        nxt = str(start + limit) if start + limit < len(rows) else None
        route.fulfill(body=json.dumps({"items": page, "next_cursor": nxt}), content_type="application/json")
        return
    route.continue_()


@pytest.fixture(scope="module")
def mail_env() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SEED_DEFAULT_PASSWORD", SEED_PASSWORD)  # the local .env may set another one
        patch.setenv("MAIL_ENABLED", "true")
        patch.setenv("MAIL_BACKEND", "console")
        yield


@pytest.fixture(scope="module")
def site(mail_env: None, site: Site) -> Site:  # noqa: ARG001 - overrides conftest's `site` with mail enabled
    return site


def open_detail(site: Site, subject: str = SUBJECT) -> Page:
    """Superadmin "Correos" tab with the faked campaigns, then the delivery detail of `subject`."""
    sign_in(site, SUPERADMIN, "/")
    page = site.page
    page.unroute("**/api/mail/campaigns**")
    page.route(re.compile(r"/api/mail/campaigns(/|\?|$)"), _fake)
    page.goto(site.url("/admin?tab=correos&paso=contenido"))
    history = page.get_by_role("region", name="Historial")
    history.get_by_role("button", name=f"Ver entregas de {subject}").click()
    detail = page.get_by_role("region", name="Entregas")
    expect(detail.get_by_role("heading", name=subject)).to_be_visible()
    return page


def tab(page: Page, name: str):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("region", name="Entregas").get_by_role("tab", name=re.compile(rf"^{name}"))


def people(page: Page):  # noqa: ANN201 - playwright Locator
    return page.get_by_role("region", name="Entregas").get_by_role("list", name="Personas").get_by_role("listitem")


def test_open_sent_email_shows_counts_and_tabs_per_status(site: Site) -> None:
    page = open_detail(site)
    for name, n in (("Entregados", 23), ("Rebotados", 2), ("Fallidos", 1), ("Marcados como spam", 1), ("En camino", 1), ("Sin enviar", 0)):
        expect(tab(page, name)).to_contain_text(str(n))
    expect(tab(page, "Entregados")).to_have_attribute("aria-selected", "true")
    tab(page, "Sin enviar").click()
    expect(page.get_by_role("region", name="Entregas").get_by_text("Nadie quedó sin enviar")).to_be_visible()
    tab(page, "Marcados como spam").click()
    expect(people(page)).to_have_count(1)
    expect(people(page).first).to_contain_text("Sara Spam")
    tab(page, "Marcados como spam").press("ArrowLeft")  # keyboard: arrows move between tabs
    expect(tab(page, "Fallidos")).to_be_focused()
    site.shot("delivery-tabs")


def test_bounced_tab_lists_people_with_reason(site: Site) -> None:
    page = open_detail(site)
    tab(page, "Rebotados").click()
    expect(people(page)).to_have_count(2)
    rita = people(page).filter(has_text="Rita Rebote")
    expect(rita).to_contain_text("persona.bounced.00@upiixsol.dev")
    expect(rita).to_contain_text("El buzón no existe o no acepta correo")
    expect(rita).to_contain_text("bounce")
    expect(people(page).filter(has_text="Dirección suprimida por rebotes previos")).to_have_count(1)
    tab(page, "Fallidos").click()
    expect(people(page).first).to_contain_text("El servicio de envío no respondió a tiempo")
    site.shot("delivery-bounced")


def test_delivered_tab_lists_people(site: Site) -> None:
    page = open_detail(site)
    first = people(page).first
    expect(first).to_contain_text("Persona delivered 00")
    expect(first).to_contain_text("persona.delivered.00@upiixsol.dev")
    expect(first.locator("time")).to_have_attribute("datetime", WHEN)
    expect(first).not_to_contain_text("undefined")


def test_delivery_search_and_load_more(site: Site) -> None:
    page = open_detail(site)
    expect(people(page)).to_have_count(20)
    page.get_by_role("region", name="Entregas").get_by_role("button", name="Cargar más").click()
    expect(people(page)).to_have_count(23)
    expect(page.get_by_role("region", name="Entregas").get_by_role("button", name="Cargar más")).to_have_count(0)
    page.get_by_role("region", name="Entregas").get_by_role("searchbox", name="Buscar por nombre o correo").fill("delivered.07")
    expect(people(page)).to_have_count(1)
    expect(people(page).first).to_contain_text("Persona delivered 07")
    page.get_by_role("region", name="Entregas").get_by_role("searchbox", name="Buscar por nombre o correo").fill("nadie-asi")
    expect(page.get_by_role("region", name="Entregas").get_by_text("Nadie coincide con la búsqueda")).to_be_visible()


def test_purged_email_says_detail_is_gone(site: Site) -> None:
    page = open_detail(site, OLD_SUBJECT)
    detail = page.get_by_role("region", name="Entregas")
    expect(detail.get_by_text("El detalle por persona se borra al año del envío")).to_be_visible()
    expect(tab(page, "Entregados")).to_contain_text("40")
    expect(detail.get_by_role("list", name="Personas")).to_have_count(0)
    site.shot("delivery-purged")


def test_usar_de_nuevo_opens_the_composer(site: Site) -> None:
    page = open_detail(site)
    page.get_by_role("region", name="Entregas").get_by_role("button", name="Usar de nuevo").click()
    expect(page).to_have_url(re.compile(rf"reusar={SENT}"))
    query = parse_qs(urlparse(page.url).query)
    assert query["tab"] == ["correos"]
    assert query["paso"] == ["plantilla"]
    assert query["reusar"] == [str(SENT)]
    expect(page.get_by_role("tab", name="Correos")).to_have_attribute("aria-selected", "true")


def test_delivery_detail_at_390_wide(site: Site) -> None:
    page = open_detail(site)
    tab(page, "Rebotados").click()
    expect(people(page)).to_have_count(2)
    page.get_by_role("region", name="Entregas").get_by_role("button", name="Volver al historial").click()
    expect(page.get_by_role("region", name="Historial").get_by_role("button", name=f"Ver entregas de {SUBJECT}")).to_be_visible()
    open_detail(site)
    site.shot("delivery-detail")  # raises if the page scrolls horizontally (1280 and 390)
