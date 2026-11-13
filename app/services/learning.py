"""Learning routes, course player and progress (flow step 3).

Members only see published routes/lessons of active academies; the academy's admins and superadmins
can preview unpublished content (they build it in UPS-008).
"""

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import Academy, LearningRoute, Lesson, LessonProgress, Module, User
from app.schemas.learning import (
    LessonLinkOut,
    LessonOut,
    LessonSummaryOut,
    ModuleOut,
    RouteCardOut,
    RouteDetailOut,
    RouteProgressOut,
)
from app.security import can_manage_academy
from app.services import progress
from app.services.youtube import embed_url, thumbnail_url


class CompletionOut(BaseModel):
    lesson_id: int
    completed: bool
    progress: RouteProgressOut


def _not_found() -> AppError:
    return AppError(404, "No encontramos ese contenido.")


def _visible(academy: Academy, user: User) -> bool:
    return academy.is_active or can_manage_academy(user, academy.id)


def _progress_out(db: Session, user: User, route_id: int) -> RouteProgressOut:
    return RouteProgressOut(**progress.route_progress(db, user.id, route_id).__dict__)


def routes_stmt(academy: Academy, user: User):
    stmt = select(LearningRoute).where(LearningRoute.academy_id == academy.id)
    if not can_manage_academy(user, academy.id):
        stmt = stmt.where(LearningRoute.is_published.is_(True))
    return stmt


def route_cards(db: Session, user: User, routes: list[LearningRoute]) -> list[RouteCardOut]:
    by_route = progress.routes_progress(db, user.id, [r.id for r in routes])
    return [
        RouteCardOut.model_validate(r).model_copy(
            update={"progress": RouteProgressOut(**by_route[r.id].__dict__)}
        )
        for r in routes
    ]


def get_route(db: Session, route_id: int, user: User) -> tuple[LearningRoute, Academy]:
    row = db.execute(
        select(LearningRoute, Academy)
        .join(Academy, Academy.id == LearningRoute.academy_id)
        .where(LearningRoute.id == route_id)
    ).first()
    if row is None:
        raise _not_found()
    route, academy = row
    manager = can_manage_academy(user, academy.id)
    if not _visible(academy, user) or (not route.is_published and not manager):
        raise _not_found()
    return route, academy


def route_detail(db: Session, route_id: int, user: User) -> RouteDetailOut:
    route, academy = get_route(db, route_id, user)
    show_drafts = can_manage_academy(user, academy.id)
    modules = list(
        db.scalars(
            select(Module)
            .where(Module.route_id == route.id)
            .options(selectinload(Module.lessons))
            .order_by(Module.position, Module.id)
        )
    )
    lesson_ids = [lesson.id for m in modules for lesson in m.lessons]
    done = (
        set(
            db.scalars(
                select(LessonProgress.lesson_id).where(
                    LessonProgress.user_id == user.id,
                    LessonProgress.lesson_id.in_(lesson_ids),
                    LessonProgress.completed_at.is_not(None),
                )
            )
        )
        if lesson_ids
        else set()
    )

    module_out = []
    for module in modules:
        lessons = [lesson for lesson in module.lessons if lesson.is_published or show_drafts]
        summaries = [
            LessonSummaryOut.model_validate(lesson).model_copy(update={"completed": lesson.id in done})
            for lesson in lessons
        ]
        published = [lesson for lesson in lessons if lesson.is_published]
        module_out.append(
            ModuleOut(
                id=module.id,
                title=module.title,
                position=module.position,
                completed=sum(1 for lesson in published if lesson.id in done),
                total=len(published),
                lessons=summaries,
            )
        )
    # From the card (no relationships): RouteDetailOut.model_validate(route) would lazy-load `modules`.
    card = RouteCardOut.model_validate(route).model_dump(exclude={"progress"})
    return RouteDetailOut(**card, progress=_progress_out(db, user, route.id), modules=module_out)


def get_lesson(db: Session, lesson_id: int, user: User) -> tuple[Lesson, LearningRoute, Academy]:
    row = db.execute(
        select(Lesson, LearningRoute, Academy)
        .join(Module, Module.id == Lesson.module_id)
        .join(LearningRoute, LearningRoute.id == Module.route_id)
        .join(Academy, Academy.id == LearningRoute.academy_id)
        .where(Lesson.id == lesson_id)
    ).first()
    if row is None:
        raise _not_found()
    lesson, route, academy = row
    manager = can_manage_academy(user, academy.id)
    if not _visible(academy, user) or (not manager and not (route.is_published and lesson.is_published)):
        raise _not_found()
    return lesson, route, academy


def _neighbours(
    db: Session, route_id: int, lesson_id: int, include_drafts: bool
) -> tuple[int | None, int | None]:
    stmt = (
        select(Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.route_id == route_id)
        .order_by(Module.position, Module.id, Lesson.position, Lesson.id)
    )
    if not include_drafts:
        stmt = stmt.where(Lesson.is_published.is_(True))
    ordered = list(db.scalars(stmt))
    index = ordered.index(lesson_id)  # always present: drafts are included when previewing one
    prev_id = ordered[index - 1] if index > 0 else None
    next_id = ordered[index + 1] if index + 1 < len(ordered) else None
    return prev_id, next_id


def lesson_detail(db: Session, lesson_id: int, user: User) -> LessonOut:
    lesson, route, academy = get_lesson(db, lesson_id, user)
    links = (
        db.scalars(select(Lesson).where(Lesson.id == lesson.id).options(selectinload(Lesson.links)))
        .one()
        .links
    )
    row = progress.mark_viewed(db, user.id, lesson.id)
    prev_id, next_id = _neighbours(db, route.id, lesson.id, include_drafts=not lesson.is_published)
    return LessonOut(
        id=lesson.id,
        module_id=lesson.module_id,
        route_id=route.id,
        academy_slug=academy.slug,
        title=lesson.title,
        youtube_video_id=lesson.youtube_video_id,
        embed_url=embed_url(lesson.youtube_video_id, lesson.start_s, lesson.end_s),
        thumbnail_url=thumbnail_url(lesson.youtube_video_id),
        description=lesson.description,
        duration_min=lesson.duration_min,
        start_s=lesson.start_s,
        end_s=lesson.end_s,
        is_published=lesson.is_published,
        links=[LessonLinkOut.model_validate(link) for link in links],
        completed=row.completed_at is not None,
        completed_at=row.completed_at,
        prev_lesson_id=prev_id,
        next_lesson_id=next_id,
    )


def set_completed(db: Session, lesson_id: int, user: User, completed: bool) -> CompletionOut:
    lesson, route, _academy = get_lesson(db, lesson_id, user)
    if completed:
        progress.complete_lesson(db, user.id, lesson.id)
    else:
        progress.uncomplete_lesson(db, user.id, lesson.id)
    return CompletionOut(lesson_id=lesson.id, completed=completed, progress=_progress_out(db, user, route.id))
