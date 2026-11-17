"""Nicknames are unique (ignoring case) and "admin" / "upiixia" are reserved (UPS-070)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User

REGISTER = {
    "full_name": "Ana López Pérez",
    "boleta": "2026123456",
    "email": "ana.lopez@alumno.ipn.mx",
    "password": "segura-123",
    "accept_privacy": True,
}
RESERVED_VARIANTS = ["admin", "Admin", "UPIIXIA", "a.d.m.i.n", "Ádmin", "upiix-ia"]


def _register(client: TestClient, n: int, **extra: object):
    body = {**REGISTER, "boleta": f"20261234{n:02d}", "email": f"ana{n}@alumno.ipn.mx", **extra}
    return client.post("/api/auth/register", json=body)


def test_register_rejects_a_taken_nickname_case_insensitive(client: TestClient, seeded: dict) -> None:
    taken = _register(client, 1, nickname="ALUMNO.demo")
    assert taken.status_code == 409 and taken.json()["error"]["code"] == "nickname_taken"
    assert _register(client, 2, nickname="alumna.nueva").status_code == 201
    again = _register(client, 3, nickname="Alumna.Nueva")
    assert again.status_code == 409 and again.json()["error"]["code"] == "nickname_taken"


def test_register_default_nickname_is_numbered_when_taken(client: TestClient, seeded: dict) -> None:
    first = _register(client, 1)
    second = _register(client, 2, full_name="Ana Ruiz Gómez")
    third = _register(client, 3, full_name="ANA Díaz Soto")
    assert [r.json()["user"]["nickname"] for r in (first, second, third)] == ["ana", "ana2", "ana3"]


@pytest.mark.parametrize("name", RESERVED_VARIANTS)
def test_reserved_nicknames_are_refused_everywhere(
    name: str, client: TestClient, as_superadmin: TestClient, as_member: TestClient, db: Session
) -> None:
    def refused(response) -> bool:
        return response.status_code == 422 and response.json()["error"]["code"] == "nickname_reserved"

    assert refused(_register(client, 1, nickname=name))
    created = as_superadmin.post(
        "/api/admin/users",
        json={
            "role": "member",
            "email": "nuevo@ipn.mx",
            "full_name": "Nuevo Usuario",
            "password": "temporal-123",
            "nickname": name,
        },
    )
    assert refused(created)
    member = db.query(User).filter_by(email="alumno.demo@upiixsol.dev").one()
    assert refused(as_superadmin.patch(f"/api/admin/users/{member.id}", json={"nickname": name}))
    assert refused(as_member.patch("/api/account/profile", json={"nickname": name}))
    assert db.get(User, member.id).nickname == "alumno.demo"


def test_automatic_nicknames_skip_reserved_names(
    client: TestClient, as_superadmin: TestClient, seeded: dict
) -> None:
    registered = _register(client, 1, full_name="Admin Pérez Ruiz")
    assert registered.status_code == 201 and registered.json()["user"]["nickname"] == "admin2"
    created = as_superadmin.post(
        "/api/admin/users",
        json={
            "role": "member",
            "email": "up@ipn.mx",
            "full_name": "Upiixia Nueva",
            "password": "temporal-123",
        },
    )
    assert created.status_code == 201 and created.json()["nickname"] == "upiixia2"


def test_profile_update_rejects_taken_and_reserved_nickname(
    as_member: TestClient, as_superadmin: TestClient, db: Session
) -> None:
    taken = as_member.patch("/api/account/profile", json={"nickname": "Admin.IA"})
    assert taken.status_code == 409 and taken.json()["error"]["code"] == "nickname_taken"
    assert as_member.patch("/api/account/profile", json={"nickname": "ADMIN"}).status_code == 422
    # Your own nickname, even in another case, is not a conflict.
    own = as_member.patch("/api/account/profile", json={"nickname": "ALUMNO.demo"})
    assert own.status_code == 200 and own.json()["nickname"] == "ALUMNO.demo"
    member = db.query(User).filter_by(email="alumno.demo@upiixsol.dev").one()
    clash = as_superadmin.patch(f"/api/admin/users/{member.id}", json={"nickname": "SuperAdmin1"})
    assert clash.status_code == 409 and clash.json()["error"]["code"] == "nickname_taken"


def test_migration_renames_existing_duplicate_and_reserved_nicknames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alembic import command
    from alembic.config import Config

    from app.config import get_settings

    url = f"sqlite:///{tmp_path / 'nicknames.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    insert = (
        "INSERT INTO users (id, role, email, password_hash, full_name, nickname,"
        " must_change_password, is_active)"
        " VALUES (:id, 'member', :email, 'x', 'Persona Prueba', :nick, 0, 1)"
    )
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "0007")
        nicknames = ["Ana", "ana", "ANA", "admin", "Admin", "ana2", "Upiixia", "luis"]
        with engine.begin() as conn:
            for i, nickname in enumerate(nicknames, start=1):
                conn.execute(text(insert), {"id": i, "email": f"u{i}@ipn.mx", "nick": nickname})
        command.upgrade(config, "head")
        with engine.connect() as conn:
            rows = dict(conn.execute(text("SELECT id, nickname FROM users")).all())
        assert rows[1] == "Ana" and rows[6] == "ana2" and rows[8] == "luis"  # the first of each keeps it
        lowered = [name.lower() for name in rows.values()]
        assert len(set(lowered)) == len(lowered)
        assert not {"admin", "upiixia"} & set(lowered)
        assert rows[2].startswith("ana") and rows[4].startswith("admin") and rows[7].startswith("Upiixia")
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(insert), {"id": 99, "email": "dup@ipn.mx", "nick": "LUIS"})
        command.downgrade(config, "base")
    finally:
        engine.dispose()
        get_settings.cache_clear()
