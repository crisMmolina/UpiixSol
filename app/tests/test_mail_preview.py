"""Email preview (UPS-089, spec 004 §Preview): the same render as send, same scope checks as create."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Academy
from app.models.mail import MailCampaign
from app.services import mail_campaigns
from app.tests.test_mail_campaigns import CAMPAIGNS, FakeTransport, _send, fake  # noqa: F401

PREVIEW = "/api/mail/preview"
BLOCKS = [
    {"kind": "heading", "text": "Hola"},
    {"kind": "paragraph", "text": "Nos vemos *pronto*"},
    {"kind": "button", "label": "Ver", "url": "https://upiixsol.com/x"},
]


def _payload(**extra: object) -> dict:
    return {
        "subject": "Aviso",
        "blocks": BLOCKS,
        "preheader": "Resumen",
        "reply_to": "club@ipn.mx",
        "audience": {"kind": "individual", "emails": ["a@ipn.mx", "b@ipn.mx"]},
    } | extra


def test_preview_returns_the_same_html_as_send(
    as_superadmin: TestClient,
    db: Session,
    fake: FakeTransport,  # noqa: F811
) -> None:
    preview = as_superadmin.post(PREVIEW, json=_payload())
    assert preview.status_code == 200, preview.text
    html, text = preview.json()["html"], preview.json()["text"]
    assert "Nos vemos" in html and "Resumen" in html and "club@ipn.mx" in html
    assert "%recipient" not in html  # sample name and a dummy unsubscribe link
    campaign = as_superadmin.post(CAMPAIGNS, json=_payload()).json()
    _send(as_superadmin, campaign["id"])
    sent = fake.calls[0][0]
    dummy = "https://www.upiixsol.com/api/mail/unsubscribe?t=vista-previa"
    # What send renders, with the per-person variables filled the way the preview fills them.
    filled = sent.html.replace("%recipient.name%", "Ana Ejemplo").replace(
        "%recipient.unsubscribe_url%", dummy
    )
    assert filled == html
    assert (
        sent.text.replace("%recipient.name%", "Ana Ejemplo").replace("%recipient.unsubscribe_url%", dummy)
        == text
    )
    assert db.query(MailCampaign).count() == 1  # the preview stored nothing


def test_preview_scoped_like_create(
    as_admin_ia: TestClient,
    db: Session,
    seeded: dict,
    fake: FakeTransport,  # noqa: F811
) -> None:
    other = Academy(slug="robotica", name="Robótica")
    db.add(other)
    db.flush()
    outside = _payload(audience={"kind": "academy", "academy_id": other.id})
    assert as_admin_ia.post(PREVIEW, json=outside).status_code == 403
    assert as_admin_ia.post(CAMPAIGNS, json=outside).status_code == 403
    own = _payload(audience={"kind": "academy", "academy_id": seeded["academy_id"]})
    assert as_admin_ia.post(PREVIEW, json=own).status_code == 200
    assert as_admin_ia.post(PREVIEW, json=_payload(blocks=[])).status_code == 422
    assert as_admin_ia.post(PREVIEW, json=_payload(reply_to="a@b.mx\nBcc: x@y.mx")).status_code == 422


def test_preview_of_a_legacy_body_campaign(
    as_superadmin: TestClient,
    fake: FakeTransport,  # noqa: F811
) -> None:
    payload = {"subject": "Aviso", "body": "Hola legado", "audience": {"kind": "all"}}
    response = as_superadmin.post(PREVIEW, json=payload)
    assert response.status_code == 200, response.text
    assert "Hola legado" in response.json()["html"]
    assert "%recipient" not in response.json()["html"]


def test_event_block_needs_a_sender_to_resolve(db: Session) -> None:
    event = {
        "kind": "event",
        "title": "Taller",
        "start": "2026-12-01T20:00:00Z",
        "end": "2026-12-01T22:00:00Z",
    }
    with pytest.raises(AppError) as error:
        mail_campaigns._render_email(
            db, None, subject="A", content=[event], preheader=None, reply_to=None,
            club=None, footer_reason="", ics_token=None,
        )  # fmt: skip
    assert error.value.status == 422
