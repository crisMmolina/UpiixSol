from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Academy, LearningRoute, Lesson, LessonProgress, Module, User
from app.models.common import utcnow
from app.services.progress import (
    academy_continue,
    complete_lesson,
    route_progress,
    routes_progress,
)


def _route(db: Session, academy: Academy, *, lessons_per_module=(2, 2), published=True) -> LearningRoute:
    route = LearningRoute(academy_id=academy.id, title="Ruta", is_published=published)
    db.add(route)
    db.flush()
    for m, count in enumerate(lessons_per_module):
        module = Module(route_id=route.id, title=f"M{m}", position=m)
        db.add(module)
        db.flush()
        for i in range(count):
            db.add(
                Lesson(
                    module_id=module.id,
                    title=f"L{m}.{i}",
                    youtube_url="u",
                    youtube_video_id="dQw4w9WgXcQ",
                    position=i,
                    is_published=True,
                )
            )
    db.flush()
    return route


def _lessons(db: Session, route: LearningRoute) -> list[Lesson]:
    return list(
        db.query(Lesson)
        .join(Module)
        .filter(Module.route_id == route.id)
        .order_by(Module.position, Lesson.position)
    )


def test_two_of_four_is_50_percent_and_next_is_lesson_3(db: Session, academy: Academy, member: User) -> None:
    route = _route(db, academy)
    lessons = _lessons(db, route)
    complete_lesson(db, member.id, lessons[0].id)
    complete_lesson(db, member.id, lessons[1].id)

    progress = route_progress(db, member.id, route.id)
    assert (progress.completed, progress.total, progress.percent) == (2, 4, 50)
    assert progress.next_lesson_id == lessons[2].id


def test_unpublished_lessons_do_not_count(db: Session, academy: Academy, member: User) -> None:
    route = _route(db, academy)
    lessons = _lessons(db, route)
    lessons[3].is_published = False
    complete_lesson(db, member.id, lessons[0].id)
    complete_lesson(db, member.id, lessons[3].id)  # completed before being unpublished

    progress = route_progress(db, member.id, route.id)
    assert (progress.completed, progress.total, progress.percent) == (1, 3, 33)


def test_empty_route_is_zero_percent(db: Session, academy: Academy, member: User) -> None:
    route = _route(db, academy, lessons_per_module=())
    progress = route_progress(db, member.id, route.id)
    assert (progress.completed, progress.total, progress.percent, progress.next_lesson_id) == (0, 0, 0, None)


def test_all_complete_is_100_and_no_next(db: Session, academy: Academy, member: User) -> None:
    route = _route(db, academy, lessons_per_module=(1,))
    complete_lesson(db, member.id, _lessons(db, route)[0].id)
    progress = route_progress(db, member.id, route.id)
    assert (progress.percent, progress.next_lesson_id) == (100, None)


def test_complete_is_idempotent_and_stays_completed(
    db: Session, academy: Academy, member: User
) -> None:
    route = _route(db, academy, lessons_per_module=(1,))
    lesson = _lessons(db, route)[0]
    first = complete_lesson(db, member.id, lesson.id)
    again = complete_lesson(db, member.id, lesson.id)
    assert first.completed_at == again.completed_at

    row = db.get(LessonProgress, (member.id, lesson.id))
    assert row is not None and row.completed_at == first.completed_at  # nothing unmarks it (UPS-062)
    assert route_progress(db, member.id, route.id).percent == 100


def test_routes_progress_batches_several_routes(db: Session, academy: Academy, member: User) -> None:
    a = _route(db, academy)
    b = _route(db, academy, lessons_per_module=(3,))
    complete_lesson(db, member.id, _lessons(db, b)[0].id)
    result = routes_progress(db, member.id, [a.id, b.id])
    assert (result[a.id].percent, result[b.id].percent) == (0, 33)
    assert routes_progress(db, member.id, []) == {}


def test_academy_continue_uses_last_viewed_route(db: Session, academy: Academy, member: User) -> None:
    first = _route(db, academy)
    second = _route(db, academy)
    first.position, second.position = 0, 1
    lessons = _lessons(db, second)
    complete_lesson(db, member.id, lessons[0].id)
    complete_lesson(db, member.id, lessons[1].id)
    row = db.get(LessonProgress, (member.id, lessons[1].id))
    row.last_viewed_at = utcnow() + timedelta(minutes=5)
    db.flush()

    info = academy_continue(db, member.id, academy.id)
    assert info is not None
    assert (info.route_id, info.lesson_id, info.lesson_number, info.percent) == (
        second.id,
        lessons[2].id,
        3,
        50,
    )
    assert info.lesson_title == "L1.0"


def test_academy_continue_defaults_to_first_published_route(
    db: Session, academy: Academy, member: User
) -> None:
    _route(db, academy, published=False)
    route = _route(db, academy)
    info = academy_continue(db, member.id, academy.id)
    assert info is not None
    assert (info.route_id, info.lesson_number, info.percent) == (route.id, 1, 0)


def test_academy_continue_when_finished_points_to_last_lesson(
    db: Session, academy: Academy, member: User
) -> None:
    route = _route(db, academy, lessons_per_module=(2,))
    for lesson in _lessons(db, route):
        complete_lesson(db, member.id, lesson.id)
    info = academy_continue(db, member.id, academy.id)
    assert info is not None
    assert (info.lesson_id, info.percent) == (_lessons(db, route)[-1].id, 100)


def test_academy_continue_none_without_content(db: Session, academy: Academy, member: User) -> None:
    assert academy_continue(db, member.id, academy.id) is None
    _route(db, academy, lessons_per_module=())
    assert academy_continue(db, member.id, academy.id) is None
