"""My account (IDEA §2.3). Every route acts on the caller only."""

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.ratelimit import LOGIN_LIMIT, limiter
from app.routers.auth import _set_refresh_cookie
from app.schemas.users import EmailChangeIn, PasswordChangeIn, ProfileUpdateIn, TokenOut, UserMe
from app.security import current_user
from app.services import account as service

router = APIRouter(prefix="/api/account", tags=["account"])


def _per_user(request: Request) -> str:
    return f"user:{getattr(request.state, 'user_id', None)}"


@router.patch("/profile", response_model=UserMe)
def update_profile(
    data: ProfileUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> UserMe:
    result = service.update_profile(db, user, data)
    db.commit()
    return result


@router.post("/avatar", response_model=UserMe)
async def upload_avatar(
    file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)
) -> UserMe:
    return await service.upload_avatar(db, user, file)  # commits itself (file cleanup on failure)


# Both require the current password: rate-limited per user so a stolen access token can't brute-force it.
@router.post("/email", response_model=UserMe)
@limiter.limit(LOGIN_LIMIT, key_func=_per_user)
def change_email(
    request: Request, data: EmailChangeIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> UserMe:
    result = service.change_email(db, user, data)
    db.commit()
    return result


@router.post("/password", response_model=TokenOut)
@limiter.limit(LOGIN_LIMIT, key_func=_per_user)
def change_password(
    request: Request,
    response: Response,
    data: PasswordChangeIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TokenOut:
    token, raw = service.change_password(db, user, data)
    db.commit()
    _set_refresh_cookie(response, raw)
    response.headers["Cache-Control"] = "no-store"
    return token
