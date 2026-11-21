"""Mail audience (UPS-074, spec 003 §Audiences and permissions): preview count, recipient search, status.

Seeded accounts are `@upiixsol.dev`, the default `MAIL_BLOCKED_DOMAINS`, so they never count; the
people each test counts are created here with `@ipn.mx` addresses. Everything goes through HTTP.
"""

import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Academy, Enrollment, Role, User
from app.models.common import utcnow
from app.models.mail import MailCampaign, MailRecipient, MailSuppression
from app.services.mail_audience import billing_period
from app.services.mailer import new_unsubscribe_token
from app.tests.conftest import make_user

PREVIEW = "/api/mail/audience/preview"
RECIPIENTS = "/api/mail/recipients"
STATUS = "/api/mail/status"


def _person(
    db: Session,
    email: str,
    *,
    role: Role = Role.member,
    academy_id: int | None = None,
    enrolled: tuple[int, ...] = (),
    active: bool = True,
    full_name: str | None = None,
) -> User:
    user = make_user(db, role=role, email=email, academy_id=academy_id, is_active=active)
    if full_name:  # the default nickname is the address's local part; a named person gets their own
        user.full_name = full_name
        user.nickname = full_name.split()[0].lower()
    db.add_all([Enrollment(user_id=user.id, academy_id=academy) for academy in enrolled])
    db.flush()
    return user


def _robotica(db: Session) -> int:
    academy = Academy(slug="robotica", name="Robótica")
    db.add(academy)
    db.flush()
    return academy.id


def _preview(client: TestClient, audience: dict) -> dict:
    response = client.post(PREVIEW, json=audience)
    assert response.status_code == 200, response.text
    return response.json()


def test_all_counts_active_users_once(as_superadmin: TestClient, db: Session, seeded: dict) -> None:
    _person(db, "ana@ipn.mx", enrolled=(seeded["academy_id"],))
    _person(db, "beto@ipn.mx")
    _person(db, "ceci@ipn.mx", active=False)
    body = _preview(as_superadmin, {"kind": "all"})
    assert body["count"] == 2
    assert body["excluded"]["inactive"] == 1


def test_academy_counts_enrollees_and_its_admins(
    as_superadmin: TestClient, db: Session, seeded: dict
) -> None:
    ia = seeded["academy_id"]
    robotica = _robotica(db)
    _person(db, "uno@ipn.mx", enrolled=(ia, robotica))  # in two clubs: still one address
    _person(db, "dos@ipn.mx", enrolled=(ia,))
    _person(db, "jefa@ipn.mx", role=Role.academy_admin, academy_id=ia)
    _person(db, "otro@ipn.mx", enrolled=(robotica,))
    _person(db, "jefe.robotica@ipn.mx", role=Role.academy_admin, academy_id=robotica)
    assert _preview(as_superadmin, {"kind": "academy", "academy_id": ia})["count"] == 3
    assert _preview(as_superadmin, {"kind": "academy", "academy_id": robotica})["count"] == 3


def test_role_counts_that_role_only(as_superadmin: TestClient, db: Session, seeded: dict) -> None:
    _person(db, "super@ipn.mx", role=Role.superadmin)
    _person(db, "jefa@ipn.mx", role=Role.academy_admin, academy_id=seeded["academy_id"])
    _person(db, "m1@ipn.mx")
    _person(db, "m2@ipn.mx")
    counts = {
        role: _preview(as_superadmin, {"kind": "role", "role": role})["count"]
        for role in ("superadmin", "academy_admin", "member")
    }
    assert counts == {"superadmin": 1, "academy_admin": 1, "member": 2}


def test_individual_mixes_users_and_outside_addresses(as_superadmin: TestClient, db: Session) -> None:
    ana = _person(db, "ana@ipn.mx")
    beto = _person(db, "beto@ipn.mx")
    audience = {
        "kind": "individual",
        "user_ids": [ana.id, beto.id],
        "emails": ["Fuera@Gmail.com", "otra@gmail.com", "ANA@ipn.mx", "fuera@gmail.com"],
    }
    assert _preview(as_superadmin, audience)["count"] == 4


def test_individual_accepts_hundreds_of_outside_addresses(as_superadmin: TestClient, db: Session) -> None:
    emails = [f"fuera{i}@gmail.com" for i in range(300)]
    ids = [_person(db, f"p{i}@ipn.mx").id for i in range(50)]
    assert _preview(as_superadmin, {"kind": "individual", "emails": emails})["count"] == 300
    mixed = _preview(as_superadmin, {"kind": "individual", "user_ids": ids, "emails": emails})
    assert mixed["count"] == 350


def test_outside_addresses_over_the_monthly_remaining_is_422(
    as_superadmin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "mail_monthly_limit", 30)
    emails = [f"fuera{i}@gmail.com" for i in range(31)]
    over = as_superadmin.post(PREVIEW, json={"kind": "individual", "emails": emails})
    assert over.status_code == 422
    assert "30" in over.json()["error"]["message"]
    repeated = emails[:30] + [e.upper() for e in emails[:30]]
    assert _preview(as_superadmin, {"kind": "individual", "emails": repeated})["count"] == 30


def test_outside_addresses_are_normalized_and_deduplicated(as_superadmin: TestClient) -> None:
    emails = ["  Fuera@Gmail.com ", "fuera@gmail.com", "FUERA@GMAIL.COM", "otra@gmail.com"]
    assert _preview(as_superadmin, {"kind": "individual", "emails": emails})["count"] == 2


def test_campus_users_still_at_most_50(as_superadmin: TestClient, db: Session) -> None:
    ids = [_person(db, f"p{i}@ipn.mx").id for i in range(51)]
    too_many = as_superadmin.post(PREVIEW, json={"kind": "individual", "user_ids": ids})
    assert too_many.status_code == 422
    with_outside = {"kind": "individual", "user_ids": ids[:50], "emails": ["a@gmail.com", "b@gmail.com"]}
    assert _preview(as_superadmin, with_outside)["count"] == 52


def test_invalid_outside_address_is_422(as_superadmin: TestClient) -> None:
    for bad in ("no-es-correo", "a@b@c.mx", "x@gmail.com\nBcc: y@gmail.com"):
        response = as_superadmin.post(PREVIEW, json={"kind": "individual", "emails": [bad]})
        assert response.status_code == 422, bad
        assert response.json()["error"]["code"] == "validation_error"


def test_excludes_inactive_suppressed_and_blocked_domains(
    as_superadmin: TestClient, db: Session, seeded: dict
) -> None:
    _person(db, "ok@ipn.mx")
    _person(db, "baja.inactiva@ipn.mx", active=False)
    _person(db, "suprimida@ipn.mx")
    db.add_all(
        [
            MailSuppression(email="suprimida@ipn.mx", reason="unsubscribed"),
            MailSuppression(email="rebote@gmail.com", reason="bounced"),
        ]
    )
    db.flush()
    seeded_active = db.scalar(
        select(func.count()).where(User.email.like("%@upiixsol.dev"), User.is_active.is_(True))
    )
    assert seeded_active > 0
    body = _preview(as_superadmin, {"kind": "all"})
    assert body == {
        "count": 1,
        "excluded": {"inactive": 1, "suppressed": 1, "blocked_domain": seeded_active},
    }
    outside = {"kind": "individual", "emails": ["REBOTE@gmail.com", "x@upiixsol.dev", "nuevo@gmail.com"]}
    assert _preview(as_superadmin, outside) == {
        "count": 1,
        "excluded": {"inactive": 0, "suppressed": 1, "blocked_domain": 1},
    }


def test_academy_admin_cannot_mail_all(as_admin_ia: TestClient) -> None:
    assert as_admin_ia.post(PREVIEW, json={"kind": "all"}).status_code == 403


def test_academy_admin_cannot_mail_a_role(as_admin_ia: TestClient) -> None:
    for role in ("member", "academy_admin", "superadmin"):
        assert as_admin_ia.post(PREVIEW, json={"kind": "role", "role": role}).status_code == 403


def test_academy_admin_cannot_mail_another_club(as_admin_ia: TestClient, db: Session, seeded: dict) -> None:
    robotica = _robotica(db)
    _person(db, "robot@ipn.mx", enrolled=(robotica,))
    for academy_id in (robotica, 99999):
        response = as_admin_ia.post(PREVIEW, json={"kind": "academy", "academy_id": academy_id})
        assert response.status_code == 403
    _person(db, "propio@ipn.mx", enrolled=(seeded["academy_id"],))
    own = _preview(as_admin_ia, {"kind": "academy", "academy_id": seeded["academy_id"]})
    assert own["count"] == 1


def test_academy_admin_cannot_pick_a_non_enrolled_user(
    as_admin_ia: TestClient, db: Session, seeded: dict
) -> None:
    robotica = _robotica(db)
    outsider = _person(db, "ajeno@ipn.mx", enrolled=(robotica,))
    loner = _person(db, "solo@ipn.mx")
    mine = _person(db, "mio@ipn.mx", enrolled=(seeded["academy_id"],))
    for ids in ([outsider.id], [loner.id], [mine.id, outsider.id], [seeded["superadmin_id"]], [99999]):
        response = as_admin_ia.post(PREVIEW, json={"kind": "individual", "user_ids": ids})
        assert response.status_code == 403, ids
    assert _preview(as_admin_ia, {"kind": "individual", "user_ids": [mine.id]})["count"] == 1


def test_academy_admin_can_add_outside_addresses(as_admin_ia: TestClient, db: Session, seeded: dict) -> None:
    mine = _person(db, "mio@ipn.mx", enrolled=(seeded["academy_id"],))
    audience = {"kind": "individual", "user_ids": [mine.id], "emails": ["fuera@gmail.com", "otra@unam.mx"]}
    assert _preview(as_admin_ia, audience)["count"] == 3


def test_recipient_search_hides_email_from_academy_admin(
    as_admin_ia: TestClient, as_superadmin: TestClient, db: Session, seeded: dict
) -> None:
    robotica = _robotica(db)
    lucia = _person(db, "lucia.secreta@ipn.mx", enrolled=(seeded["academy_id"],), full_name="Lucía Pérez")
    _person(db, "luciano@ipn.mx", enrolled=(robotica,), full_name="Luciano Ajeno")
    _person(db, "lucio.baja@ipn.mx", enrolled=(seeded["academy_id"],), full_name="Lucio Baja", active=False)
    page = as_admin_ia.get(RECIPIENTS, params={"q": "luc"})
    assert page.status_code == 200, page.text
    items = page.json()["items"]
    assert [item["id"] for item in items] == [lucia.id]
    # Spec 006 (victor 2026-11-20): club admins see the addresses of the people they may pick.
    assert set(items[0]) == {"id", "full_name", "nickname", "avatar_url", "email"}
    assert items[0]["email"] == "lucia.secreta@ipn.mx"
    # Searching by address matches only people in their scope (not Luciano's club, not the inactive Lucio).
    by_address = as_admin_ia.get(RECIPIENTS, params={"q": "ipn.mx"}).json()["items"]
    assert [item["id"] for item in by_address] == [lucia.id]
    found = as_superadmin.get(RECIPIENTS, params={"q": "secreta"}).json()["items"]
    assert [(item["id"], item["email"]) for item in found] == [(lucia.id, "lucia.secreta@ipn.mx")]
    assert len(as_superadmin.get(RECIPIENTS, params={"q": "luc"}).json()["items"]) == 2
    assert as_superadmin.get(RECIPIENTS, params={"limit": 51}).status_code == 422


def test_member_and_anon_get_403_and_401(as_member: TestClient, db: Session) -> None:
    from app.main import app

    anon = TestClient(app)
    calls = [("GET", STATUS, {}), ("GET", RECIPIENTS, {}), ("POST", PREVIEW, {"json": {"kind": "all"}})]
    for method, path, kwargs in calls:
        assert as_member.request(method, path, **kwargs).status_code == 403, path
        assert anon.request(method, path, **kwargs).status_code == 401, path


def test_status_reports_monthly_limit_used_remaining_and_renewal_date(
    as_superadmin: TestClient, as_admin_ia: TestClient, db: Session, seeded: dict
) -> None:
    campaign = MailCampaign(
        sender_id=seeded["superadmin_id"], audience_kind="all", subject="Aviso", body="Hola", status="sending"
    )
    db.add(campaign)
    db.flush()
    now = utcnow()
    statuses = [
        ("accepted", now),
        ("delivered", now),
        ("failed", now),
        ("pending", now),
        ("delivered", now - timedelta(days=40)),  # an earlier billing period
    ]
    for i, (status, updated_at) in enumerate(statuses):
        db.add(
            MailRecipient(
                campaign_id=campaign.id,
                email=f"r{i}@ipn.mx",
                name="R",
                status=status,
                unsubscribe_token_hash=new_unsubscribe_token()[1],
                updated_at=updated_at,
            )
        )
    db.flush()
    body = as_superadmin.get(STATUS).json()
    start, end = billing_period(now, 1)
    assert body == {
        "enabled": False,
        "monthly_limit": 3000,
        "sent_this_period": 3,
        "remaining": 2997,
        "period_start": start.isoformat().replace("+00:00", "Z"),
        "period_end": end.isoformat().replace("+00:00", "Z"),
    }
    assert as_admin_ia.get(STATUS).json() == body


def test_preview_p95_under_300_ms_on_seeded_data(
    as_superadmin: TestClient, db: Session, seeded: dict
) -> None:
    ia = seeded["academy_id"]
    for i in range(300):
        _person(db, f"carga{i}@ipn.mx", enrolled=(ia,) if i % 2 else ())
    db.add_all([MailSuppression(email=f"carga{i}@ipn.mx", reason="unsubscribed") for i in range(0, 300, 7)])
    db.flush()
    audiences = [{"kind": "all"}, {"kind": "academy", "academy_id": ia}, {"kind": "role", "role": "member"}]
    timings = []
    for i in range(21):
        start = time.perf_counter()
        _preview(as_superadmin, audiences[i % 3])
        timings.append(time.perf_counter() - start)
    timings.sort()
    assert timings[int(len(timings) * 0.95) - 1] < 0.3


def test_empty_individual_is_422(as_superadmin: TestClient) -> None:
    response = as_superadmin.post(PREVIEW, json={"kind": "individual", "user_ids": [], "emails": []})
    assert response.status_code == 422


def test_academy_admin_without_a_club_gets_403(client: TestClient, db: Session, seeded: dict) -> None:
    from app.tests.conftest import auth_headers

    orphan = _person(db, "sin.club@ipn.mx", role=Role.academy_admin)
    headers = auth_headers(orphan)
    _person(db, "alguien@ipn.mx", enrolled=(seeded["academy_id"],))
    for audience in ({"kind": "academy", "academy_id": seeded["academy_id"]}, {"kind": "all"}):
        assert client.post(PREVIEW, json=audience, headers=headers).status_code == 403
    assert client.get(RECIPIENTS, headers=headers).json()["items"] == []


def test_resolve_audience_returns_one_deliverable_recipient_per_address(db: Session, seeded: dict) -> None:
    from app.services.mail_audience import IndividualAudience, ResolvedRecipient, resolve_audience

    sender = db.get(User, seeded["admin_ia_id"])
    mine = _person(db, "mio@ipn.mx", enrolled=(seeded["academy_id"],), full_name="Mía Ruiz")
    audience = IndividualAudience(
        kind="individual", user_ids=[mine.id], emails=["MIO@ipn.mx", "Fuera@Gmail.com", "x@upiixsol.dev"]
    )
    recipients = resolve_audience(db, sender, audience)
    assert recipients == [
        ResolvedRecipient(user_id=mine.id, email="mio@ipn.mx", name="Mía Ruiz"),
        ResolvedRecipient(user_id=None, email="fuera@gmail.com", name="fuera"),
    ]
    assert "ipn.mx" not in repr(recipients) and "gmail" not in repr(recipients)


def test_recipient_search_without_query_pages_the_club(
    as_admin_ia: TestClient, db: Session, seeded: dict
) -> None:
    for i in range(3):
        _person(db, f"socio{i}@ipn.mx", enrolled=(seeded["academy_id"],), full_name=f"Socio {i}")
    first = as_admin_ia.get(RECIPIENTS, params={"limit": 2}).json()
    second = as_admin_ia.get(RECIPIENTS, params={"limit": 2, "cursor": first["next_cursor"]}).json()
    names = [item["full_name"] for item in first["items"] + second["items"]]
    assert names == sorted(names) and len(set(names)) == len(names)
    assert {"Socio 0", "Socio 1", "Socio 2"} <= set(names)


def test_academy_admin_preview_does_not_confirm_typed_addresses(
    as_admin_ia: TestClient, as_superadmin: TestClient, db: Session, seeded: dict
) -> None:
    mine = _person(db, "mio@ipn.mx", enrolled=(seeded["academy_id"],))
    db.add(MailSuppression(email="rebote@gmail.com", reason="bounced"))
    db.flush()
    audience = {"kind": "individual", "user_ids": [mine.id], "emails": ["MIO@ipn.mx", "rebote@gmail.com"]}
    # A guess that is the member's address, or a suppressed one, changes nothing an admin can see.
    assert _preview(as_admin_ia, audience) == {
        "count": 3,
        "excluded": {"inactive": 0, "suppressed": 0, "blocked_domain": 0},
    }
    assert _preview(as_superadmin, audience) == {
        "count": 1,
        "excluded": {"inactive": 0, "suppressed": 1, "blocked_domain": 0},
    }


def test_academy_admin_can_pick_a_co_admin_of_their_club(
    as_admin_ia: TestClient, db: Session, seeded: dict
) -> None:
    """Human decision (victor 2026-11-17, plan PR #128): own co-admins are pickable, other clubs' are not."""
    robotica = _robotica(db)
    co_admin = _person(
        db, "jefa@ipn.mx", role=Role.academy_admin, academy_id=seeded["academy_id"], full_name="Jefa Club"
    )
    other = _person(
        db, "jefe.robot@ipn.mx", role=Role.academy_admin, academy_id=robotica, full_name="Jefe Robot"
    )
    assert _preview(as_admin_ia, {"kind": "individual", "user_ids": [co_admin.id]})["count"] == 1
    response = as_admin_ia.post(PREVIEW, json={"kind": "individual", "user_ids": [co_admin.id, other.id]})
    assert response.status_code == 403
    found = as_admin_ia.get(RECIPIENTS, params={"q": "jef"}).json()["items"]
    assert [item["id"] for item in found] == [co_admin.id]
    assert found[0]["email"] == "jefa@ipn.mx"  # spec 006 (victor 2026-11-20): addresses visible in scope
