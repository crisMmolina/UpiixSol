"""Campus home + academy pages (flow step 2)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Academy, User
from app.pagination import CursorParam, LimitParam, paginate
from app.schemas.academies import AcademyCardOut, AcademyOut
from app.schemas.common import Page
from app.security import current_user, optional_user
from app.services import academies as service

router = APIRouter(prefix="/api", tags=["academies"])


@router.get("/home", response_model=service.HomeOut)
def campus_home(user: User = Depends(current_user), db: Session = Depends(get_db)) -> service.HomeOut:
    return service.campus_home(db, user)


@router.get("/academies", response_model=Page[AcademyCardOut])
def list_academies(
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Page[AcademyCardOut]:
    enrolled = service.enrolled_ids(db, user)
    return paginate(
        db,
        service.active_academies_stmt(),
        [Academy.position, Academy.id],
        cursor=cursor,
        limit=limit,
        descending=False,
        transform=lambda academy: service.card(academy, enrolled),
    )


@router.get("/academies/{slug}", response_model=AcademyOut)
def get_academy(
    slug: str, user: User | None = Depends(optional_user), db: Session = Depends(get_db)
) -> AcademyOut:
    """Public branding (no personal data): the web re-themes before the session is restored."""
    academy = service.get_academy(db, slug, user)
    return service.academy_out(academy, service.enrolled_ids(db, user))


@router.get("/academies/{slug}/home", response_model=service.AcademyHomeOut)
def academy_home(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return service.academy_home(db, service.get_academy(db, slug, user), user)


@router.post("/academies/{slug}/enroll", response_model=service.EnrollOut)
def enroll(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> service.EnrollOut:
    result = service.set_enrollment(db, service.get_academy(db, slug, user), user, enrolled=True)
    db.commit()
    return result


@router.delete("/academies/{slug}/enroll", response_model=service.EnrollOut)
def unenroll(
    slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> service.EnrollOut:
    result = service.set_enrollment(db, service.get_academy(db, slug, user), user, enrolled=False)
    db.commit()
    return result
