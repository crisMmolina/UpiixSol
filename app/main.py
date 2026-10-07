"""App entry. Auto-discovers `app/routers/*`; nobody edits this file after setup (OWNERS: UPS-001)."""

import importlib
import json
import logging
import pkgutil
import re
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app import routers
from app.body_limit import BodySizeLimitMiddleware
from app.config import get_settings
from app.db import engine
from app.errors import AppError, error_response, internal_error, log_unhandled, register_error_handlers
from app.ratelimit import limiter

ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = ROOT / "web" / "dist"

logging.basicConfig(level=logging.INFO, format="%(message)s")
access_log = logging.getLogger("app.access")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
# Uploaded files (including SVG) can never run scripts.
MEDIA_CSP = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"
REQUEST_ID = re.compile(r"[A-Za-z0-9-]{1,64}")


def create_app() -> FastAPI:
    settings = get_settings()
    docs = settings.docs_enabled
    app = FastAPI(
        title="UpiixSol Campus API",
        version="0.1.0",
        redoc_url=None,
        docs_url="/api/docs" if docs else None,
        openapi_url="/api/openapi.json" if docs else None,
    )
    app.state.limiter = limiter
    register_error_handlers(app)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # 500s still get request id, security headers and an access log
            log_unhandled(request, exc)
            response = internal_error()
        response.headers["X-Request-ID"] = request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/media/"):
            response.headers["Content-Security-Policy"] = MEDIA_CSP
        # Structured log with no PII: user id only (set by auth dependencies), never email/boleta.
        access_log.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                    "user_id": getattr(request.state, "user_id", None),
                }
            )
        )
        return response

    @app.get("/api/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/ready", tags=["ops"])
    def ready() -> dict[str, str]:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            raise AppError(503, "Base de datos no disponible.", code="not_ready") from exc
        return {"status": "ready"}

    include_routers(app)

    media_dir = Path(settings.media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_dir), name="media")

    if WEB_DIST.is_dir():  # pragma: no cover - exercised by smoke/e2e with a real build
        mount_spa(app, WEB_DIST)
    return app


def include_routers(app: FastAPI) -> None:
    # `routers` (not `app.routers`): the `app` variable shadows the package of the same name.
    for module in pkgutil.iter_modules(routers.__path__):
        router = getattr(importlib.import_module(f"{routers.__name__}.{module.name}"), "router", None)
        if router is not None:
            app.include_router(router)


def mount_spa(app: FastAPI, dist: Path) -> None:
    """Serve the built frontend; unknown non-API paths fall back to index.html (client routing)."""
    dist = dist.resolve()
    index = dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Response:
        if path == "api" or path.startswith(("api/", "media/")):
            return error_response(404, "not_found", "No encontrado.")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
