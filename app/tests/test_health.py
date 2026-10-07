from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.errors import AppError, register_error_handlers
from app.main import app, create_app, mount_spa


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_database(client: TestClient) -> None:
    assert client.get("/api/ready").json() == {"status": "ready"}


def test_ready_reports_503_when_database_is_down(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    def broken_connect():
        raise RuntimeError("db down")

    monkeypatch.setattr("app.main.engine.connect", broken_connect)
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_ready"


def test_security_headers_and_request_id(client: TestClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "abc"})
    assert response.headers["X-Request-ID"] == "abc"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_media_is_served_with_restrictive_csp(client: TestClient) -> None:
    response = client.get("/media/does-not-exist.svg")
    assert response.status_code == 404
    assert "sandbox" in response.headers["Content-Security-Policy"]


def test_unknown_api_route_uses_uniform_error(client: TestClient) -> None:
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "No encontrado.", "details": None}}


class Payload(BaseModel):
    password: str
    age: int


@pytest.fixture
def errors_client() -> TestClient:
    probe = FastAPI()
    register_error_handlers(probe)

    @probe.post("/validate")
    def validate(payload: Payload) -> dict:
        return {}

    @probe.get("/app-error")
    def app_error() -> dict:
        raise AppError(409, details={"field": "email"})

    @probe.get("/custom")
    def custom() -> dict:
        raise AppError(418, "Soy una tetera", code="teapot")

    @probe.get("/boom")
    def boom() -> dict:
        raise RuntimeError("secret internals")

    @probe.get("/http-detail")
    def http_detail() -> dict:
        from fastapi import HTTPException

        raise HTTPException(403, "Solo superadmin.")

    return TestClient(probe, raise_server_exceptions=False)


def test_validation_error_never_echoes_input(errors_client: TestClient) -> None:
    response = errors_client.post("/validate", json={"password": "hunter2", "age": "x"})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert "hunter2" not in response.text
    assert body["details"][0]["loc"] == ["body", "age"]


def test_app_error_defaults_and_custom(errors_client: TestClient) -> None:
    conflict = errors_client.get("/app-error").json()["error"]
    assert conflict == {"code": "conflict", "message": "El recurso ya existe.", "details": {"field": "email"}}
    teapot = errors_client.get("/custom")
    assert teapot.status_code == 418
    assert teapot.json()["error"]["code"] == "teapot"


def test_unhandled_error_is_generic(errors_client: TestClient) -> None:
    response = errors_client.get("/boom")
    assert response.status_code == 500
    assert "secret internals" not in response.text
    assert response.json()["error"]["code"] == "internal_error"


def test_http_exception_detail_is_kept(errors_client: TestClient) -> None:
    response = errors_client.get("/http-detail")
    assert response.json()["error"] == {"code": "forbidden", "message": "Solo superadmin.", "details": None}


def test_rate_limit_error_format() -> None:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from starlette.requests import Request

    probe = create_app()
    limiter = Limiter(key_func=get_remote_address)
    probe.state.limiter = limiter

    @probe.post("/api/limited")
    @limiter.limit("1/minute")
    def limited(request: Request) -> dict:
        return {}

    client = TestClient(probe)
    assert client.post("/api/limited").status_code == 200
    response = client.post("/api/limited")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


def test_spa_fallback(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("nope")
    probe = FastAPI()
    mount_spa(probe, tmp_path)
    client = TestClient(probe)

    assert client.get("/").text == "<div id=root></div>"
    assert client.get("/a/upiixia/rutas").text == "<div id=root></div>"
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert "nope" not in client.get("/../secret.txt").text
    assert client.get("/api/missing").status_code == 404
    assert client.get("/api").status_code == 404


def test_settings_parse_cors_list_and_require_prod_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.mx, https://b.mx")
    assert Settings(_env_file=None).cors_origins == ["https://a.mx", "https://b.mx"]

    monkeypatch.setenv("ENV", "prod")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    assert Settings(_env_file=None).env == "prod"


def test_get_db_yields_a_working_session() -> None:
    from sqlalchemy import text

    from app.db import get_db

    sessions = get_db()
    session = next(sessions)
    assert session.execute(text("SELECT 1")).scalar() == 1
    sessions.close()


def test_postgres_engine_uses_a_pool() -> None:
    from app.db import make_engine

    engine = make_engine("postgresql+psycopg://user:pw@localhost:5432/db")
    assert engine.dialect.name == "postgresql"
    assert engine.pool.size() == 10


def test_routers_are_auto_discovered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib
    import sys

    package = tmp_path / "fake_routers"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "demo.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter(prefix='/api/demo')\n"
        "@router.get('')\n"
        "def demo():\n"
        "    return {'demo': True}\n"
    )
    (package / "helpers.py").write_text("VALUE = 1\n")  # no `router`: ignored
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr("app.main.routers", importlib.import_module("fake_routers"))
    try:
        probe = create_app()
        assert TestClient(probe).get("/api/demo").json() == {"demo": True}
    finally:
        for name in ("fake_routers", "fake_routers.demo", "fake_routers.helpers"):
            sys.modules.pop(name, None)
