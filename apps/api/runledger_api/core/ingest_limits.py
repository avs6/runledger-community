"""Request-size guard for ingest and OTLP routes (I-14).

Rejects bodies whose declared Content-Length exceeds ``INGEST_MAX_BODY_BYTES``
with 413 before they are read. OTLP handlers additionally cap the size of
gzip-inflated bodies (``OTLP_MAX_DECOMPRESSED_BYTES``).
"""

from __future__ import annotations

from typing import Any

from starlette.responses import JSONResponse

from runledger_api.core.config import settings

_GUARDED_PREFIXES = ("/ingest/", "/otlp/", "/v1/traces", "/v1/metrics", "/v1/logs")


class IngestBodyLimitMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http" and str(scope.get("path", "")).startswith(_GUARDED_PREFIXES):
            for name, value in scope.get("headers") or []:
                if name == b"content-length":
                    try:
                        size = int(value)
                    except ValueError:
                        size = 0
                    if size > settings.ingest_max_body_bytes:
                        response = JSONResponse(
                            {
                                "detail": (
                                    f"Payload too large (max {settings.ingest_max_body_bytes} bytes)"
                                )
                            },
                            status_code=413,
                        )
                        await response(scope, receive, send)
                        return
                    break
        await self.app(scope, receive, send)
