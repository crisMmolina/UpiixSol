"""Mail templates API (UPS-101, spec 005 §Templates): built-ins + UpiixSol + own club, scope from the DB."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import MailTemplate, Role
from app.services.mail_templates_builtin import BUILTIN_TEMPLATES
from app.tests.conftest import _client_as, make_academy, make_user

TEMPLATES = "/api/mail/templates"
BLOCKS = [{"kind": "heading", "text": "Hola"}, {"kind": "paragraph", "text": "Nos vemos **pronto**"}]
KEYS = {"id", "kind", "scope", "name", "description", "subject", "preheader", "blocks"}


@pytest.fixture
def as_admin_robotica(db: Session, seeded: dict) -> Iterator[TestClient]:
    robotica = make_academy(db, slug="robotica", name="Robótica")
    make_user(db, role=Role.academy_admin, email="admin.robotica@upiixsol.dev", academy_id=robotica.id)
    yield from _client_as(db, "admin.robotica@upiixsol.dev")


def _payload(name: str, **extra: object) -> dict:
    return {"name": name, "subject": "Aviso", "preheader": "Resumen", "blocks": BLOCKS} | extra


def _save(client: TestClient, name: str, **extra: object) -> dict:
    response = client.post(TEMPLATES, json=_payload(name, **extra))
    assert response.status_code == 201, response.text
    return response.json()


def _names(client: TestClient) -> list[str]:
    response = client.get(TEMPLATES)
    assert response.status_code == 200, response.text
    return [template["name"] for template in response.json()]


def test_list_has_builtins_site_and_own_club_templates(
    as_superadmin: TestClient, as_admin_ia: TestClient, as_admin_robotica: TestClient
) -> None:
    _save(as_superadmin, "Bienvenida UpiixSol")
    _save(as_admin_ia, "Club IA")
    _save(as_admin_robotica, "Club Robótica")
    response = as_admin_ia.get(TEMPLATES)
    assert response.status_code == 200, response.text
    items = response.json()
    builtins = [t.name for t in BUILTIN_TEMPLATES]
    assert [t["name"] for t in items] == [*builtins, "Bienvenida UpiixSol", "Club IA"]
    assert all(set(t) == KEYS for t in items)
    assert [t["kind"] for t in items] == ["builtin"] * len(builtins) + ["saved", "saved"]
    assert items[0]["id"] == BUILTIN_TEMPLATES[0].id and items[0]["blocks"] == BUILTIN_TEMPLATES[0].blocks
    assert [t["scope"] for t in items[-2:]] == ["site", "academy"]
    assert "Club Robótica" not in _names(as_admin_ia)
    assert "Club IA" not in _names(as_admin_robotica)


def test_superadmin_lists_all_templates(
    as_superadmin: TestClient, as_admin_ia: TestClient, as_admin_robotica: TestClient
) -> None:
    _save(as_superadmin, "Bienvenida UpiixSol")
    _save(as_admin_ia, "Club IA")
    _save(as_admin_robotica, "Club Robótica")
    names = _names(as_superadmin)
    assert names[len(BUILTIN_TEMPLATES) :] == ["Bienvenida UpiixSol", "Club IA", "Club Robótica"]


def test_superadmin_saves_site_template(as_superadmin: TestClient, db: Session) -> None:
    saved = _save(as_superadmin, "Boletín", description="Cada mes")
    assert saved["kind"] == "saved" and saved["scope"] == "site" and saved["description"] == "Cada mes"
    assert saved["blocks"] == [
        {"kind": "heading", "text": "Hola"},
        {"kind": "paragraph", "text": "Nos vemos **pronto**"},
    ]
    row = db.get(MailTemplate, saved["id"])
    assert row is not None and row.scope == "site" and row.academy_id is None and row.created_by is not None


def test_academy_admin_saves_own_club_template_scope_from_db(
    as_admin_ia: TestClient, as_admin_robotica: TestClient, db: Session, seeded: dict
) -> None:
    # Neither the scope nor the club can come from the body.
    assert as_admin_ia.post(TEMPLATES, json=_payload("A", academy_id=999)).status_code == 422
    assert as_admin_ia.post(TEMPLATES, json=_payload("A", scope="site")).status_code == 422
    saved = _save(as_admin_ia, "Club IA")
    assert saved["scope"] == "academy"
    row = db.get(MailTemplate, saved["id"])
    assert row is not None and row.scope == "academy" and row.academy_id == seeded["academy_id"]


def test_academy_admin_cannot_edit_site_or_other_club_template(
    as_superadmin: TestClient, as_admin_ia: TestClient, as_admin_robotica: TestClient
) -> None:
    site = _save(as_superadmin, "UpiixSol")
    other = _save(as_admin_robotica, "Robótica")
    own = _save(as_admin_ia, "Propia")
    for template in (site, other):
        url = f"{TEMPLATES}/{template['id']}"
        assert as_admin_ia.patch(url, json={"name": "Mía"}).status_code == 403
        assert as_admin_ia.delete(url).status_code == 403
    renamed = as_admin_ia.patch(f"{TEMPLATES}/{own['id']}", json={"name": "Renombrada", "description": "D"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Renombrada" and renamed.json()["description"] == "D"
    assert as_admin_ia.patch(f"{TEMPLATES}/{own['id']}", json={"subject": "X"}).status_code == 422
    assert as_admin_ia.delete(f"{TEMPLATES}/{own['id']}").status_code == 204
    assert as_admin_ia.delete(f"{TEMPLATES}/{own['id']}").status_code == 404
    # A superadmin manages every template.
    assert as_superadmin.patch(f"{TEMPLATES}/{other['id']}", json={"name": "Por la mesa"}).status_code == 200
    assert as_superadmin.delete(f"{TEMPLATES}/{other['id']}").status_code == 204
    assert _names(as_admin_robotica)[len(BUILTIN_TEMPLATES) :] == ["UpiixSol"]


def test_builtins_are_read_only(as_superadmin: TestClient) -> None:
    url = f"{TEMPLATES}/{BUILTIN_TEMPLATES[0].id}"
    patched = as_superadmin.patch(url, json={"name": "Otra"})
    assert patched.status_code == 405, patched.text
    assert patched.json()["error"]["message"] == "Las plantillas incluidas no se pueden cambiar."
    assert as_superadmin.delete(url).status_code == 405
    assert as_superadmin.delete(f"{TEMPLATES}/builtin:no-existe").status_code == 404
    assert as_superadmin.delete(f"{TEMPLATES}/abc").status_code == 404
    assert as_superadmin.delete(f"{TEMPLATES}/99999").status_code == 404


def test_template_blocks_validated_like_campaigns(as_admin_ia: TestClient) -> None:
    bad = [
        [],
        [{"kind": "button", "label": "Ver", "url": "javascript:alert(1)"}],
        [{"kind": "paragraph", "text": "Hola"}] * 31,
        [{"kind": "event", "placeholder": True}, {"kind": "event", "placeholder": True}],
        [{"kind": "script", "text": "x"}],
    ]
    for blocks in bad:
        response = as_admin_ia.post(TEMPLATES, json=_payload("Mala", blocks=blocks))
        assert response.status_code == 422, blocks
    assert as_admin_ia.post(TEMPLATES, json=_payload("Asunto", subject="A\nBcc: x@y.mx")).status_code == 422
    assert as_admin_ia.post(TEMPLATES, json=_payload("x" * 61)).status_code == 422
    assert as_admin_ia.post(TEMPLATES, json=_payload("Larga", description="d" * 141)).status_code == 422
    # A template may keep the event slot: the sender completes it before sending.
    saved = _save(as_admin_ia, "Evento", blocks=[{"kind": "event", "placeholder": True}])
    assert saved["blocks"][0]["placeholder"] is True


def test_saved_template_has_no_audience_or_reply_to(as_admin_ia: TestClient, db: Session) -> None:
    for extra in (
        {"audience": {"kind": "all"}},
        {"reply_to": "club@ipn.mx"},
        {"sender_academy_id": 1},
    ):
        assert as_admin_ia.post(TEMPLATES, json=_payload("Con extra", **extra)).status_code == 422, extra
    saved = _save(as_admin_ia, "Limpia")
    assert set(saved) == KEYS
    columns = set(MailTemplate.__table__.columns.keys())
    assert not columns & {"audience", "audience_kind", "audience_params", "reply_to", "sender_academy_id"}


def test_duplicate_name_in_scope_is_409(
    as_superadmin: TestClient, as_admin_ia: TestClient, as_admin_robotica: TestClient
) -> None:
    first = _save(as_admin_ia, "Aviso")
    duplicate = as_admin_ia.post(TEMPLATES, json=_payload("aviso"))
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"]["message"] == "Ya existe una plantilla con ese nombre."
    _save(as_admin_robotica, "Aviso")  # another club
    _save(as_superadmin, "Aviso")  # UpiixSol
    second = _save(as_admin_ia, "Otro")
    assert as_admin_ia.patch(f"{TEMPLATES}/{second['id']}", json={"name": "AVISO"}).status_code == 409
    # Renaming a template to itself (another case) is not a duplicate.
    assert as_admin_ia.patch(f"{TEMPLATES}/{first['id']}", json={"name": "AVISO"}).status_code == 200


def test_member_and_anon_get_403_and_401(as_member: TestClient, as_superadmin: TestClient) -> None:
    saved = _save(as_superadmin, "UpiixSol")
    url = f"{TEMPLATES}/{saved['id']}"
    anon = TestClient(app)
    for client, code in ((as_member, 403), (anon, 401)):
        assert client.get(TEMPLATES).status_code == code
        assert client.post(TEMPLATES, json=_payload("X")).status_code == code
        assert client.patch(url, json={"name": "Y"}).status_code == code
        assert client.delete(url).status_code == code
