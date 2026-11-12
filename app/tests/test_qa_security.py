"""QA security and uploads (UPS-058): docs/PRUEBAS-CAMPUS.md §14 (SEC-01…07), §9 (RES-02) and §10 (ACC-04).

Hostile uploads are generated in the test (HTML or an SVG with script behind a .png name, an .exe, an
oversized body), then the stored media is fetched back to check how it is served.
"""

import io
import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.main import app
from app.models import User

ROOT = Path(__file__).resolve().parents[2]
HTML_AS_PNG = b"<!doctype html><html><body><script>alert(document.cookie)</script></body></html>"
SVG_WITH_SCRIPT = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><script>alert(1)</script></svg>'
)
SVG_WITH_HANDLER = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)" width="10" height="10"/>'
SAFE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
)
EXE = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 120


def _png(size: tuple[int, int] = (64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def _served(client: TestClient, url: str):
    response = client.get(url)
    assert response.status_code == 200, url  # noqa: S101
    return response


def _assert_safe_media_headers(response) -> None:
    content_type = response.headers["content-type"]
    assert "html" not in content_type and content_type.startswith("image/"), content_type  # noqa: S101
    assert response.headers.get("x-content-type-options") == "nosniff"  # noqa: S101
    assert "sandbox" in response.headers.get("content-security-policy", "")  # noqa: S101


# ── SEC-01 · extra fields ────────────────────────────────────


def test_extra_json_fields_are_refused(client: TestClient, as_member: TestClient) -> None:
    register = client.post(
        "/api/auth/register",
        json={
            "full_name": "Ana López Pérez",
            "boleta": "2026123499",
            "email": "ana.extra@alumno.ipn.mx",
            "password": "segura-123",
            "accept_privacy": True,
            "role": "superadmin",
        },
        headers={"X-Requested-With": "fetch"},
    )
    assert register.status_code == 422
    assert (
        as_member.patch("/api/account/profile", json={"nickname": "yo", "role": "superadmin"}).status_code
        == 422
    )
    assert (
        as_member.patch("/api/account/profile", json={"nickname": "yo", "is_active": False}).status_code
        == 422
    )


# ── SEC-06 · password storage ────────────────────────────────


def test_passwords_are_stored_as_argon2id(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Bruno Hash Díaz",
            "boleta": "2026123498",
            "email": "bruno.hash@alumno.ipn.mx",
            "password": "segura-123",
            "accept_privacy": True,
        },
        headers={"X-Requested-With": "fetch"},
    )
    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == "bruno.hash@alumno.ipn.mx"))
    assert user.password_hash.startswith("$argon2id$") and "segura-123" not in user.password_hash
    assert "password_hash" not in response.text and "$argon2" not in response.text  # never echoed back


# ── SEC-07 · unexpected errors ───────────────────────────────


def test_unexpected_errors_return_uniform_json_without_a_stack_trace(
    db: Session, seeded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.db import get_db
    from app.models import Lesson
    from app.services import learning
    from app.tests.conftest import auth_headers

    def explode(*_args, **_kwargs):
        raise RuntimeError("secret detail: alumno.demo@upiixsol.dev")

    monkeypatch.setattr(learning, "thumbnail_url", explode)
    member = db.get(User, seeded["member_id"])
    lesson_id = db.scalar(select(Lesson.id).limit(1))
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app, raise_server_exceptions=False, headers=auth_headers(member)) as client:
            response = client.get(f"/api/lessons/{lesson_id}")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Ocurrió un error inesperado.", "details": None}
    }
    for leak in ("Traceback", "RuntimeError", "secret detail", "alumno.demo", 'File "'):
        assert leak not in response.text


# ── SEC-03 · fake-extension uploads ──────────────────────────


@pytest.mark.parametrize(
    ("payload", "name"),
    [(HTML_AS_PNG, "foto.png"), (SVG_WITH_SCRIPT, "foto.png"), (b"GIF89a" + HTML_AS_PNG, "foto.gif")],
)
def test_fake_image_uploads_are_rejected(as_member: TestClient, payload: bytes, name: str) -> None:
    response = as_member.post("/api/account/avatar", files={"file": (name, payload, "image/png")})
    assert response.status_code == 422, response.text
    assert response.json()["error"]["message"]  # a clear message, not a stack trace


@pytest.mark.parametrize("svg", [SVG_WITH_SCRIPT, SVG_WITH_HANDLER])
def test_svg_with_script_is_rejected_where_svg_is_allowed(
    as_admin_ia: TestClient, seeded: dict, svg: bytes
) -> None:
    response = as_admin_ia.post(
        f"/api/academies/{seeded['academy_id']}/logo", files={"file": ("logo.svg", svg, "image/svg+xml")}
    )
    assert response.status_code == 422, response.text


def test_stored_media_is_never_served_as_html(
    as_admin_ia: TestClient, as_member: TestClient, seeded: dict
) -> None:
    logo = as_admin_ia.post(
        f"/api/academies/{seeded['academy_id']}/logo", files={"file": ("logo.svg", SAFE_SVG, "text/html")}
    )
    assert logo.status_code == 200, logo.text
    svg_url = logo.json()["logo_url"]
    _assert_safe_media_headers(_served(as_member, svg_url))
    avatar = as_member.post("/api/account/avatar", files={"file": ("a.html", _png(), "text/html")})
    assert avatar.status_code == 200, avatar.text
    served = _served(as_member, avatar.json()["avatar_url"])
    _assert_safe_media_headers(served)
    assert served.headers["content-type"] == "image/webp"  # re-encoded whatever the declared type


# ── RES-02 · resource files ──────────────────────────────────


@pytest.mark.parametrize(
    ("payload", "name", "mime"),
    [(EXE, "setup.exe", "application/octet-stream"), (HTML_AS_PNG, "pagina.html", "text/html")],
)
def test_resource_rejects_executables_and_html(
    as_admin_ia: TestClient, seeded: dict, payload: bytes, name: str, mime: str
) -> None:
    response = as_admin_ia.post(
        f"/api/academies/{seeded['academy_id']}/resources",
        data={"type": "document", "title": "Archivo"},
        files={"file": (name, payload, mime)},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["message"]


def test_files_over_10_mb_are_rejected_with_a_clear_message(as_admin_ia: TestClient, seeded: dict) -> None:
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (10 * 1024 * 1024 + 1)
    response = as_admin_ia.post(
        f"/api/academies/{seeded['academy_id']}/resources",
        data={"type": "document", "title": "Enorme"},
        files={"file": ("enorme.png", big, "image/png")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["message"] == "El archivo es demasiado grande."


# ── ACC-04 · avatar ──────────────────────────────────────────


def test_avatar_rejects_non_images_and_oversized_files(as_member: TestClient) -> None:
    text = as_member.post(
        "/api/account/avatar", files={"file": ("cv.pdf", b"%PDF-1.7 hola", "application/pdf")}
    )
    assert text.status_code == 422 and text.json()["error"]["message"]
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (3 * 1024 * 1024)  # above the 2 MB avatar limit
    big = as_member.post("/api/account/avatar", files={"file": ("big.png", oversized, "image/png")})
    assert big.status_code in (413, 422) and big.json()["error"]["message"]


def test_avatar_is_re_encoded_and_resized(as_member: TestClient) -> None:
    response = as_member.post(
        "/api/account/avatar", files={"file": ("grande.png", _png((1200, 900)), "image/png")}
    )
    assert response.status_code == 200, response.text
    url = response.json()["avatar_url"]
    assert re.fullmatch(r"/media/avatar/[0-9a-f]{32}\.webp", url)  # random name, never the uploaded one
    image = Image.open(io.BytesIO(_served(as_member, url).content))
    assert image.format == "WEBP" and max(image.size) <= 256


# ── SEC-04 · CORS and cookies ────────────────────────────────


def test_cors_answers_only_the_configured_origins(client: TestClient) -> None:
    allowed = get_settings().cors_origins[0]
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    ok = client.options("/api/auth/login", headers={"Origin": allowed, **preflight})
    assert ok.headers.get("access-control-allow-origin") == allowed
    assert ok.headers.get("access-control-allow-credentials") == "true"
    for origin in ("https://evil.example", "null", f"{allowed}.evil.example"):
        denied = client.options("/api/auth/login", headers={"Origin": origin, **preflight})
        assert "access-control-allow-origin" not in denied.headers, origin
        assert (
            client.get("/api/site", headers={"Origin": origin}).headers.get("access-control-allow-origin")
            is None
        )


def test_refresh_cookie_is_httponly_secure_and_scoped(db: Session, seeded: dict) -> None:
    from app.db import get_db

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app, base_url="https://testserver", headers={"X-Requested-With": "fetch"}) as client:
            response = client.post(
                "/api/auth/login", json={"identifier": "alumno.demo@upiixsol.dev", "password": "admin123"}
            )
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 200, response.text
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "path=/api/auth" in cookie and "samesite" in cookie
    assert ("secure" in cookie) is get_settings().cookie_secure
    assert get_settings().cookie_secure  # the default; .env.example also says COOKIE_SECURE=true
    assert "refresh" not in response.json()  # the refresh token never travels in the body


# ── SEC-05 · secrets ─────────────────────────────────────────


def test_repository_has_no_secrets() -> None:
    result = subprocess.run(  # noqa: S603
        ["bash", str(ROOT / ".uak" / "bin" / "secret-scan")],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        result.stdout[-500:] + result.stderr[-500:]
    )  # the scanner never prints values


def test_env_example_holds_no_real_values() -> None:
    values = dict(
        line.split("=", 1)
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    for key in ("JWT_SECRET", "SEED_DEFAULT_PASSWORD"):
        assert values.get(key, "").strip() == "", f"{key} must be empty in .env.example"
    secretish = [
        k for k, v in values.items() if re.search(r"SECRET|PASSWORD|TOKEN|KEY", k) and len(v.strip()) >= 16
    ]
    assert secretish == []
