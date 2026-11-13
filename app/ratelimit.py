"""Shared slowapi limiter (in-memory, one process in v1; see ADR 0001).

Usage in a router:
    from app.ratelimit import limiter
    @router.post("/login")
    @limiter.limit("5/minute")
    def login(request: Request, ...): ...
"""

from limits import parse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings
from app.errors import AppError

LOGIN_LIMIT = "5/minute"
POST_LIMIT = "10/minute"


def build_limiter(enabled: bool) -> Limiter:
    """A per-IP limiter switched by the app setting. slowapi also reads RATELIMIT_ENABLED itself and, when
    the default it gets is False, skips the bool cast: the text "false" (truthy) overrides `enabled`. So
    the setting already parsed by pydantic is applied again after construction."""
    built = Limiter(key_func=get_remote_address, enabled=enabled)
    built.enabled = enabled
    return built


limiter = build_limiter(get_settings().ratelimit_enabled)
_LOGIN_PER_EMAIL = parse(LOGIN_LIMIT)


def hit_login_email(email: str) -> None:
    """Login attempts per account, besides per IP: guessing one password from many IPs is also limited
    (UPS-020). The key is the normalized email, so case and spaces do not open new buckets."""
    if limiter.enabled and not limiter.limiter.hit(_LOGIN_PER_EMAIL, "login-email", email.strip().lower()):
        raise AppError(429, code="rate_limited")
