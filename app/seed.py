"""Idempotent seed: accounts from IDEA §2.3 + the UpiixIA demo case (§3). Run: `uv run python -m app.seed`.

Running it twice changes nothing. Seeded accounts get `must_change_password = true`;
the initial password comes from SEED_DEFAULT_PASSWORD (prod refuses the documented default).
"""

import json
from datetime import timedelta, timezone
from pathlib import Path

from sqlalchemy import select
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
from app.security import hash_password
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


def seed(db: Session) -> dict:
    """Load accounts + demo data. Flushes but does not commit (the caller owns the transaction)."""
    demo = json.loads(DEMO.read_text(encoding="utf-8"))
    password_hash = hash_password(get_settings().seed_default_password)
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
        users[account["email"]], _ = _get_or_create(db, User, {"email": account["email"]}, values)
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
        result = seed(db)
        db.commit()
    print(f"SEED_OK academy_id={result['academy_id']} accounts={len(ACCOUNTS)}")  # noqa: T201 (no secrets printed)


if __name__ == "__main__":  # pragma: no cover
    main()
