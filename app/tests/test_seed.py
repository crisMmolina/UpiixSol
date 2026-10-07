from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Academy,
    BlogPost,
    Channel,
    Enrollment,
    Event,
    HomeContent,
    LearningRoute,
    Lesson,
    LessonLink,
    Post,
    Project,
    Resource,
    Role,
    User,
)
from app.security import verify_password
from app.seed import ACCOUNTS, seed
from app.services.progress import academy_continue


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_seed_creates_accounts_from_idea(db: Session) -> None:
    seed(db)
    users = {u.email: u for u in db.scalars(select(User))}
    assert set(users) == {a["email"] for a in ACCOUNTS}
    assert sum(u.role == Role.superadmin for u in users.values()) == 4
    admin = users["admin.ia@upiixsol.dev"]
    academy = db.scalar(select(Academy).filter_by(slug="upiixia"))
    assert admin.role == Role.academy_admin and admin.academy_id == academy.id
    assert all(u.must_change_password for u in users.values())
    assert users["alumno.demo@upiixsol.dev"].boleta == "2026000001"
    assert users["superadmin1@upiixsol.dev"].boleta is None
    assert verify_password(admin.password_hash, "admin123")
    assert "admin123" not in admin.password_hash


def test_seed_demo_case_matches_idea_section_3(db: Session) -> None:
    ids = seed(db)
    assert _count(db, LearningRoute) == 1
    assert _count(db, Lesson) == 4
    assert _count(db, LessonLink) >= 2
    assert _count(db, Resource) == 3
    assert _count(db, Event) == 2
    assert _count(db, Post) == 5
    assert _count(db, Project) == 3
    assert _count(db, BlogPost) == 1
    assert {c.slug for c in db.scalars(select(Channel))} == {"feed", "general", "upiixia"}
    assert db.get(Enrollment, (ids["member_id"], ids["academy_id"])) is not None
    assert db.get(HomeContent, 1).featured_project_ids

    info = academy_continue(db, ids["member_id"], ids["academy_id"])
    assert info is not None
    assert (info.lesson_number, info.percent) == (3, 50)


def test_seed_is_idempotent(db: Session) -> None:
    seed(db)
    counts = [
        _count(db, m) for m in (User, Academy, Lesson, Post, Event, Project, BlogPost, Channel, Resource)
    ]
    seed(db)
    assert counts == [
        _count(db, m) for m in (User, Academy, Lesson, Post, Event, Project, BlogPost, Channel, Resource)
    ]


def test_seed_uses_configured_password(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "seed_default_password", "otra-clave-larga-123")
    seed(db)
    user = db.scalar(select(User).filter_by(email="superadmin2@upiixsol.dev"))
    assert verify_password(user.password_hash, "otra-clave-larga-123")


def test_migrations_match_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Alembic head == models (what CI's `alembic check` enforces), and downgrade is clean."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "head")
        command.check(config)
        engine = create_engine(url)
        assert "lesson_progress" in inspect(engine).get_table_names()
        command.downgrade(config, "base")
        assert inspect(engine).get_table_names() == ["alembic_version"]
        engine.dispose()
    finally:
        get_settings.cache_clear()


def test_postgres_migration_sql_has_unique_constraint_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: enum CHECKs were emitted 3x with the same name in 0001 (Postgres DuplicateObject;
    SQLite silently accepts it). Renders the migration as Postgres SQL offline (no database needed)."""
    import io
    import re
    from collections import Counter

    from alembic import command
    from alembic.config import Config

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pw@localhost:5432/offline")
    from app.config import get_settings

    get_settings.cache_clear()
    buffer = io.StringIO()
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"), output_buffer=buffer)
        command.upgrade(config, "head", sql=True)
    finally:
        get_settings.cache_clear()
    sql = buffer.getvalue()
    assert "CREATE TABLE channels" in sql
    for statement in sql.split(";"):
        names = Counter(re.findall(r"CONSTRAINT (\w+)", statement))
        duplicated = [name for name, count in names.items() if count > 1]
        assert not duplicated, duplicated
