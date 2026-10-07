"""Shared slowapi limiter (in-memory, one process in v1; see ADR 0001).

Usage in a router:
    from app.ratelimit import limiter
    @router.post("/login")
    @limiter.limit("5/minute")
    def login(request: Request, ...): ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

LOGIN_LIMIT = "5/minute"
POST_LIMIT = "10/minute"

limiter = Limiter(key_func=get_remote_address, enabled=get_settings().ratelimit_enabled)
