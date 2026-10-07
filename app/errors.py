"""Uniform JSON errors: {"error": {"code", "message", "details"}}. Messages are user-facing (es-MX)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")

_DEFAULT_CODES = {
    400: ("bad_request", "Solicitud inválida."),
    401: ("unauthorized", "Necesitas iniciar sesión."),
    403: ("forbidden", "No tienes permiso para hacer esto."),
    404: ("not_found", "No encontrado."),
    405: ("method_not_allowed", "Método no permitido."),
    409: ("conflict", "El recurso ya existe."),
    413: ("payload_too_large", "El archivo es demasiado grande."),
    422: ("validation_error", "Revisa los datos enviados."),
    429: ("rate_limited", "Demasiados intentos. Espera un momento."),
}


class AppError(Exception):
    """Raise from services/routers for an expected, user-facing error."""

    def __init__(self, status: int, message: str | None = None, code: str | None = None,
                 details: Any = None) -> None:
        default_code, default_message = _DEFAULT_CODES.get(status, ("error", "Ocurrió un error."))
        self.status = status
        self.code = code or default_code
        self.message = message or default_message
        self.details = details
        super().__init__(self.message)


def error_response(status: int, code: str, message: str, details: Any = None,
                   headers: dict[str, str] | None = None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": jsonable_encoder(details)}}
    return JSONResponse(body, status_code=status, headers=headers)


async def _app_error(_: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status, exc.code, exc.message, exc.details)


async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _DEFAULT_CODES.get(exc.status_code, ("error", "Ocurrió un error."))
    if isinstance(exc.detail, str) and exc.detail and exc.status_code not in (404, 405):
        message = exc.detail
    return error_response(exc.status_code, code, message, headers=getattr(exc, "headers", None))


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Never echo the submitted input back (it may hold passwords).
    details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    code, message = _DEFAULT_CODES[422]
    return error_response(422, code, message, details)


async def _rate_limited(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    code, message = _DEFAULT_CODES[429]
    return error_response(429, code, message, {"limit": str(exc.detail)})


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "internal_error", "Ocurrió un error inesperado.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(RateLimitExceeded, _rate_limited)
    app.add_exception_handler(Exception, _unhandled)
