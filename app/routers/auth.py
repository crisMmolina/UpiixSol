"""Single login for the 3 roles + member self-registration (IDEA §2.2, flow step 1)."""

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError, error_response
from app.models import User
from app.ratelimit import LOGIN_LIMIT, hit_login_email, limiter
from app.schemas.users import LoginIn, RegisterIn, TokenOut, UserMe
from app.security import current_user
from app.services import auth as service

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "upx_refresh"
COOKIE_PATH = "/api/auth"  # the refresh cookie is only ever sent to these endpoints


def require_fetch_header(x_requested_with: str | None = Header(default=None)) -> None:
    """CSRF guard for cookie-authenticated endpoints: HTML forms and simple cross-site requests cannot
    set custom headers, and a cross-origin fetch with one needs a CORS preflight our CORS denies."""
    if x_requested_with != "fetch":
        raise AppError(403, "Solicitud no permitida.", code="csrf")


def _set_refresh_cookie(response: Response, raw: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.jwt_refresh_days * 24 * 3600,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE, path=COOKIE_PATH, httponly=True, secure=settings.cookie_secure, samesite="lax"
    )


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_fetch_header)],
)
@limiter.limit(LOGIN_LIMIT)
def register(
    request: Request, response: Response, data: RegisterIn, db: Session = Depends(get_db)
) -> TokenOut:
    user = service.register_member(db, data)
    token, raw = service.issue_session(db, user)
    db.commit()
    _set_refresh_cookie(response, raw)
    return token


@router.post("/login", response_model=TokenOut, dependencies=[Depends(require_fetch_header)])
@limiter.limit(LOGIN_LIMIT)
def login(request: Request, response: Response, data: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    hit_login_email(data.email)  # per account too, not only per IP
    user = service.authenticate(db, data)
    token, raw = service.issue_session(db, user)
    db.commit()
    _set_refresh_cookie(response, raw)
    return token


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(require_fetch_header)])
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    upx_refresh: str | None = Cookie(default=None),
) -> TokenOut | Response:
    try:
        token, raw = service.rotate_refresh(db, upx_refresh)
    except AppError as error:
        failed = error_response(error.status, error.code, "Tu sesión expiró. Inicia sesión de nuevo.")
        # The failed token must not stick around in the browser, unless another tab just rotated it:
        # clearing the cookie then would delete the one that tab received.
        if error.code != "refresh_race":
            _clear_refresh_cookie(failed)
        return failed
    db.commit()
    _set_refresh_cookie(response, raw)
    return token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_fetch_header)])
def logout(db: Session = Depends(get_db), upx_refresh: str | None = Cookie(default=None)) -> Response:
    service.logout(db, upx_refresh)
    db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> UserMe:
    return service.user_me(db, user)
