"""Academy panel (flow step 5): identity, routes → modules → lessons, enrollees.

Every write resolves the academy from the database row being changed and calls ensure_academy_scope:
an academy_admin can only touch their own academy; superadmins can touch any.
"""

from datetime import datetime

from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import Academy, Enrollment, LearningRoute, Lesson, LessonLink, Module, Role, User
from app.pagination import paginate
from app.sanitize import clean_markdown
from app.schemas.academies import AcademyOut, BrandingUpdateIn
from app.schemas.common import OutModel, Page
from app.schemas.learning import (
    LessonIn,
    LessonLinkIn,
    LessonLinkOut,
    LessonUpdateIn,
    ModuleIn,
    RouteIn,
    RouteUpdateIn,
)
from app.security import ensure_academy_scope
from app.services import media
from app.services.youtube import extract_video_id

# ── Feature-local response models ────────────────────────────


class LessonAdminOut(OutModel):
    id: int
    module_id: int
    title: str
    youtube_url: str
    youtube_video_id: str
    description: str
    duration_min: int | None
    position: int
    is_published: bool
    links: list[LessonLinkOut] = []


class ModuleAdminOut(OutModel):
    id: int
    route_id: int
    title: str
    position: int
    lessons: list[LessonAdminOut] = []


class RouteAdminOut(OutModel):
    id: int
    academy_id: int
    title: str
    description: str
    position: int
    is_published: bool
    modules: list[ModuleAdminOut] = []


class ContentOut(BaseModel):
    academy_id: int
    routes: list[RouteAdminOut]


class EnrolleeOut(OutModel):
    user_id: int
    full_name: str
    nickname: str
    email: str
    boleta: str | None
    enrolled_at: datetime


class EnrollIn(BaseModel):
    boleta: str


# ── Loading with scope ───────────────────────────────────────


def _not_found() -> AppError:
    return AppError(404, "No encontramos ese contenido.")


def academy_for(db: Session, academy_id: int, user: User) -> Academy:
    academy = db.get(Academy, academy_id)
    if academy is None:
        raise _not_found()
    ensure_academy_scope(user, academy.id)
    return academy


def route_for(db: Session, route_id: int, user: User) -> LearningRoute:
    route = db.get(LearningRoute, route_id)
    if route is None:
        raise _not_found()
    ensure_academy_scope(user, route.academy_id)
    return route


def module_for(db: Session, module_id: int, user: User) -> tuple[Module, LearningRoute]:
    row = db.execute(
        select(Module, LearningRoute)
        .join(LearningRoute, LearningRoute.id == Module.route_id)
        .where(Module.id == module_id)
    ).first()
    if row is None:
        raise _not_found()
    ensure_academy_scope(user, row[1].academy_id)
    return row[0], row[1]


def lesson_for(db: Session, lesson_id: int, user: User) -> Lesson:
    row = db.execute(
        select(Lesson, LearningRoute.academy_id)
        .join(Module, Module.id == Lesson.module_id)
        .join(LearningRoute, LearningRoute.id == Module.route_id)
        .where(Lesson.id == lesson_id)
    ).first()
    if row is None:
        raise _not_found()
    ensure_academy_scope(user, row[1])
    return row[0]


# ── Branding ─────────────────────────────────────────────────


def update_branding(db: Session, academy: Academy, data: BrandingUpdateIn) -> AcademyOut:
    values = data.model_dump(exclude_unset=True)
    if "welcome_text" in values and values["welcome_text"] is not None:
        values["welcome_text"] = clean_markdown(values["welcome_text"])
    for field, value in values.items():
        if value is None and field != "color_accent_2":
            continue
        setattr(academy, field, value)
    db.flush()
    return AcademyOut.model_validate(academy)


async def upload_image(db: Session, academy: Academy, file: UploadFile, kind: str) -> AcademyOut:
    url = await media.save_upload(file, kind)  # type: ignore[arg-type]
    field = f"{kind}_url"
    previous = getattr(academy, field)
    setattr(academy, field, url)
    db.flush()
    media.delete_media(previous)  # only removes files we stored under /media
    return AcademyOut.model_validate(academy)


# ── Content tree ─────────────────────────────────────────────


def _lesson_out(lesson: Lesson) -> LessonAdminOut:
    return LessonAdminOut(
        id=lesson.id,
        module_id=lesson.module_id,
        title=lesson.title,
        youtube_url=lesson.youtube_url,
        youtube_video_id=lesson.youtube_video_id,
        description=lesson.description,
        duration_min=lesson.duration_min,
        position=lesson.position,
        is_published=lesson.is_published,
        links=[LessonLinkOut.model_validate(link) for link in lesson.links],
    )


def content_tree(db: Session, academy: Academy) -> ContentOut:
    routes = db.scalars(
        select(LearningRoute)
        .where(LearningRoute.academy_id == academy.id)
        .options(selectinload(LearningRoute.modules).selectinload(Module.lessons).selectinload(Lesson.links))
        .order_by(LearningRoute.position, LearningRoute.id)
    )
    return ContentOut(
        academy_id=academy.id,
        routes=[
            RouteAdminOut(
                id=r.id,
                academy_id=r.academy_id,
                title=r.title,
                description=r.description,
                position=r.position,
                is_published=r.is_published,
                modules=[
                    ModuleAdminOut(
                        id=m.id,
                        route_id=m.route_id,
                        title=m.title,
                        position=m.position,
                        lessons=[_lesson_out(lesson) for lesson in m.lessons],
                    )
                    for m in r.modules
                ],
            )
            for r in routes
        ],
    )


def _next_position(db: Session, column, *where) -> int:
    current = db.scalar(select(func.max(column)).where(*where))
    return 0 if current is None else current + 1


def _route_out(route: LearningRoute) -> RouteAdminOut:
    return RouteAdminOut(
        id=route.id,
        academy_id=route.academy_id,
        title=route.title,
        description=route.description,
        position=route.position,
        is_published=route.is_published,
    )


def create_route(db: Session, academy: Academy, data: RouteIn) -> RouteAdminOut:
    route = LearningRoute(
        academy_id=academy.id,
        title=data.title,
        description=clean_markdown(data.description),
        is_published=data.is_published,
        position=_next_position(db, LearningRoute.position, LearningRoute.academy_id == academy.id),
    )
    db.add(route)
    db.flush()
    return _route_out(route)


def update_route(db: Session, route: LearningRoute, data: RouteUpdateIn) -> RouteAdminOut:
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    if "description" in values:
        values["description"] = clean_markdown(values["description"])
    for field, value in values.items():
        setattr(route, field, value)
    db.flush()
    return _route_out(route)


def create_module(db: Session, route: LearningRoute, data: ModuleIn) -> ModuleAdminOut:
    module = Module(
        route_id=route.id,
        title=data.title,
        position=_next_position(db, Module.position, Module.route_id == route.id),
    )
    db.add(module)
    db.flush()
    return ModuleAdminOut(id=module.id, route_id=route.id, title=module.title, position=module.position)


def update_module(db: Session, module: Module, data: ModuleIn) -> ModuleAdminOut:
    module.title = data.title
    db.flush()
    return ModuleAdminOut(
        id=module.id, route_id=module.route_id, title=module.title, position=module.position
    )


def _video_id(url: str) -> str:
    video_id = extract_video_id(url)
    if video_id is None:
        raise AppError(422, "La URL de YouTube no es válida.", code="invalid_youtube_url")
    return video_id


def _set_links(db: Session, lesson: Lesson, links: list[LessonLinkIn]) -> None:
    for link in list(db.scalars(select(LessonLink).where(LessonLink.lesson_id == lesson.id))):
        db.delete(link)
    db.flush()
    for position, link in enumerate(links):
        db.add(LessonLink(lesson_id=lesson.id, label=link.label, url=link.url, position=position))
    db.flush()


def _reload_lesson(db: Session, lesson_id: int) -> LessonAdminOut:
    db.expire_all()
    lesson = db.scalars(
        select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.links))
    ).one()
    return _lesson_out(lesson)


def create_lesson(db: Session, module: Module, data: LessonIn) -> LessonAdminOut:
    lesson = Lesson(
        module_id=module.id,
        title=data.title,
        youtube_url=data.youtube_url,
        youtube_video_id=_video_id(data.youtube_url),
        description=clean_markdown(data.description),
        duration_min=data.duration_min,
        is_published=data.is_published,
        position=_next_position(db, Lesson.position, Lesson.module_id == module.id),
    )
    db.add(lesson)
    db.flush()
    _set_links(db, lesson, data.links)
    return _reload_lesson(db, lesson.id)


def update_lesson(db: Session, lesson: Lesson, data: LessonUpdateIn) -> LessonAdminOut:
    values = data.model_dump(exclude_unset=True)
    links = values.pop("links", None)
    if values.get("youtube_url") is not None:
        lesson.youtube_video_id = _video_id(values["youtube_url"])
    if values.get("description") is not None:
        values["description"] = clean_markdown(values["description"])
    for field, value in values.items():
        if value is not None or field == "duration_min":
            setattr(lesson, field, value)
    db.flush()
    if links is not None:
        _set_links(db, lesson, data.links or [])
    return _reload_lesson(db, lesson.id)


def reorder(db: Session, model, parent_column, parent_id: int, ids: list[int]) -> None:
    """Rewrite positions 0..n-1; `ids` must be exactly the current siblings (no foreign/missing ids)."""
    siblings = {row.id: row for row in db.scalars(select(model).where(parent_column == parent_id))}
    if sorted(ids) != sorted(siblings) or len(set(ids)) != len(ids):
        raise AppError(422, "El orden debe incluir exactamente los elementos actuales.", code="invalid_order")
    for position, item_id in enumerate(ids):
        siblings[item_id].position = position
    db.flush()


# ── Enrollments ──────────────────────────────────────────────


def enrollees(db: Session, academy: Academy, cursor: str | None, limit: int) -> Page[EnrolleeOut]:
    stmt = select(Enrollment).where(Enrollment.academy_id == academy.id)
    page = paginate(db, stmt, [Enrollment.enrolled_at, Enrollment.user_id], cursor=cursor, limit=limit)
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([e.user_id for e in page.items])))}
    return Page[EnrolleeOut](
        items=[
            EnrolleeOut(
                user_id=e.user_id,
                full_name=users[e.user_id].full_name,
                nickname=users[e.user_id].nickname,
                email=users[e.user_id].email,
                boleta=users[e.user_id].boleta,
                enrolled_at=e.enrolled_at,
            )
            for e in page.items
        ],
        next_cursor=page.next_cursor,
    )


def enroll_by_boleta(db: Session, academy: Academy, boleta: str) -> EnrolleeOut:
    user = db.scalar(
        select(User).where(User.boleta == boleta.strip(), User.role == Role.member, User.is_active.is_(True))
    )
    if user is None:
        raise AppError(404, "No hay un miembro activo con esa boleta.")
    enrollment = db.get(Enrollment, (user.id, academy.id))
    if enrollment is None:
        enrollment = Enrollment(user_id=user.id, academy_id=academy.id)
        db.add(enrollment)
        db.flush()
        db.refresh(enrollment)
    return EnrolleeOut(
        user_id=user.id,
        full_name=user.full_name,
        nickname=user.nickname,
        email=user.email,
        boleta=user.boleta,
        enrolled_at=enrollment.enrolled_at,
    )


def unenroll(db: Session, academy: Academy, user_id: int) -> None:
    enrollment = db.get(Enrollment, (user_id, academy.id))
    if enrollment is not None:
        db.delete(enrollment)
        db.flush()
