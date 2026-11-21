"""Combined audience `mix` (UPS-105, spec 006 §Combined recipients, plan §Design, §STRIDE).

Seeded accounts are on the blocked `upiixsol.dev` domain, so they only ever show up as "cannot"; the
people each test counts are created here with `@ipn.mx` addresses. Everything goes through HTTP except
the migration round-trip.
"""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Academy, Enrollment, Role, User
from app.models.mail import MailSuppression
from app.tests.conftest import make_user

PREVIEW = "/api/mail/audience/preview"
LIST = "/api/mail/audience/list"
INDEX = "ix_mail_recipients_campaign_id_status"


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
    if full_name:
        user.full_name = full_name
        user.nickname = full_name.split()[0].lower()
    db.add_all([Enrollment(user_id=user.id, academy_id=academy) for academy in enrolled])
    db.flush()
    return user


def _club(db: Session, slug: str = "robotica", name: str = "Robótica") -> int:
    academy = Academy(slug=slug, name=name)
    db.add(academy)
    db.flush()
    return academy.id


def _mix(**parts: object) -> dict:
    return {"kind": "mix", **parts}


def _preview(client: TestClient, audience: dict) -> dict:
    response = client.post(PREVIEW, json=audience)
    assert response.status_code == 200, response.text
    return response.json()


def _list_all(client: TestClient, audience: dict, **params: object) -> list[dict]:
    items: list[dict] = []
    cursor = None
    while True:
        body = {"audience": audience, **params, **({"cursor": cursor} if cursor else {})}
        response = client.post(LIST, json=body)
        assert response.status_code == 200, response.text
        page = response.json()
        items += page["items"]
        cursor = page["next_cursor"]
        if not cursor:
            return items


def _insert_campaign(conn, kind: str, status: str = "draft") -> None:
    conn.execute(
        text(
            "INSERT INTO mail_campaigns (audience_kind, audience_params, subject, body, status, "
            "recipient_count) VALUES (:kind, '{}', 's', 'b', :status, 0)"
        ),
        {"kind": kind, "status": status},
    )


def test_mail_audience_mix_migration_round_trips_on_sqlite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alembic import command
    from alembic.config import Config

    from app.config import get_settings

    url = f"sqlite:///{tmp_path / 'mix.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    loggers = [
        logger for logger in logging.root.manager.loggerDict.values() if isinstance(logger, logging.Logger)
    ]
    disabled = {logger: logger.disabled for logger in loggers}
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "head")
        indexes = {ix["name"] for ix in inspect(engine).get_indexes("mail_recipients")}
        assert INDEX in indexes
        with engine.begin() as conn:
            _insert_campaign(conn, "mix")  # widened CHECK
        for kind, status in (("bogus", "draft"), ("mix", "bogus")):  # both CHECKs still bite
            with pytest.raises(IntegrityError), engine.begin() as conn:
                _insert_campaign(conn, kind, status)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM mail_campaigns"))
        command.downgrade(config, "0011")
        assert INDEX not in {ix["name"] for ix in inspect(engine).get_indexes("mail_recipients")}
        with pytest.raises(IntegrityError), engine.begin() as conn:
            _insert_campaign(conn, "mix")  # narrower CHECK restored
        with engine.begin() as conn:
            _insert_campaign(conn, "individual")
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        get_settings.cache_clear()
        for logger, was_disabled in disabled.items():
            logger.disabled = was_disabled


def test_mix_unions_sources_people_and_outside_addresses_once(as_superadmin: TestClient, db: Session) -> None:
    robotica = _club(db)
    uno = _person(db, "uno@ipn.mx", enrolled=(robotica,))
    jefa = _person(db, "jefa@ipn.mx", role=Role.academy_admin, academy_id=robotica)
    picked = _person(db, "picked@ipn.mx")  # only through user_ids
    also = _person(db, "also@ipn.mx", role=Role.academy_admin, academy_id=None)
    audience = _mix(
        sources=[{"kind": "academy", "academy_id": robotica}, {"kind": "role", "role": "academy_admin"}],
        user_ids=[picked.id, uno.id],  # uno is already in the club: still once
        emails=["fuera@gmail.com", "FUERA@gmail.com", "uno@ipn.mx"],  # uno typed: that same user
    )
    body = _preview(as_superadmin, audience)
    items = [
        item for item in _list_all(as_superadmin, audience) if item["email"].endswith(("ipn.mx", "gmail.com"))
    ]
    by_email = {item["email"]: item for item in items}
    assert sorted(by_email) == sorted(
        ["uno@ipn.mx", "jefa@ipn.mx", "picked@ipn.mx", "also@ipn.mx", "fuera@gmail.com"]
    )
    assert len(items) == 5
    assert set(by_email["uno@ipn.mx"]["origins"]) == {f"academy:{robotica}", "picked", "outside"}
    assert set(by_email["jefa@ipn.mx"]["origins"]) == {f"academy:{robotica}", "role:academy_admin"}
    assert by_email["picked@ipn.mx"]["origins"] == ["picked"]
    assert by_email["also@ipn.mx"]["origins"] == ["role:academy_admin"]
    assert by_email["fuera@gmail.com"]["origins"] == ["outside"]
    assert by_email["fuera@gmail.com"]["user_id"] is None
    assert by_email["uno@ipn.mx"]["user_id"] == uno.id and by_email["jefa@ipn.mx"]["user_id"] == jefa.id
    assert by_email["also@ipn.mx"]["user_id"] == also.id
    assert {item["state"] for item in items} == {"receives"}
    receives = [item for item in _list_all(as_superadmin, audience) if item["state"] == "receives"]
    assert body["count"] == len(receives) == 5
    # "all" as a source covers everyone: one row per person
    everyone = _list_all(as_superadmin, _mix(sources=[{"kind": "all"}], emails=["uno@ipn.mx"]))
    emails = [item["email"] for item in everyone]
    assert len(emails) == len(set(emails)) == db.query(User).count()


def test_mix_exclusions_remove_campus_users(as_superadmin: TestClient, db: Session) -> None:
    robotica = _club(db)
    uno = _person(db, "uno@ipn.mx", enrolled=(robotica,))
    dos = _person(db, "dos@ipn.mx", enrolled=(robotica,))
    stranger = _person(db, "stranger@ipn.mx")
    audience = _mix(
        sources=[{"kind": "academy", "academy_id": robotica}],
        emails=["fuera@gmail.com"],
        exclude_user_ids=[uno.id, stranger.id, 999_999],  # ids outside the set are ignored
    )
    body = _preview(as_superadmin, audience)
    assert body["count"] == 2  # dos + the outside address
    assert body["removed"] == 1
    items = {item["email"]: item for item in _list_all(as_superadmin, audience)}
    assert items["uno@ipn.mx"]["state"] == "removed"
    assert items["dos@ipn.mx"]["state"] == "receives" and items["dos@ipn.mx"]["user_id"] == dos.id
    assert "stranger@ipn.mx" not in items
    removed = _list_all(as_superadmin, audience, state="removed")
    assert [item["user_id"] for item in removed] == [uno.id]
    # removing every campus user leaves only the typed address
    assert _preview(as_superadmin, {**audience, "exclude_user_ids": [uno.id, dos.id]})["count"] == 1


def test_mix_scope_for_academy_admin(as_admin_ia: TestClient, db: Session, seeded: dict) -> None:
    ia = seeded["academy_id"]
    robotica = _club(db)
    mine = _person(db, "mia@ipn.mx", enrolled=(ia,))
    co_admin = _person(db, "coadmin@ipn.mx", role=Role.academy_admin, academy_id=ia)
    theirs = _person(db, "ajena@ipn.mx", enrolled=(robotica,))
    ok = _mix(
        sources=[{"kind": "academy", "academy_id": ia}],
        user_ids=[mine.id, co_admin.id],
        exclude_user_ids=[theirs.id],  # removing is always safe, even outside the scope
        emails=["fuera@gmail.com"],
    )
    assert _preview(as_admin_ia, ok)["count"] >= 3
    assert as_admin_ia.post(LIST, json={"audience": ok}).status_code == 200
    forbidden = [
        _mix(sources=[{"kind": "all"}]),
        _mix(sources=[{"kind": "role", "role": "member"}]),
        _mix(sources=[{"kind": "academy", "academy_id": robotica}]),
        _mix(sources=[{"kind": "academy", "academy_id": ia}, {"kind": "academy", "academy_id": robotica}]),
        _mix(user_ids=[theirs.id]),
        _mix(user_ids=[mine.id, theirs.id]),
    ]
    for audience in forbidden:
        assert as_admin_ia.post(PREVIEW, json=audience).status_code == 403, audience
        assert as_admin_ia.post(LIST, json={"audience": audience}).status_code == 403, audience
    assert _preview(as_admin_ia, _mix(emails=["solo@gmail.com"]))["count"] == 1


def test_mix_caps_are_422(as_superadmin: TestClient) -> None:
    too_many = [
        _mix(sources=[{"kind": "all"}] * 11),
        _mix(user_ids=list(range(1, 1002))),
        _mix(sources=[{"kind": "all"}], exclude_user_ids=list(range(1, 5002))),
        _mix(),  # nothing to send to
        _mix(exclude_user_ids=[1]),  # exclusions alone are not an audience
        _mix(sources=[{"kind": "individual", "user_ids": [1]}]),  # sources are all|academy|role only
        _mix(sources=[{"kind": "mix", "sources": [{"kind": "all"}]}]),
        _mix(emails=["no-es-correo"]),
    ]
    for audience in too_many:
        assert as_superadmin.post(PREVIEW, json=audience).status_code == 422, audience
        assert as_superadmin.post(LIST, json={"audience": audience}).status_code == 422, audience
    # at the cap is fine
    assert as_superadmin.post(PREVIEW, json=_mix(sources=[{"kind": "all"}] * 10)).status_code == 200
    assert as_superadmin.post(PREVIEW, json=_mix(user_ids=list(range(1, 1001)))).status_code == 200
    # list paging params are bounded
    for extra in (
        {"limit": 51},
        {"limit": 0},
        {"state": "otro"},
        {"cursor": "no-es-cursor"},
        {"q": "x" * 101},
    ):
        body = {"audience": _mix(sources=[{"kind": "all"}]), **extra}
        assert as_superadmin.post(LIST, json=body).status_code == 422, extra


def test_mix_outside_addresses_over_the_quota_are_422(
    as_superadmin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "mail_monthly_limit", 2)
    audience = _mix(emails=["a@gmail.com", "b@gmail.com", "c@gmail.com"])
    for path, body in ((PREVIEW, audience), (LIST, {"audience": audience})):
        response = as_superadmin.post(path, json=body)
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == "quota_exceeded"


def test_mix_preview_counts_receives_removed_and_cannot(as_superadmin: TestClient, db: Session) -> None:
    robotica = _club(db)
    ok = _person(db, "ok@ipn.mx", enrolled=(robotica,))
    quitado = _person(db, "quitado@ipn.mx", enrolled=(robotica,))
    baja = _person(db, "baja@ipn.mx", enrolled=(robotica,), active=False)
    supr = _person(db, "supr@ipn.mx", enrolled=(robotica,))
    blocked = _person(db, "blocked@upiixsol.dev", enrolled=(robotica,))
    db.add(MailSuppression(email="supr@ipn.mx", reason="unsubscribed"))
    db.add(MailSuppression(email="fuera.supr@gmail.com", reason="bounced"))
    db.flush()
    audience = _mix(
        sources=[{"kind": "academy", "academy_id": robotica}],
        emails=["fuera@gmail.com", "fuera.supr@gmail.com"],
        exclude_user_ids=[quitado.id, baja.id],  # "cannot" wins over "removed" (no checkbox there)
    )
    body = _preview(as_superadmin, audience)
    assert body["count"] == 2
    assert body["removed"] == 1
    assert body["excluded"] == {"inactive": 1, "suppressed": 2, "blocked_domain": 1}
    states = {
        state: _list_all(as_superadmin, audience, state=state) for state in ("receives", "removed", "cannot")
    }
    assert sorted(item["email"] for item in states["receives"]) == ["fuera@gmail.com", "ok@ipn.mx"]
    assert [item["user_id"] for item in states["removed"]] == [quitado.id]
    cannot = {item["email"]: item["reason"] for item in states["cannot"]}
    assert cannot == {
        "baja@ipn.mx": "inactive",
        "supr@ipn.mx": "suppressed",
        "fuera.supr@gmail.com": "suppressed",
        "blocked@upiixsol.dev": "blocked_domain",
    }
    assert all(item["reason"] is None for item in states["receives"] + states["removed"])
    assert len(_list_all(as_superadmin, audience)) == sum(len(items) for items in states.values()) == 7
    assert body["count"] == len(states["receives"]) and body["removed"] == len(states["removed"])
    assert sum(body["excluded"].values()) == len(states["cannot"])
    assert ok.id in {item["user_id"] for item in states["receives"]}
    assert {supr.id, blocked.id} <= {item["user_id"] for item in states["cannot"]}


def test_mix_list_pages_with_origin_state_and_reason(as_superadmin: TestClient, db: Session) -> None:
    robotica = _club(db)
    people = [
        _person(db, f"p{i:02}@ipn.mx", enrolled=(robotica,), full_name=f"Persona {i:02} Robótica")
        for i in range(7)
    ]
    _person(db, "otra@ipn.mx", full_name="Zoila Nadie")
    audience = _mix(sources=[{"kind": "academy", "academy_id": robotica}], emails=["fuera@gmail.com"])
    first = as_superadmin.post(LIST, json={"audience": audience, "limit": 3})
    assert first.status_code == 200, first.text
    page = first.json()
    assert len(page["items"]) == 3 and page["next_cursor"]
    item = page["items"][0]
    assert set(item) == {"user_id", "name", "nickname", "email", "avatar_url", "origins", "state", "reason"}
    every = _list_all(as_superadmin, audience, limit=3)
    assert len(every) == 8
    keys = [(item["name"].lower(), item["email"]) for item in every]
    assert keys == sorted(keys)  # stable order, no overlap between pages
    assert len({item["email"] for item in every}) == 8
    outside = next(item for item in every if item["user_id"] is None)
    assert outside == {
        "user_id": None,
        "name": "fuera",
        "nickname": None,
        "email": "fuera@gmail.com",
        "avatar_url": None,
        "origins": ["outside"],
        "state": "receives",
        "reason": None,
    }
    # search by name, nickname or address
    assert [item["user_id"] for item in _list_all(as_superadmin, audience, q="persona 03")] == [people[3].id]
    assert [item["user_id"] for item in _list_all(as_superadmin, audience, q="p05@")] == [people[5].id]
    assert [item["email"] for item in _list_all(as_superadmin, audience, q="FUERA")] == ["fuera@gmail.com"]
    assert _list_all(as_superadmin, audience, q="zoila") == []


def test_list_returns_only_in_scope_people_with_email(
    as_admin_ia: TestClient, db: Session, seeded: dict
) -> None:
    ia = seeded["academy_id"]
    robotica = _club(db)
    lucia = _person(db, "lucia.secreta@ipn.mx", enrolled=(ia,), full_name="Lucía Pérez")
    _person(db, "luciano@ipn.mx", enrolled=(robotica,), full_name="Luciano Ajeno")
    audience = _mix(sources=[{"kind": "academy", "academy_id": ia}])
    items = _list_all(as_admin_ia, audience)
    assert items and all(item["email"] for item in items)
    assert "luciano@ipn.mx" not in {item["email"] for item in items}
    found = _list_all(as_admin_ia, audience, q="secreta")
    assert [(item["user_id"], item["email"]) for item in found] == [(lucia.id, "lucia.secreta@ipn.mx")]
    # every person listed is someone this admin may pick (enrollee or co-admin of their club)
    enrolled = {row.user_id for row in db.query(Enrollment).filter(Enrollment.academy_id == ia)}
    admins = {u.id for u in db.query(User).filter(User.role == Role.academy_admin, User.academy_id == ia)}
    assert {item["user_id"] for item in items} <= enrolled | admins


def test_mix_list_does_not_confirm_typed_addresses(
    as_admin_ia: TestClient, as_superadmin: TestClient, db: Session, seeded: dict
) -> None:
    ia = seeded["academy_id"]
    _person(db, "ajeno@ipn.mx", full_name="Ajeno Total")  # a campus user outside the club
    mia = _person(db, "mia@ipn.mx", enrolled=(ia,))
    db.add(MailSuppression(email="baja.fuera@gmail.com", reason="unsubscribed"))
    db.add(MailSuppression(email="ajeno@ipn.mx", reason="unsubscribed"))
    db.flush()
    typed = ["ajeno@ipn.mx", "baja.fuera@gmail.com", "mia@ipn.mx"]
    audience = _mix(user_ids=[mia.id], emails=typed)
    items = _list_all(as_admin_ia, audience)
    outside = [item for item in items if item["user_id"] is None]
    # each typed address is its own "De fuera" row, never merged with nor named after a campus user
    assert sorted(item["email"] for item in outside) == sorted(typed)
    assert all(item["origins"] == ["outside"] and item["state"] == "receives" for item in outside)
    assert all(item["reason"] is None and item["name"] == item["email"].partition("@")[0] for item in outside)
    assert "Ajeno" not in str(items)
    assert _preview(as_admin_ia, audience)["count"] == 4
    assert _list_all(as_admin_ia, audience, state="cannot") == []
    # a superadmin sees the truth: suppressed addresses and the campus user behind a typed address
    truth = {item["email"]: item for item in _list_all(as_superadmin, audience)}
    assert truth["baja.fuera@gmail.com"]["state"] == "cannot"
    assert truth["ajeno@ipn.mx"]["state"] == "cannot"
    assert truth["mia@ipn.mx"]["user_id"] == mia.id
