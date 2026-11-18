"""UPS-093 · the superadmin turns members into club admins and back (spec 005, ROL-07)."""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Enrollment, Role, User
from app.tests.conftest import auth_headers, make_academy, make_user


def _put(client: TestClient, user_id: int, body: dict) -> object:
    return client.put(f"/api/admin/users/{user_id}/role", json=body)


def test_superadmin_makes_a_member_a_club_admin_of_an_active_club(
    as_superadmin: TestClient, seeded: dict, db: Session
) -> None:
    response = _put(
        as_superadmin, seeded["member_id"], {"role": "academy_admin", "academy_id": seeded["academy_id"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "academy_admin" and body["academy_id"] == seeded["academy_id"]
    assert body["id"] == seeded["member_id"]
    user = db.get(User, seeded["member_id"])
    assert user.role == Role.academy_admin and user.academy_id == seeded["academy_id"]


def test_superadmin_makes_a_club_admin_a_member_and_clears_the_club(
    as_superadmin: TestClient, seeded: dict, db: Session
) -> None:
    other = make_academy(db, slug="robotica", name="UpiixRobótica")
    admin = make_user(db, role=Role.academy_admin, email="otro.admin@upiixsol.dev", academy_id=other.id)
    db.add(Enrollment(user_id=admin.id, academy_id=other.id))
    db.flush()
    response = _put(as_superadmin, admin.id, {"role": "member"})
    assert response.status_code == 200
    assert response.json()["role"] == "member" and response.json()["academy_id"] is None
    db.refresh(admin)
    assert admin.role == Role.member and admin.academy_id is None
    # Enrollments are kept: demoting does not remove the person from the club.
    assert db.get(Enrollment, (admin.id, other.id)) is not None
    # A member body that still carries a club does not keep it either.
    again = _put(as_superadmin, seeded["admin_ia_id"], {"role": "member", "academy_id": seeded["academy_id"]})
    assert again.status_code == 200 and again.json()["academy_id"] is None


def test_rejects_superadmin_role_and_missing_or_inactive_club_with_422(
    as_superadmin: TestClient, seeded: dict, db: Session
) -> None:
    member_id = seeded["member_id"]
    assert _put(as_superadmin, member_id, {"role": "superadmin"}).status_code == 422
    assert _put(as_superadmin, member_id, {"role": "superadmin", "academy_id": 1}).status_code == 422
    assert _put(as_superadmin, member_id, {"role": "dios"}).status_code == 422
    assert _put(as_superadmin, member_id, {"academy_id": 1}).status_code == 422
    assert _put(as_superadmin, member_id, {"role": "academy_admin"}).status_code == 422
    assert _put(as_superadmin, member_id, {"role": "academy_admin", "academy_id": None}).status_code == 422
    assert _put(as_superadmin, member_id, {"role": "academy_admin", "academy_id": 99999}).status_code == 422
    closed = make_academy(db, slug="cerrado", name="Cerrado")
    closed.is_active = False
    db.flush()
    shut = _put(as_superadmin, member_id, {"role": "academy_admin", "academy_id": closed.id})
    assert shut.status_code == 422
    # Nothing changed after the refused calls.
    user = db.get(User, member_id)
    assert user.role == Role.member and user.academy_id is None
    # Unknown user is a 404, an inactive one a 409.
    assert _put(as_superadmin, 99999, {"role": "member"}).status_code == 404
    sleeper = make_user(db, email="inactivo@upiixsol.dev", is_active=False)
    inactive = _put(as_superadmin, sleeper.id, {"role": "academy_admin", "academy_id": seeded["academy_id"]})
    assert inactive.status_code == 409


def test_refuses_own_role_and_superadmin_targets_with_409(
    as_superadmin: TestClient, seeded: dict, db: Session
) -> None:
    own = _put(as_superadmin, seeded["superadmin_id"], {"role": "member"})
    assert own.status_code == 409 and own.json()["error"]["message"] == "No puedes cambiar tu propio rol."
    other_super = make_user(db, role=Role.superadmin, email="super2@upiixsol.dev")
    refused = _put(as_superadmin, other_super.id, {"role": "member"})
    assert refused.status_code == 409
    assert db.get(User, other_super.id).role == Role.superadmin
    assert db.get(User, seeded["superadmin_id"]).role == Role.superadmin


def test_new_role_applies_on_next_request_and_logs_without_pii(
    as_superadmin: TestClient,
    client: TestClient,
    seeded: dict,
    db: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    member = db.get(User, seeded["member_id"])
    headers = auth_headers(member)  # one token, issued while the person is still a member
    enrollments = f"/api/academies/{seeded['academy_id']}/enrollments"
    assert client.get(enrollments, headers=headers).status_code == 403

    caplog.set_level(logging.INFO)
    promote = _put(as_superadmin, member.id, {"role": "academy_admin", "academy_id": seeded["academy_id"]})
    assert promote.status_code == 200
    assert client.get(enrollments, headers=headers).status_code == 200  # same token, new role

    demote = _put(as_superadmin, member.id, {"role": "member"})
    assert demote.status_code == 200
    assert client.get(enrollments, headers=headers).status_code == 403  # lost at once

    lines = [r.getMessage() for r in caplog.records if "role.changed" in r.getMessage()]
    assert len(lines) == 2
    assert f"actor={seeded['superadmin_id']}" in lines[0] and f"target={member.id}" in lines[0]
    assert "old=member" in lines[0] and "new=academy_admin" in lines[0]
    assert "old=academy_admin" in lines[1] and "new=member" in lines[1]
    for needle in (member.email, member.full_name, member.nickname):
        assert needle not in caplog.text
