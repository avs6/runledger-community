"""ASGI guard for the ``/mcp`` mount: workload keys need the ``mcp`` scope.

The MCP tools forward the caller's key to ordinary API routes, so each tool's data
access is still checked per route (``read`` for queries, ``ingest`` for recording).
This guard only decides whether a key may use the MCP endpoint at all.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from starlette.responses import JSONResponse

from runledger_api.core.db import AsyncSessionLocal
from runledger_api.core.scopes import MCP, key_allows
from runledger_api.services.auth import verify_api_key

_CACHE_TTL = 30.0
_cache: dict[str, tuple[float, bool]] = {}


async def _allowed(token: str) -> bool:
    digest = hashlib.sha256(token.encode()).hexdigest()
    cached = _cache.get(digest)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    async with AsyncSessionLocal() as db:
        key = await verify_api_key(token, db)
    # Unknown/revoked tokens pass here; every tool call they make is then rejected by
    # the API itself. Session keys are governed by roles, not scopes.
    allowed = key is None or key.is_session or key_allows(key.scopes, MCP)
    _cache[digest] = (time.monotonic() + _CACHE_TTL, allowed)
    return allowed


class McpScopeGuard:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode("latin-1")
            if auth.lower().startswith("bearer ") and not await _allowed(auth[7:].strip()):
                response = JSONResponse(
                    {"detail": "API key scope does not allow this request (needs: mcp)"},
                    status_code=403,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class McpPathNormalizer:
    """Serve ``/mcp`` and ``/mcp/`` alike.

    The MCP app is mounted at ``/mcp``, so a bare ``POST /mcp`` would get a 307 to
    ``/mcp/`` — and some MCP clients do not follow redirects for POST.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http" and scope.get("path") == "/mcp":
            scope = {**scope, "path": "/mcp/", "raw_path": b"/mcp/"}
        await self.app(scope, receive, send)
