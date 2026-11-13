"""Progress = completed published lessons ÷ published lessons of the route, always computed here (IDEA §5)."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LearningRoute, Lesson, LessonProgress, Module
from app.models.common import utcnow


@dataclass(frozen=True)
class RouteProgress:
    completed: int
    total: int
    percent: int
    next_lesson_id: int | None


@dataclass(frozen=True)
class ContinueInfo:
    route_id: int
    lesson_id: int
    lesson_title: str
    lesson_number: int
    percent: int


def _percent(completed: int, total: int) -> int:
    return round(100 * completed / total) if total else 0


def _published_lessons(db: Session, route_ids: Sequence[int]) -> list[tuple[int, int, str]]:
    """(route_id, lesson_id, title) of published lessons, in course order."""
    rows = db.execute(
        select(Module.route_id, Lesson.id, Lesson.title)
        .join(Lesson, Lesson.module_id == Module.id)
        .where(Module.route_id.in_(route_ids), Lesson.is_published.is_(True))
        .order_by(Module.route_id, Module.position, Module.id, Lesson.position, Lesson.id)
    )
    return [(r[0], r[1], r[2]) for r in rows]


def _completed_ids(db: Session, user_id: int, lesson_ids: Sequence[int]) -> set[int]:
    if not lesson_ids:
        return set()
    return set(
        db.scalars(
            select(LessonProgress.lesson_id).where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id.in_(lesson_ids),
                LessonProgress.completed_at.is_not(None),
            )
        )
    )


def routes_progress(db: Session, user_id: int, route_ids: Sequence[int]) -> dict[int, RouteProgress]:
    """Progress of several routes in 2 queries (no N+1)."""
    if not route_ids:
        return {}
    lessons = _published_lessons(db, route_ids)
    done = _completed_ids(db, user_id, [lesson_id for _, lesson_id, _ in lessons])
    result: dict[int, RouteProgress] = {}
    for route_id in route_ids:
        ordered = [lesson_id for rid, lesson_id, _ in lessons if rid == route_id]
        completed = sum(1 for lesson_id in ordered if lesson_id in done)
        next_id = next((lesson_id for lesson_id in ordered if lesson_id not in done), None)
        result[route_id] = RouteProgress(completed, len(ordered), _percent(completed, len(ordered)), next_id)
    return result


def route_progress(db: Session, user_id: int, route_id: int) -> RouteProgress:
    return routes_progress(db, user_id, [route_id])[route_id]


def academy_continue(db: Session, user_id: int, academy_id: int) -> ContinueInfo | None:
    """ "Continuar donde te quedaste": the route viewed most recently, else the first published route."""
    route_ids = list(
        db.scalars(
            select(LearningRoute.id)
            .where(LearningRoute.academy_id == academy_id, LearningRoute.is_published.is_(True))
            .order_by(LearningRoute.position, LearningRoute.id)
        )
    )
    if not route_ids:
        return None
    last_viewed_route = db.scalar(
        select(Module.route_id)
        .join(Lesson, Lesson.module_id == Module.id)
        .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
        .where(LessonProgress.user_id == user_id, Module.route_id.in_(route_ids))
        .order_by(func.coalesce(LessonProgress.last_viewed_at, LessonProgress.completed_at).desc())
        .limit(1)
    )
    candidates = [last_viewed_route] if last_viewed_route else route_ids
    lessons = _published_lessons(db, candidates)
    for route_id in candidates:
        ordered = [(lesson_id, title) for rid, lesson_id, title in lessons if rid == route_id]
        if not ordered:
            continue
        done = _completed_ids(db, user_id, [lesson_id for lesson_id, _ in ordered])
        index = next(
            (i for i, (lesson_id, _) in enumerate(ordered) if lesson_id not in done), len(ordered) - 1
        )
        lesson_id, title = ordered[index]
        return ContinueInfo(route_id, lesson_id, title, index + 1, _percent(len(done), len(ordered)))
    return None


def _progress_row(db: Session, user_id: int, lesson_id: int) -> LessonProgress:
    row = db.get(LessonProgress, (user_id, lesson_id))
    if row is None:
        row = LessonProgress(user_id=user_id, lesson_id=lesson_id)
        db.add(row)
    return row


def mark_viewed(db: Session, user_id: int, lesson_id: int) -> LessonProgress:
    row = _progress_row(db, user_id, lesson_id)
    row.last_viewed_at = utcnow()
    db.flush()
    return row


def complete_lesson(db: Session, user_id: int, lesson_id: int) -> LessonProgress:
    """Idempotent: completing twice keeps the first completion time."""
    row = _progress_row(db, user_id, lesson_id)
    now = utcnow()
    row.completed_at = row.completed_at or now
    row.last_viewed_at = now
    db.flush()
    return row
