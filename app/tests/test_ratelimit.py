"""RATELIMIT_ENABLED switches every limit, whatever slowapi reads from the environment itself (UPS-039)."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import ratelimit
from app.errors import AppError
from app.ratelimit import LOGIN_LIMIT, build_limiter, hit_login_email

ATTEMPTS = int(LOGIN_LIMIT.split("/")[0])


def _per_ip_app(enabled: bool) -> TestClient:
    limiter = build_limiter(enabled)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.post("/login")
    @limiter.limit(LOGIN_LIMIT)
    def login(request: Request) -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


@pytest.mark.parametrize(("value", "enabled"), [("false", False), ("true", True)])
def test_env_value_sets_the_limiter(monkeypatch: MonkeyPatch, value: str, enabled: bool) -> None:
    monkeypatch.setenv("RATELIMIT_ENABLED", value)
    assert build_limiter(enabled).enabled is enabled


@pytest.mark.parametrize(("value", "enabled"), [("false", False), ("true", True)])
def test_per_ip_decorator_follows_the_flag(monkeypatch: MonkeyPatch, value: str, enabled: bool) -> None:
    monkeypatch.setenv("RATELIMIT_ENABLED", value)
    client = _per_ip_app(enabled)
    codes = [client.post("/login").status_code for _ in range(ATTEMPTS + 1)]
    assert codes[:ATTEMPTS] == [200] * ATTEMPTS
    assert codes[-1] == (429 if enabled else 200)


@pytest.mark.parametrize(("value", "enabled"), [("false", False), ("true", True)])
def test_login_email_limit_follows_the_flag(monkeypatch: MonkeyPatch, value: str, enabled: bool) -> None:
    monkeypatch.setenv("RATELIMIT_ENABLED", value)
    monkeypatch.setattr(ratelimit, "limiter", build_limiter(enabled))
    for _ in range(ATTEMPTS):
        hit_login_email(" Ana@Alumno.ipn.mx ")
    if enabled:
        with pytest.raises(AppError) as exc:
            hit_login_email("ana@alumno.ipn.mx")
        assert exc.value.status == 429
    else:
        hit_login_email("ana@alumno.ipn.mx")
