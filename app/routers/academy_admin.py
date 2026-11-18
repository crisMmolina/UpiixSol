"""Academy panel endpoints (flow step 5). Scope: own academy for academy_admin, any for superadmin."""

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearningRoute, Lesson, Module, User
from app.pagination import CursorParam, LimitParam
from app.ratelimit import POST_LIMIT, limiter
from app.schemas.academies import AcademyOut, BrandingUpdateIn
from app.schemas.common import Page, ReorderIn
from app.schemas.learning import LessonIn, LessonUpdateIn, ModuleIn, RouteIn, RouteUpdateIn
from app.security import current_user
from app.services import academy_admin as service

router = APIRouter(prefix="/api", tags=["academy-admin"])

NO_CONTENT = Response(status_code=status.HTTP_204_NO_CONTENT)
ENROLL_LIMIT = "20/minute"


# ── Identity ─────────────────────────────────────────────────


@router.patch("/academies/{academy_id}/branding", response_model=AcademyOut)
def update_branding(
    academy_id: int, data: BrandingUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> AcademyOut:
    result = service.update_branding(db, service.academy_for(db, academy_id, user), data)
    db.commit()
    return result


def _per_user(request: Request) -> str:
    return f"user:{getattr(request.state, 'user_id', None)}"


async def _upload(
    academy_id: int,
    kind: str,
    file: UploadFile,
    user: User,
    db: Session,
    response: Response,
    transparent_background: bool,
) -> AcademyOut:
    academy = service.academy_for(db, academy_id, user)  # scope check before reading the upload
    return await service.upload_image(  # commits itself (file cleanup on failure)
        db, academy, file, kind, transparent_background=transparent_background, response=response
    )


@router.post("/academies/{academy_id}/logo", response_model=AcademyOut)
@limiter.limit(POST_LIMIT, key_func=_per_user)  # each upload decodes and re-encodes an image
async def upload_logo(
    request: Request,
    academy_id: int,
    response: Response,
    file: UploadFile = File(...),
    transparent_background: bool = Form(False),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AcademyOut:
    return await _upload(academy_id, "logo", file, user, db, response, transparent_background)


@router.post("/academies/{academy_id}/mascot", response_model=AcademyOut)
@limiter.limit(POST_LIMIT, key_func=_per_user)  # each upload decodes and re-encodes an image
async def upload_mascot(
    request: Request,
    academy_id: int,
    response: Response,
    file: UploadFile = File(...),
    transparent_background: bool = Form(False),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AcademyOut:
    return await _upload(academy_id, "mascot", file, user, db, response, transparent_background)


# ── Content ──────────────────────────────────────────────────


@router.get("/academies/{academy_id}/content", response_model=service.ContentOut)
def content(
    academy_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> service.ContentOut:
    return service.content_tree(db, service.academy_for(db, academy_id, user))


@router.post("/academies/{academy_id}/routes", response_model=service.RouteAdminOut, status_code=201)
def create_route(
    academy_id: int, data: RouteIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> service.RouteAdminOut:
    result = service.create_route(db, service.academy_for(db, academy_id, user), data)
    db.commit()
    return result


@router.put("/academies/{academy_id}/routes/order", status_code=200)
def order_routes(
    academy_id: int, data: ReorderIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    academy = service.academy_for(db, academy_id, user)
    service.reorder(db, LearningRoute, LearningRoute.academy_id, academy.id, data.ids)
    db.commit()
    return {"ids": data.ids}


@router.patch("/routes/{route_id}", response_model=service.RouteAdminOut)
def update_route(
    route_id: int, data: RouteUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> service.RouteAdminOut:
    result = service.update_route(db, service.route_for(db, route_id, user), data)
    db.commit()
    return result


@router.delete("/routes/{route_id}", status_code=204)
def delete_route(
    route_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    db.delete(service.route_for(db, route_id, user))
    db.commit()
    return NO_CONTENT


@router.post(
    "/academies/{academy_id}/routes/{route_id}/modules",
    response_model=service.ModuleAdminOut,
    status_code=201,
)
def create_module(
    academy_id: int,
    route_id: int,
    data: ModuleIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> service.ModuleAdminOut:
    academy = service.academy_for(db, academy_id, user)
    route = service.route_for(db, route_id, user)
    if route.academy_id != academy.id:
        raise service._not_found()
    result = service.create_module(db, route, data)
    db.commit()
    return result


@router.put("/routes/{route_id}/modules/order", status_code=200)
def order_modules(
    route_id: int, data: ReorderIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    route = service.route_for(db, route_id, user)
    service.reorder(db, Module, Module.route_id, route.id, data.ids)
    db.commit()
    return {"ids": data.ids}


@router.patch("/modules/{module_id}", response_model=service.ModuleAdminOut)
def update_module(
    module_id: int, data: ModuleIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> service.ModuleAdminOut:
    module, _route = service.module_for(db, module_id, user)
    result = service.update_module(db, module, data)
    db.commit()
    return result


@router.delete("/modules/{module_id}", status_code=204)
def delete_module(
    module_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    module, _route = service.module_for(db, module_id, user)
    db.delete(module)
    db.commit()
    return NO_CONTENT


@router.post("/modules/{module_id}/lessons", response_model=service.LessonAdminOut, status_code=201)
def create_lesson(
    module_id: int, data: LessonIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> service.LessonAdminOut:
    module, _route = service.module_for(db, module_id, user)
    result = service.create_lesson(db, module, data)
    db.commit()
    return result


@router.put("/modules/{module_id}/lessons/order", status_code=200)
def order_lessons(
    module_id: int, data: ReorderIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    module, _route = service.module_for(db, module_id, user)
    service.reorder(db, Lesson, Lesson.module_id, module.id, data.ids)
    db.commit()
    return {"ids": data.ids}


@router.patch("/lessons/{lesson_id}", response_model=service.LessonAdminOut)
def update_lesson(
    lesson_id: int, data: LessonUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> service.LessonAdminOut:
    result = service.update_lesson(db, service.lesson_for(db, lesson_id, user), data)
    db.commit()
    return result


@router.delete("/lessons/{lesson_id}", status_code=204)
def delete_lesson(
    lesson_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    db.delete(service.lesson_for(db, lesson_id, user))
    db.commit()
    return NO_CONTENT


# ── Enrollments ──────────────────────────────────────────────


@router.get("/academies/{academy_id}/enrollments", response_model=Page[service.EnrolleeOut])
def list_enrollments(
    academy_id: int,
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Page[service.EnrolleeOut]:
    return service.enrollees(db, service.academy_for(db, academy_id, user), cursor, limit)


@router.post("/academies/{academy_id}/enrollments", response_model=service.EnrolleeOut, status_code=201)
@limiter.limit(ENROLL_LIMIT, key_func=_per_user)  # blocks boleta enumeration
def enroll_member(
    request: Request,
    academy_id: int,
    data: service.EnrollIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> service.EnrolleeOut:
    result = service.enroll_by_boleta(db, service.academy_for(db, academy_id, user), data.boleta)
    db.commit()
    return result


@router.delete("/academies/{academy_id}/enrollments/{user_id}", status_code=204)
def unenroll_member(
    academy_id: int, user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    service.unenroll(db, service.academy_for(db, academy_id, user), user_id)
    db.commit()
    return NO_CONTENT
