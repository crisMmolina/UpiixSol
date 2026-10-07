"""Request body size cap at the app edge (security review UPS-011).

FastAPI parses a whole multipart form (spooling files to disk) before any endpoint code runs, so
per-upload limits in services/media.py come too late to stop a multi-GB body. This ASGI middleware
rejects an oversized declared Content-Length immediately and aborts streamed bodies that exceed the
cap. nginx should enforce the same limit in production (`client_max_body_size`, UPS-015).
"""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import error_response

MAX_BODY_BYTES = 6 * 1024 * 1024  # largest upload (5 MB post image) + form overhead


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    # Stops the endpoint from reading further (FastAPI turns it into an error response,
                    # which limited_send below replaces with the uniform 413).
                    raise HTTPException(413, "El archivo es demasiado grande.")
            return message

        replaced = False

        async def limited_send(message: Message) -> None:
            nonlocal replaced
            if exceeded:
                if not replaced:
                    replaced = True
                    await self._reject(scope, receive, send)
                return
            await send(message)

        await self.app(scope, limited_receive, limited_send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = error_response(413, "payload_too_large", "El archivo es demasiado grande.")
        await response(scope, receive, send)
