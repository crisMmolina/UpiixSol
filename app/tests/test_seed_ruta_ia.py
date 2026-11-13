"""Seed of the UpiixIA route "De cero a LLMs" (UPS-047, spec 002): fixture from the UPS-046 catalog,
idempotent by title, drafts unless `ok`, never edits a published lesson, never touches the demo route."""

import json
import math
import re

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LearningRoute, Lesson, LessonLink, Module
from app.seed import RUTA_IA, seed, seed_ruta_ia
from app.services.youtube import extract_video_id

TITLE = "De cero a LLMs"
DEMO_TITLE = "Fundamentos de IA con Python"
ES = "*Video en español.*"
EN = "*Video en inglés (activa subtítulos en español).*"


@pytest.fixture
def ruta(db: Session, seeded: dict) -> dict:
    """The demo seed plus the route, as `python -m app.seed --ruta-ia` does."""
    seed_ruta_ia(db)
    return seeded


def _fixture() -> dict:
    return json.loads(RUTA_IA.read_text(encoding="utf-8"))


def _route(db: Session, title: str = TITLE) -> LearningRoute:
    return db.scalar(select(LearningRoute).where(LearningRoute.title == title))


def _lessons(db: Session, route: LearningRoute) -> list[Lesson]:
    return list(
        db.scalars(
            select(Lesson)
            .join(Module)
            .where(Module.route_id == route.id)
            .order_by(Module.position, Lesson.position)
        )
    )


def _counts(db: Session) -> tuple[int, int, int]:
    route = _route(db)
    modules = db.scalar(select(func.count(Module.id)).where(Module.route_id == route.id))
    return db.scalar(select(func.count(LearningRoute.id))), modules, len(_lessons(db, route))


def _lesson(db: Session, title: str) -> Lesson:
    route = _route(db)
    return next(lesson for lesson in _lessons(db, route) if lesson.title == title)


def test_ruta_ia_fixture_valid() -> None:
    route = _fixture()["route"]
    assert route["title"] == TITLE and len(route["modules"]) == 9
    lessons = [lesson for module in route["modules"] for lesson in module["lessons"]]
    assert len(lessons) == 65
    for lesson in lessons:
        assert extract_video_id(lesson["youtube_url"]), lesson["youtube_url"]
        assert "t=" not in lesson["youtube_url"]  # the start lives in start_s, never in the stored URL
        assert lesson["lang"] in {"es", "en"} and lesson["status"] in {"ok", "sustituto"}
        if lesson["start_s"] is not None and lesson["end_s"] is not None:
            assert lesson["end_s"] > lesson["start_s"]
        for link in lesson["links"]:
            assert link["label"] and link["url"].startswith("https://")


def test_ruta_ia_seed_creates_nine_modules(db: Session, ruta: dict) -> None:
    route = _route(db)
    assert route is not None and route.academy_id == ruta["academy_id"] and route.is_published
    assert _counts(db)[1:] == (9, 65)
    order = select(Module.title).where(Module.route_id == route.id).order_by(Module.position)
    titles = db.scalars(order).all()
    assert titles[0] == "Python desde cero" and titles[-1] == "LLMs en la Jetson"


def test_ruta_ia_seed_idempotent(db: Session, ruta: dict, capsys) -> None:
    before = _counts(db)
    seed(db, ruta_ia=True)
    seed_ruta_ia(db)
    assert _counts(db) == before
    out = capsys.readouterr().out
    assert re.search(r"ruta-ia: \+0 modules, \+0 lessons, \d+ updated, 1 drafts", out), out


def test_ruta_ia_drafts_unless_ok(db: Session, ruta: dict) -> None:
    lessons = _lessons(db, _route(db))
    drafts = [lesson.title for lesson in lessons if not lesson.is_published]
    assert drafts == ["Ollama: LLMs locales"]  # 8.4, the only `sustituto` in the catalog
    assert sum(lesson.is_published for lesson in lessons) == 64


def test_ruta_ia_never_edits_published_lesson(db: Session, ruta: dict) -> None:
    published = _lesson(db, "Variables")
    draft = _lesson(db, "Ollama: LLMs locales")
    published.description, published.end_s = "Editada por el admin", 6000
    draft.description = "Borrador viejo"
    db.add(LessonLink(lesson_id=draft.id, label="Enlace viejo", url="https://example.com/viejo", position=0))
    db.flush()
    seed_ruta_ia(db)
    db.refresh(published)
    db.refresh(draft)
    assert (published.description, published.end_s) == ("Editada por el admin", 6000)
    assert draft.description.endswith(ES) and draft.description != "Borrador viejo"  # draft: refreshed
    links = db.scalars(select(LessonLink.label).where(LessonLink.lesson_id == draft.id)).all()
    assert "Enlace viejo" not in links  # a draft's links follow the fixture again


def test_ruta_ia_language_suffix(db: Session, ruta: dict) -> None:
    by_lang = {
        lesson["title"]: lesson["lang"]
        for module in _fixture()["route"]["modules"]
        for lesson in module["lessons"]
    }
    for lesson in _lessons(db, _route(db)):
        assert lesson.description.endswith(ES if by_lang[lesson.title] == "es" else EN), lesson.title


def test_ruta_ia_segment_duration(db: Session, ruta: dict) -> None:
    variables = _lesson(db, "Variables")
    assert (variables.start_s, variables.end_s) == (2938, 5665)
    assert variables.duration_min == math.ceil((5665 - 2938) / 60)
    assert variables.youtube_url == "https://www.youtube.com/watch?v=Kp4Mvapo5kc"


def test_ruta_ia_keeps_demo_route(db: Session, seeded: dict) -> None:
    assert _route(db) is None  # the default seed does not add it (human decision 2026-11-13)
    demo = _route(db, DEMO_TITLE)
    lessons = [(lesson.title, lesson.youtube_url, lesson.is_published) for lesson in _lessons(db, demo)]
    seed_ruta_ia(db)
    assert [
        (lesson.title, lesson.youtube_url, lesson.is_published) for lesson in _lessons(db, demo)
    ] == lessons
    assert len(lessons) == 4
