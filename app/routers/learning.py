"""Learning routes, course player and progress (flow step 3)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearningRoute, User
from app.pagination import CursorParam, LimitParam, paginate
from app.schemas.common import Page
from app.schemas.learning import LessonOut, RouteCardOut, RouteDetailOut
from app.security import current_user
from app.services import academies, learning

router = APIRouter(prefix="/api", tags=["learning"])


@router.get("/academies/{slug}/routes", response_model=Page[RouteCardOut])
def list_routes(
    slug: str,
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Page[RouteCardOut]:
    academy = academies.get_academy(db, slug, user)
    page = paginate(
        db,
        learning.routes_stmt(academy, user),
        [LearningRoute.position, LearningRoute.id],
        cursor=cursor,
        limit=limit,
        descending=False,
    )
    return Page[RouteCardOut](items=learning.route_cards(db, user, page.items), next_cursor=page.next_cursor)


@router.get("/routes/{route_id}", response_model=RouteDetailOut)
def route_detail(
    route_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> RouteDetailOut:
    return learning.route_detail(db, route_id, user)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def lesson_detail(
    lesson_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> LessonOut:
    lesson = learning.lesson_detail(db, lesson_id, user)
    db.commit()  # persists last_viewed_at ("Continuar donde te quedaste")
    return lesson


@router.post("/lessons/{lesson_id}/complete", response_model=learning.CompletionOut)
def complete(
    lesson_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> learning.CompletionOut:
    result = learning.set_completed(db, lesson_id, user, completed=True)
    db.commit()
    return result


@router.delete("/lessons/{lesson_id}/complete", response_model=learning.CompletionOut)
def uncomplete(
    lesson_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> learning.CompletionOut:
    result = learning.set_completed(db, lesson_id, user, completed=False)
    db.commit()
    return result
