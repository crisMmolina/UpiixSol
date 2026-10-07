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


def test_settings_parse_cors_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.mx, https://b.mx")
    assert Settings(_env_file=None).cors_origins == ["https://a.mx", "https://b.mx"]


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
        ({"JWT_SECRET": "short"}, "32 chars"),
        ({"ENV": "prod", "SEED_DEFAULT_PASSWORD": "a-long-seed-password"}, "JWT_SECRET is required"),
        ({"ENV": "prod", "JWT_SECRET": "x" * 40}, "SEED_DEFAULT_PASSWORD"),
        ({"ENV": "prod", "JWT_SECRET": "x" * 40, "SEED_DEFAULT_PASSWORD": "admin123"}, "SEED_DEFAULT"),
        ({"ENV": "prod", "JWT_SECRET": "x" * 40, "SEED_DEFAULT_PASSWORD": "short"}, "SEED_DEFAULT"),
    ],
)
def test_settings_reject_unsafe_values(monkeypatch: pytest.MonkeyPatch, env: dict, message: str) -> None:
    for name in ("ENV", "JWT_SECRET", "SEED_DEFAULT_PASSWORD", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError, match=message):
        Settings(_env_file=None)


def test_empty_env_values_fall_back_to_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "")
    assert len(Settings(_env_file=None).jwt_secret) >= 32


def test_prod_settings_with_strong_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("SEED_DEFAULT_PASSWORD", "a-long-seed-password")
    settings = Settings(_env_file=None)
    assert settings.env == "prod"
    assert settings.docs_enabled is False


def test_docs_are_hidden_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    prod = Settings.model_construct(env="prod", cors_origins=[], media_dir="media")
    monkeypatch.setattr("app.main.get_settings", lambda: prod)
    probe = TestClient(create_app())
    assert probe.get("/api/docs").status_code == 404
    assert probe.get("/api/openapi.json").status_code == 404
    assert TestClient(app).get("/api/openapi.json").status_code == 200


def test_bad_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "x" * 65})
    assert response.headers["X-Request-ID"] != "x" * 65
    assert len(response.headers["X-Request-ID"]) == 32


def test_500_keeps_headers_and_does_not_log_pii(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("app.main.WEB_DIST", tmp_path / "no-dist")  # keep the SPA catch-all out
    probe = create_app()

    @probe.get("/api/boom")
    def boom() -> dict:
        raise RuntimeError("Key (email)=(alumno@ipn.mx) already exists")

    with caplog.at_level("INFO"):
        response = TestClient(probe, raise_server_exceptions=False).get("/api/boom")
    assert response.status_code == 500
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Request-ID" in response.headers
    assert "alumno@ipn.mx" not in caplog.text
    assert "RuntimeError" in caplog.text


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
