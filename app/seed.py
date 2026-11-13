"""Idempotent seed: accounts from IDEA §2.3 + the UpiixIA demo case (§3). Run: `uv run python -m app.seed`.

Running it twice changes nothing. Seeded accounts get `must_change_password = true`;
the initial password comes from SEED_DEFAULT_PASSWORD (prod refuses the documented default). While a
seeded account was never used, a new SEED_DEFAULT_PASSWORD replaces its provisional one (UPS-031).
"""

import json
import math
import sys
from datetime import timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Academy,
    BlogPost,
    Channel,
    ChannelType,
    Enrollment,
    Event,
    HomeContent,
    LearningRoute,
    Lesson,
    LessonLink,
    Module,
    Post,
    Project,
    ProjectStatus,
    Resource,
    ResourceType,
    Role,
    User,
)
from app.models.common import utcnow
from app.sanitize import clean_markdown
from app.security import hash_password, verify_password
from app.services.progress import complete_lesson
from app.services.youtube import extract_video_id

DEMO = Path(__file__).parent / "fixtures" / "demo.json"
# Club time: central Mexico, UTC-6 all year (no DST since 2022). Demo events are "17:00 local".
CLUB_TZ = timezone(timedelta(hours=-6), "America/Mexico_City")

ACCOUNTS = [
    *(
        {
            "email": f"superadmin{i}@upiixsol.dev",
            "role": Role.superadmin,
            "full_name": f"Superadmin {i}",
            "nickname": f"superadmin{i}",
        }
        for i in range(1, 5)
    ),
    {
        "email": "admin.ia@upiixsol.dev",
        "role": Role.academy_admin,
        "full_name": "Admin UpiixIA",
        "nickname": "admin.ia",
        "academy": "upiixia",
    },
    {
        "email": "alumno.demo@upiixsol.dev",
        "role": Role.member,
        "full_name": "Alumno Demo",
        "nickname": "alumno.demo",
        "boleta": "2026000001",
    },
]


def _get_or_create(db: Session, model, lookup: dict, values: dict | None = None):
    row = db.scalar(select(model).filter_by(**lookup))
    created = row is None
    if created:
        row = model(**lookup, **(values or {}))
        db.add(row)
        db.flush()
    return row, created


def _ensure_channels(db: Session, academy: Academy) -> Channel:
    _get_or_create(db, Channel, {"slug": "feed"}, {"type": ChannelType.feed, "name": "Feed"})
    _get_or_create(db, Channel, {"slug": "general"}, {"type": ChannelType.general, "name": "General"})
    channel, _ = _get_or_create(
        db,
        Channel,
        {"slug": academy.slug},
        {"type": ChannelType.academy, "name": academy.name, "academy_id": academy.id},
    )
    return channel


def _seed_route(db: Session, academy: Academy, data: dict) -> list[Lesson]:
    route = LearningRoute(
        academy_id=academy.id,
        title=data["title"],
        description=data["description"],
        is_published=True,
        position=0,
    )
    db.add(route)
    db.flush()
    lessons: list[Lesson] = []
    for m, module_data in enumerate(data["modules"]):
        module = Module(route_id=route.id, title=module_data["title"], position=m)
        db.add(module)
        db.flush()
        for i, lesson_data in enumerate(module_data["lessons"]):
            video_id = extract_video_id(lesson_data["youtube_url"])
            if video_id is None:  # pragma: no cover - guarded by test_seed
                raise ValueError(f"invalid demo video: {lesson_data['youtube_url']}")
            lesson = Lesson(
                module_id=module.id,
                title=lesson_data["title"],
                youtube_url=lesson_data["youtube_url"],
                youtube_video_id=video_id,
                description=clean_markdown(lesson_data["description"]),
                position=i,
                is_published=True,
            )
            db.add(lesson)
            db.flush()
            for j, link in enumerate(lesson_data["links"]):
                db.add(LessonLink(lesson_id=lesson.id, label=link["label"], url=link["url"], position=j))
            lessons.append(lesson)
    db.flush()
    return lessons


RUTA_IA = Path(__file__).parent / "fixtures" / "ruta-ia.json"


SUFFIX = {"es": "*Video en español.*", "en": "*Video en inglés (activa subtítulos en español).*"}


def _ruta_ia_values(data: dict, position: int) -> dict:
    """Seed-owned fields of a lesson: the canonical URL, the segment, the language suffix, the draft flag."""
    video_id = extract_video_id(data["youtube_url"])
    if video_id is None:  # pragma: no cover - guarded by test_ruta_ia_fixture_valid
        raise ValueError(f"invalid ruta-ia video: {data['youtube_url']}")
    start_s, end_s = data["start_s"], data["end_s"]
    description = "\n\n".join(part for part in (data.get("note", ""), SUFFIX[data["lang"]]) if part)
    return {
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "youtube_video_id": video_id,
        "start_s": start_s,
        "end_s": end_s,
        "duration_min": math.ceil((end_s - start_s) / 60)
        if start_s is not None and end_s is not None
        else None,
        "description": clean_markdown(description),
        "position": position,
        "is_published": data["status"] == "ok",
    }


def _set_ruta_ia_links(db: Session, lesson: Lesson, links: list[dict]) -> None:
    for old in db.scalars(select(LessonLink).where(LessonLink.lesson_id == lesson.id)):
        db.delete(old)
    db.flush()
    for j, link in enumerate(links):
        db.add(LessonLink(lesson_id=lesson.id, label=link["label"], url=link["url"], position=j))


def seed_ruta_ia(db: Session) -> dict:
    """The UpiixIA route "De cero a LLMs" from app/fixtures/ruta-ia.json (UPS-047, spec 002).

    Matched by title (route, module, lesson): creates what is missing, refreshes only lessons that are still
    unpublished, never edits a published lesson and never deletes. A lesson is published only when its catalog
    status is `ok`. The demo route is not touched. Prints a one-line summary.
    """
    data = json.loads(RUTA_IA.read_text(encoding="utf-8"))["route"]
    slug = json.loads(DEMO.read_text(encoding="utf-8"))["academy"]["slug"]
    academy = db.scalar(select(Academy).where(Academy.slug == slug))
    counts = {"modules": 0, "lessons": 0, "updated": 0, "drafts": 0}
    route = db.scalar(
        select(LearningRoute).where(
            LearningRoute.academy_id == academy.id, LearningRoute.title == data["title"]
        )
    )
    if route is None:
        position = db.scalar(
            select(func.count(LearningRoute.id)).where(LearningRoute.academy_id == academy.id)
        )
        route = LearningRoute(
            academy_id=academy.id,
            title=data["title"],
            description=data["description"],
            is_published=True,
            position=position,
        )
        db.add(route)
        db.flush()
    for m, module_data in enumerate(data["modules"]):
        module = db.scalar(
            select(Module).where(Module.route_id == route.id, Module.title == module_data["title"])
        )
        if module is None:
            module = Module(route_id=route.id, title=module_data["title"], position=m)
            db.add(module)
            db.flush()
            counts["modules"] += 1
        for i, lesson_data in enumerate(module_data["lessons"]):
            values = _ruta_ia_values(lesson_data, i)
            lesson = db.scalar(
                select(Lesson).where(Lesson.module_id == module.id, Lesson.title == lesson_data["title"])
            )
            if lesson is None:
                lesson = Lesson(module_id=module.id, title=lesson_data["title"], **values)
                db.add(lesson)
                db.flush()
                _set_ruta_ia_links(db, lesson, lesson_data["links"])
                counts["lessons"] += 1
            elif not lesson.is_published:  # published lessons belong to the admins now
                for field, value in values.items():
                    setattr(lesson, field, value)
                _set_ruta_ia_links(db, lesson, lesson_data["links"])
                counts["updated"] += 1
            counts["drafts"] += not lesson.is_published
    db.flush()
    print(  # noqa: T201 (operator summary, no personal data)
        f"ruta-ia: +{counts['modules']} modules, +{counts['lessons']} lessons, "
        f"{counts['updated']} updated, {counts['drafts']} drafts"
    )
    return counts


def seed(db: Session, ruta_ia: bool = False) -> dict:
    """Load accounts + demo data. Flushes but does not commit (the caller owns the transaction).

    `ruta_ia=True` also seeds the UpiixIA route "De cero a LLMs" (UPS-047): `python -m app.seed --ruta-ia`.
    """
    demo = json.loads(DEMO.read_text(encoding="utf-8"))
    seed_password = get_settings().seed_default_password
    password_hash = hash_password(seed_password)
    now = utcnow()

    academy_data = demo["academy"]
    academy, _ = _get_or_create(
        db, Academy, {"slug": academy_data["slug"]}, {k: v for k, v in academy_data.items() if k != "slug"}
    )
    channel = _ensure_channels(db, academy)

    users: dict[str, User] = {}
    for account in ACCOUNTS:
        values = {
            "role": account["role"],
            "full_name": account["full_name"],
            "nickname": account["nickname"],
            "boleta": account.get("boleta"),
            "password_hash": password_hash,
            "must_change_password": True,
            "academy_id": academy.id if account.get("academy") else None,
        }
        user, created = _get_or_create(db, User, {"email": account["email"]}, values)
        # Never used since seeding (no change, no admin reset): its provisional password follows
        # SEED_DEFAULT_PASSWORD, so a lost first value is recovered with a new one (UPS-031).
        never_used = user.must_change_password and user.password_changed_at is None
        if not created and never_used and not verify_password(user.password_hash, seed_password):
            user.password_hash = password_hash
        users[account["email"]] = user
    member = users["alumno.demo@upiixsol.dev"]
    _get_or_create(db, Enrollment, {"user_id": member.id, "academy_id": academy.id})

    home, _ = _get_or_create(
        db,
        HomeContent,
        {"id": 1},
        {
            "hero_title": demo["home"]["hero_title"],
            "hero_text": demo["home"]["hero_text"],
            "highlighted_academy_ids": [academy.id],
            "featured_project_ids": [],
        },
    )

    has_content = db.scalar(select(LearningRoute.id).where(LearningRoute.academy_id == academy.id).limit(1))
    if not has_content:
        lessons = _seed_route(db, academy, demo["route"])
        for lesson in lessons[: demo["member_completed_lessons"]]:
            complete_lesson(db, member.id, lesson.id)

        for item in demo["resources"]:
            db.add(
                Resource(
                    academy_id=academy.id,
                    type=ResourceType(item["type"]),
                    title=item["title"],
                    description=item["description"],
                    url=item["url"],
                )
            )

        today = now.astimezone(CLUB_TZ).replace(minute=0, second=0, microsecond=0)
        for item in demo["events"]:
            starts = (today + timedelta(days=item["days_from_now"])).replace(hour=item["hour"])
            db.add(
                Event(
                    academy_id=academy.id if item["academy"] else None,
                    title=item["title"],
                    description=item["description"],
                    location=item["location"],
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=item["duration_h"]),
                    created_by_id=users["superadmin1@upiixsol.dev"].id,
                )
            )

        for minutes_ago, item in zip(range(len(demo["posts"]) * 30, 0, -30), demo["posts"], strict=True):
            db.add(
                Post(
                    channel_id=channel.id,
                    author_id=users[item["author"]].id,
                    body=clean_markdown(item["body"]),
                    link_url=item.get("link_url"),
                    created_at=now - timedelta(minutes=minutes_ago),
                )
            )

    if ruta_ia:  # on request only (human decision 2026-11-13): tests and e2e keep the single demo route
        seed_ruta_ia(db)

    projects = []
    for item in demo["projects"]:
        project, _ = _get_or_create(
            db,
            Project,
            {"slug": item["slug"]},
            {
                "title": item["title"],
                "summary": item["summary"],
                "authors": item["authors"],
                "tags": item["tags"],
                "body": item["summary"],
                "academy_id": academy.id if "vision" in item["tags"] else None,
                "status": ProjectStatus.published,
                "published_at": now - timedelta(days=item["days_ago"]),
            },
        )
        projects.append(project)
    if not home.featured_project_ids:
        home.featured_project_ids = [p.id for p in projects[:2]]

    for item in demo["blog"]:
        _get_or_create(
            db,
            BlogPost,
            {"slug": item["slug"]},
            {
                "title": item["title"],
                "body": item["body"],
                "author_id": users[item["author"]].id,
                "published_at": now - timedelta(days=item["days_ago"]),
            },
        )
    db.flush()
    return {
        "academy_id": academy.id,
        "channel_id": channel.id,
        "member_id": member.id,
        "admin_ia_id": users["admin.ia@upiixsol.dev"].id,
        "superadmin_id": users["superadmin1@upiixsol.dev"].id,
    }


def main() -> None:  # pragma: no cover - thin CLI wrapper, exercised manually / in compose
    from app.db import SessionLocal

    with SessionLocal() as db:
        result = seed(db, ruta_ia="--ruta-ia" in sys.argv[1:])
        db.commit()
    print(f"SEED_OK academy_id={result['academy_id']} accounts={len(ACCOUNTS)}")  # noqa: T201 (no secrets printed)


if __name__ == "__main__":  # pragma: no cover
    main()
