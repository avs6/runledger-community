"""API key scopes: validation, the route → scope mapping, and enforcement in the API,
the gateway resolvers and the /mcp mount."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from runledger_api.core import deps
from runledger_api.core.scopes import (
    GATEWAY,
    INGEST,
    MCP,
    READ,
    WRITE,
    key_allows,
    normalize_scopes,
    required_scopes,
)
from runledger_api.schemas.auth import ApiKeyCreate, ApiKeyUpdate

# ── Validation ────────────────────────────────────────────────────────────────


def test_normalize_scopes_dedupes_and_orders() -> None:
    assert normalize_scopes(["MCP", "read", "read", " ingest "]) == ["read", "ingest", "mcp"]
    assert normalize_scopes([]) == []


def test_unknown_scope_rejected_on_create_and_update() -> None:
    with pytest.raises(ValidationError):
        ApiKeyCreate(scopes=["admin"])
    with pytest.raises(ValidationError):
        ApiKeyUpdate(scopes=["everything"])
    assert ApiKeyCreate(scopes=["gateway", "ingest"]).scopes == ["ingest", "gateway"]
    assert ApiKeyUpdate(scopes=[]).scopes == []  # [] = remove limits
    assert ApiKeyUpdate().scopes is None  # untouched


# ── Mapping ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path", "needed"),
    [
        ("POST", "/ingest/v1/batch", INGEST),
        ("POST", "/otlp/v1/traces", INGEST),
        ("POST", "/v1/logs", INGEST),
        ("GET", "/ingest/runs", INGEST | READ),
        ("POST", "/outcomes", INGEST | WRITE),
        ("POST", "/evaluations/scores", INGEST | WRITE),
        ("GET", "/runs/{run_id}", READ),
        ("GET", "/budgets/check", READ),
        ("POST", "/policies/check", READ),
        ("POST", "/prompts", WRITE),
        ("DELETE", "/agents/{agent_id}", WRITE),
        ("PUT", "/outcomes/{outcome_id}", WRITE),
        ("POST", "/auth/logout", None),
    ],
)
def test_required_scopes(method: str, path: str, needed: frozenset[str] | None) -> None:
    assert required_scopes(method, path) == needed


def test_key_allows() -> None:
    assert key_allows([], WRITE)  # unrestricted legacy key
    assert key_allows(None, GATEWAY)
    assert key_allows(["write"], READ)  # write implies read
    assert not key_allows(["read"], WRITE)
    assert not key_allows(["ingest"], READ)
    assert key_allows(["ingest"], INGEST | READ)
    assert not key_allows(["read", "ingest"], GATEWAY)
    assert not key_allows(["gateway"], MCP)


def test_sessions_and_oidc_are_not_scope_limited() -> None:
    deps.require_key_scope(None, WRITE)
    deps.require_key_scope(SimpleNamespace(is_session=True, scopes=["read"]), WRITE)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        deps.require_key_scope(SimpleNamespace(is_session=False, scopes=["read"]), WRITE)  # type: ignore[arg-type]
    assert exc.value.status_code == 403
    assert "write" in exc.value.detail


# ── Enforcement through real routes ───────────────────────────────────────────

WS = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4(), status="active", name="ws")


def _key(scopes: list[str]) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(), workspace_id=WS.id, is_session=False, scopes=scopes, user_id=None
    )


async def _call(scopes: list[str], method: str, path: str, **kw: Any) -> int:
    from runledger_api.core.db import get_db
    from runledger_api.main import app

    async def _db() -> Any:
        yield AsyncMock()

    app.dependency_overrides[get_db] = _db
    try:
        with (
            patch.object(deps, "verify_api_key", AsyncMock(return_value=_key(scopes))),
            patch.object(deps, "authorize_api_key", AsyncMock(return_value=(WS, None))),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                resp = await c.request(
                    method, path, headers={"Authorization": "Bearer rl_live_x"}, **kw
                )
        return resp.status_code
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_ingest_only_key_cannot_read_or_write() -> None:
    assert await _call(["ingest"], "GET", "/prompts") == 403
    assert await _call(["ingest"], "POST", "/prompts", json={"name": "p"}) == 403


@pytest.mark.asyncio
async def test_read_only_key_cannot_write_or_ingest() -> None:
    assert await _call(["read"], "POST", "/prompts", json={"name": "p"}) == 403
    assert await _call(["read"], "POST", "/ingest/v1/batch", json={"events": []}) == 403


@pytest.mark.asyncio
async def test_gateway_only_key_cannot_use_the_api() -> None:
    assert await _call(["gateway"], "GET", "/runs") == 403


@pytest.mark.asyncio
async def test_scoped_key_passes_the_scope_check_for_allowed_routes() -> None:
    # Not 403: the scope check passed (the handler may then fail on the mock DB).
    with patch("runledger_api.routers.ingest._queue_events", return_value=0):
        status = await _call(["ingest"], "POST", "/ingest/v1/batch", json={"events": []})
    assert status != 403


# ── Gateway resolvers ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gateway_needs_gateway_scope() -> None:
    from runledger_api.routers import gateway_shared

    with (
        patch.object(gateway_shared, "verify_api_key", AsyncMock(return_value=_key(["read"]))),
        pytest.raises(HTTPException) as exc,
    ):
        await gateway_shared._resolve_gateway_bearer_token("rl_live_x", AsyncMock(), GATEWAY)
    assert exc.value.status_code == 403

    with (
        patch.object(gateway_shared, "verify_api_key", AsyncMock(return_value=_key(["gateway"]))),
        patch.object(deps, "authorize_api_key", AsyncMock(return_value=(WS, None))),
    ):
        workspace, _, _ = await gateway_shared._resolve_gateway_bearer_token(
            "rl_live_x", AsyncMock(), GATEWAY
        )
    assert workspace is WS


# ── /mcp mount ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_mount_requires_mcp_scope() -> None:
    from runledger_api.core import mcp_guard

    inner = AsyncMock()
    guard = mcp_guard.McpScopeGuard(inner)
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"authorization", b"Bearer rl_live_readonly")],
    }
    mcp_guard._cache.clear()
    with patch.object(mcp_guard, "verify_api_key", AsyncMock(return_value=_key(["read"]))):
        await guard(scope, AsyncMock(), send)
    assert sent[0]["status"] == 403
    inner.assert_not_awaited()

    scope["headers"] = [(b"authorization", b"Bearer rl_live_mcp")]
    with patch.object(mcp_guard, "verify_api_key", AsyncMock(return_value=_key(["read", "mcp"]))):
        await guard(scope, AsyncMock(), send)
    inner.assert_awaited_once()
