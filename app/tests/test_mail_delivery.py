"""Delivery detail per sent email (UPS-106, spec 006 §Delivery detail): who was delivered, bounced, failed or
marked it as spam, with the reason in Spanish, and the content of the email for "Usar de nuevo".

Campaigns and their recipients are inserted directly: the detail only reads them.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Academy, User
from app.models.mail import MailCampaign, MailRecipient
from app.services import mail_delivery, mail_retention
from app.services.mail_blocks import Blocks

CAMPAIGNS = "/api/mail/campaigns"


def _user(db: Session, email: str) -> User:
    return db.query(User).filter_by(email=email).one()


def _campaign(
    db: Session,
    *,
    academy_id: int | None = None,
    body: str = "Hola",
    content: list[dict[str, Any]] | None = None,
    preheader: str | None = None,
    finished_at: datetime | None = None,
) -> MailCampaign:
    campaign = MailCampaign(
        sender_id=_user(db, "superadmin1@upiixsol.dev").id,
        academy_id=academy_id,
        audience_kind="individual",
        audience_params={"user_ids": []},
        subject="Aviso",
        body=body,
        content=content,
        preheader=preheader,
        status="sent",
        finished_at=finished_at,
    )
    db.add(campaign)
    db.flush()
    return campaign


def _recipient(
    db: Session,
    campaign: MailCampaign,
    email: str,
    name: str,
    status: str = "delivered",
    error_code: str | None = None,
    user_id: int | None = None,
) -> MailRecipient:
    row = MailRecipient(
        campaign_id=campaign.id,
        user_id=user_id,
        email=email,
        name=name,
        status=status,
        error_code=error_code,
        unsubscribe_token_hash=f"{campaign.id}-{email}".ljust(64, "x")[:64],
    )
    db.add(row)
    db.flush()
    campaign.recipient_count += 1
    return row


def _rows(client: TestClient, campaign_id: int, **params: Any) -> dict:
    response = client.get(f"{CAMPAIGNS}/{campaign_id}/recipients", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_delivery_rows_by_status_with_name_email_and_time(as_superadmin: TestClient, db: Session) -> None:
    campaign = _campaign(db)
    ana = _recipient(db, campaign, "ana@ipn.mx", "Ana López", "delivered")
    _recipient(db, campaign, "beto@ipn.mx", "Beto Ruiz", "bounced", "bounce")
    _recipient(db, campaign, "caro@ipn.mx", "Caro Díaz", "failed", "timeout")
    _recipient(db, campaign, "dani@ipn.mx", "Dani Mora", "complained")
    _recipient(db, campaign, "eli@ipn.mx", "Eli Paz", "accepted")
    _recipient(db, campaign, "fer@ipn.mx", "Fer Gil", "pending")

    everyone = _rows(as_superadmin, campaign.id)
    assert [row["email"] for row in everyone["items"]] == [
        "ana@ipn.mx",
        "beto@ipn.mx",
        "caro@ipn.mx",
        "dani@ipn.mx",
        "eli@ipn.mx",
        "fer@ipn.mx",
    ]
    assert everyone["next_cursor"] is None

    delivered = _rows(as_superadmin, campaign.id, status="delivered")["items"]
    assert len(delivered) == 1
    row = delivered[0]
    assert row["user_id"] is None
    assert row["name"] == "Ana López"
    assert row["email"] == "ana@ipn.mx"
    assert row["status"] == "delivered"
    assert row["reason_code"] is None
    assert row["reason"] is None
    assert datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC) == ana.updated_at.replace(tzinfo=UTC)

    bounced = _rows(as_superadmin, campaign.id, status="bounced")["items"]
    assert [(r["email"], r["reason_code"]) for r in bounced] == [("beto@ipn.mx", "bounce")]
    others = {
        "failed": "caro@ipn.mx",
        "complained": "dani@ipn.mx",
        "accepted": "eli@ipn.mx",
        "pending": "fer@ipn.mx",
    }
    for status, email in others.items():
        assert [r["email"] for r in _rows(as_superadmin, campaign.id, status=status)["items"]] == [email]


REASONS = {
    # Mailgun `failed` (permanent) reasons, stored by the webhook (UPS-077)
    "bounce": "El buzón no existe o no acepta correo",
    "suppress-bounce": "Dirección suprimida por rebotes previos",
    "suppress-unsubscribe": "Dirección suprimida: la persona se dio de baja",
    "suppress-complaint": "Dirección suprimida: marcó un correo anterior como spam",
    "old": "No se pudo entregar después de varios intentos",
    "generic": "El servidor lo rechazó",
    "espblock": "El proveedor del destinatario bloqueó el correo",
    "hardfail": "El servidor lo rechazó de forma definitiva",
    # send errors (app/services/mailgun.py, mail_campaigns._deliver)
    "auth": "El servicio de envío rechazó la configuración",
    "rate_limited": "El servicio de envío limitó los envíos",
    "provider_error": "El servicio de envío falló",
    "rejected": "El servicio de envío rechazó el mensaje",
    "network": "Error de red al enviarlo",
    "timeout": "El servicio de envío no respondió a tiempo",
    "bad_response": "El servicio de envío dio una respuesta inesperada",
}


@pytest.mark.parametrize(("code", "text"), REASONS.items())
def test_bounce_and_failure_reasons_in_spanish(code: str, text: str) -> None:
    assert mail_delivery.reason_text("bounced", code) == text
    assert mail_delivery.reason_text("failed", code) == text


def test_bounce_and_failure_reasons_in_spanish_in_the_rows(as_superadmin: TestClient, db: Session) -> None:
    campaign = _campaign(db)
    _recipient(db, campaign, "beto@ipn.mx", "Beto", "bounced", "suppress-bounce")
    _recipient(db, campaign, "caro@ipn.mx", "Caro", "failed", "network")
    _recipient(db, campaign, "dani@ipn.mx", "Dani", "delivered", "generic")  # a stale code is not a reason
    rows = {row["email"]: row for row in _rows(as_superadmin, campaign.id)["items"]}
    assert rows["beto@ipn.mx"]["reason"] == "Dirección suprimida por rebotes previos"
    assert rows["caro@ipn.mx"]["reason"] == "Error de red al enviarlo"
    assert rows["dani@ipn.mx"]["reason"] is None
    assert rows["dani@ipn.mx"]["reason_code"] is None


def test_unknown_reason_shows_the_code(as_superadmin: TestClient, db: Session) -> None:
    assert mail_delivery.reason_text("bounced", "mailbox-full-x") == "Motivo: mailbox-full-x"
    assert mail_delivery.reason_text("failed", None) is None
    assert mail_delivery.reason_text("delivered", "bounce") is None
    assert mail_delivery.reason_text("complained", None) is None
    campaign = _campaign(db)
    _recipient(db, campaign, "beto@ipn.mx", "Beto", "bounced", "raro")
    row = _rows(as_superadmin, campaign.id)["items"][0]
    assert (row["reason_code"], row["reason"]) == ("raro", "Motivo: raro")


def test_delivery_search_and_pages(as_superadmin: TestClient, db: Session) -> None:
    campaign = _campaign(db)
    for i, name in enumerate(["Ana López", "Beto Ruiz", "Ana María", "Caro Díaz", "Dani 100%"]):
        _recipient(db, campaign, f"p{i}@ipn.mx", name, "bounced" if i % 2 else "delivered", "bounce")

    assert [r["name"] for r in _rows(as_superadmin, campaign.id, q="ANA")["items"]] == [
        "Ana López",
        "Ana María",
    ]
    assert [r["email"] for r in _rows(as_superadmin, campaign.id, q="p3@IPN")["items"]] == ["p3@ipn.mx"]
    assert [r["name"] for r in _rows(as_superadmin, campaign.id, q="100%")["items"]] == ["Dani 100%"]
    assert _rows(as_superadmin, campaign.id, q="%")["items"] == [
        _rows(as_superadmin, campaign.id, q="Dani")["items"][0]
    ]  # a wildcard is literal
    assert _rows(as_superadmin, campaign.id, q="_")["items"] == []
    assert [r["name"] for r in _rows(as_superadmin, campaign.id, q="ana", status="delivered")["items"]] == [
        "Ana López",
        "Ana María",
    ]
    assert _rows(as_superadmin, campaign.id, q="beto", status="delivered")["items"] == []

    seen: list[str] = []
    cursor = None
    for _ in range(5):
        page = _rows(as_superadmin, campaign.id, limit=2, **({"cursor": cursor} if cursor else {}))
        assert len(page["items"]) <= 2
        seen += [r["email"] for r in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert seen == [f"p{i}@ipn.mx" for i in range(5)]

    url = f"{CAMPAIGNS}/{campaign.id}/recipients"
    assert as_superadmin.get(url, params={"limit": 51}).status_code == 422
    assert as_superadmin.get(url, params={"status": "lost"}).status_code == 422
    assert as_superadmin.get(url, params={"q": "x" * 201}).status_code == 422
    assert as_superadmin.get(url, params={"cursor": "nope"}).status_code == 422


def test_delivery_detail_scope(as_admin_ia: TestClient, db: Session) -> None:
    club = _user(db, "admin.ia@upiixsol.dev").academy_id
    own = _campaign(db, academy_id=club)
    _recipient(db, own, "ana@ipn.mx", "Ana")
    robotica = Academy(slug="robotica", name="Robótica")
    db.add(robotica)
    db.flush()
    other = _campaign(db, academy_id=robotica.id)
    _recipient(db, other, "secreto@ipn.mx", "Secreto")
    board = _campaign(db)  # UpiixSol-wide, no club
    _recipient(db, board, "junta@ipn.mx", "Junta")

    assert [r["email"] for r in _rows(as_admin_ia, own.id)["items"]] == ["ana@ipn.mx"]
    for campaign in (other, board):
        response = as_admin_ia.get(f"{CAMPAIGNS}/{campaign.id}/recipients")
        assert response.status_code == 403
        assert "@ipn.mx" not in response.text
    assert as_admin_ia.get(f"{CAMPAIGNS}/999999/recipients").status_code == 404


def test_purged_campaign_reports_details_purged(as_superadmin: TestClient, db: Session) -> None:
    old = _campaign(db, finished_at=datetime.now(UTC) - timedelta(days=400))
    _recipient(db, old, "ana@ipn.mx", "Ana", "delivered")
    _recipient(db, old, "beto@ipn.mx", "Beto", "bounced", "bounce")
    fresh = _campaign(db, finished_at=datetime.now(UTC) - timedelta(days=3))
    _recipient(db, fresh, "caro@ipn.mx", "Caro", "delivered")
    assert mail_retention.purge(db).campaigns == 1

    detail = as_superadmin.get(f"{CAMPAIGNS}/{old.id}").json()
    assert detail["details_purged"] is True
    assert detail["counts_by_status"] == {"bounced": 1, "delivered": 1}
    assert _rows(as_superadmin, old.id) == {"items": [], "next_cursor": None}

    assert as_superadmin.get(f"{CAMPAIGNS}/{fresh.id}").json()["details_purged"] is False
    never_sent = _campaign(db)
    assert as_superadmin.get(f"{CAMPAIGNS}/{never_sent.id}").json()["details_purged"] is False


def test_campaign_detail_includes_content_for_reuse(as_superadmin: TestClient, db: Session) -> None:
    blocks = [
        {"kind": "heading", "text": "Taller de LLMs"},
        {"kind": "paragraph", "text": "Nos vemos el jueves."},
        {"kind": "divider"},
    ]
    rich = _campaign(db, body="Taller de LLMs\n\nNos vemos el jueves.", content=blocks, preheader="El jueves")
    _recipient(db, rich, "ana@ipn.mx", "Ana")
    detail = as_superadmin.get(f"{CAMPAIGNS}/{rich.id}").json()
    assert detail["content"] == {"preheader": "El jueves", "blocks": blocks}
    assert "ana@ipn.mx" not in str(detail["content"])  # never its recipients
    Blocks.model_validate(detail["content"]["blocks"])

    legacy = _campaign(db, body="Hola a todos\n\n  \n\nSegundo párrafo\ncon otra línea\r\n\r\nFin")
    content = as_superadmin.get(f"{CAMPAIGNS}/{legacy.id}").json()["content"]
    assert content == {
        "preheader": None,
        "blocks": [
            {"kind": "paragraph", "text": "Hola a todos"},
            {"kind": "paragraph", "text": "Segundo párrafo\ncon otra línea"},
            {"kind": "paragraph", "text": "Fin"},
        ],
    }
    Blocks.model_validate(content["blocks"])

    listed = as_superadmin.get(CAMPAIGNS).json()["items"]
    assert all("content" not in item for item in listed)  # the history list stays light


def test_member_and_anon_get_403_and_401_on_delivery(
    as_member: TestClient, client: TestClient, db: Session
) -> None:
    campaign = _campaign(db)
    _recipient(db, campaign, "ana@ipn.mx", "Ana")
    url = f"{CAMPAIGNS}/{campaign.id}/recipients"
    assert as_member.get(url).status_code == 403
    assert client.get(url).status_code == 401


def test_delivery_status_filter_matches_the_recipient_statuses() -> None:
    from typing import get_args

    from app.models.mail import RECIPIENT_STATUSES

    assert get_args(mail_delivery.DeliveryStatus) == RECIPIENT_STATUSES
