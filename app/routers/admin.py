"""Superadmin endpoints (flow step 6). Every route requires the superadmin role."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Academy, Role, User
from app.pagination import CursorParam, LimitParam, paginate
from app.schemas.academies import AcademyCreateIn, AcademyOut, AcademyUpdateIn, HomeContentIn, HomeContentOut
from app.schemas.common import Page
from app.schemas.users import AdminUserCreateIn, AdminUserUpdateIn, PasswordResetOut, UserAdminOut
from app.security import require_role
from app.services import admin as service

router = APIRouter(prefix="/api/admin", tags=["admin"])
Superadmin = Annotated[User, Depends(require_role(Role.superadmin))]


@router.get("/academies", response_model=Page[AcademyOut])
def list_academies(
    _user: Superadmin, cursor: CursorParam = None, limit: LimitParam = 20, db: Session = Depends(get_db)
) -> Page[AcademyOut]:
    return paginate(
        db,
        service.academies_stmt(),
        [Academy.position, Academy.id],
        cursor=cursor,
        limit=limit,
        descending=False,
        transform=AcademyOut.model_validate,
    )


@router.post("/academies", response_model=AcademyOut, status_code=201)
def create_academy(data: AcademyCreateIn, _user: Superadmin, db: Session = Depends(get_db)) -> AcademyOut:
    result = service.create_academy(db, data)
    db.commit()
    return result


@router.patch("/academies/{academy_id}", response_model=AcademyOut)
def update_academy(
    academy_id: int, data: AcademyUpdateIn, _user: Superadmin, db: Session = Depends(get_db)
) -> AcademyOut:
    result = service.update_academy(db, academy_id, data)
    db.commit()
    return result


@router.get("/users", response_model=Page[UserAdminOut])
def list_users(
    _user: Superadmin,
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    role: Role | None = None,
    academy_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    db: Session = Depends(get_db),
) -> Page[UserAdminOut]:
    return paginate(
        db,
        service.users_stmt(role, academy_id, q),
        [User.id],
        cursor=cursor,
        limit=limit,
        descending=False,
        transform=UserAdminOut.model_validate,
    )


@router.post("/users", response_model=UserAdminOut, status_code=201)
def create_user(data: AdminUserCreateIn, _user: Superadmin, db: Session = Depends(get_db)) -> UserAdminOut:
    result = service.create_user(db, data)
    db.commit()
    return result


@router.patch("/users/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: int, data: AdminUserUpdateIn, actor: Superadmin, db: Session = Depends(get_db)
) -> UserAdminOut:
    result = service.update_user(db, actor, user_id, data)
    db.commit()
    return result


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetOut)
def reset_password(user_id: int, _user: Superadmin, db: Session = Depends(get_db)) -> PasswordResetOut:
    result = service.reset_password(db, user_id)
    db.commit()
    return result


@router.get("/home", response_model=HomeContentOut)
def get_home(_user: Superadmin, db: Session = Depends(get_db)) -> HomeContentOut:
    result = service.get_home(db)
    db.commit()
    return result


@router.put("/home", response_model=HomeContentOut)
def put_home(data: HomeContentIn, _user: Superadmin, db: Session = Depends(get_db)) -> HomeContentOut:
    result = service.put_home(db, data)
    db.commit()
    return result
