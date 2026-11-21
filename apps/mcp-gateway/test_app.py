"""Access-control tests for the MCP gateway.

Run with:  uv run --project apps/api pytest apps/mcp-gateway/test_app.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))


def _load(require_auth: str = "true") -> Any:
    with patch.dict("os.environ", {"MCP_REQUIRE_AUTH": require_auth}):
        import app  # noqa: PLC0415

        return importlib.reload(app)


def _ctx(token: str | None) -> Any:
    headers = {"authorization": f"Bearer {token}"} if token else {}
    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(headers=headers))
    )


class _Resp:
    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status_code = status
        self._body = body

    def json(self) -> dict[str, Any]:
        return self._body


def _client(resp: _Resp) -> Any:
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    cm = AsyncMock()
    cm.__aenter__.return_value = client
    return cm


def test_namespace_is_always_inside_the_callers_workspace() -> None:
    app = _load()
    assert app._namespace("ws-1", None) == "ws-1"
    assert app._namespace("ws-1", "ws-1") == "ws-1"
    # A caller naming another tenant's workspace only gets a sub-namespace of its own.
    assert app._namespace("ws-1", "ws-2") == "ws-1:ws-2"


@pytest.mark.asyncio
async def test_tool_without_api_key_is_refused() -> None:
    app = _load()
    result = await app.memory_recall(query="q", workspace="victim", ctx=_ctx(None))
    assert result["status"] == 401


@pytest.mark.asyncio
async def test_invalid_key_is_refused_and_backend_not_called() -> None:
    app = _load()
    with (
        patch.object(app.httpx, "AsyncClient", return_value=_client(_Resp(401, {}))),
        patch.object(app, "_call", AsyncMock()) as backend,
    ):
        result = await app.memory_store(text="t", ctx=_ctx("rl_live_bad"))
    assert result["status"] == 401
    backend.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_key_scopes_data_to_resolved_workspace() -> None:
    app = _load()
    with (
        patch.object(
            app.httpx, "AsyncClient", return_value=_client(_Resp(200, {"workspace_id": "ws-a"}))
        ),
        patch.object(app, "_call", AsyncMock(return_value={"ok": True})) as backend,
    ):
        await app.memory_store(text="t", workspace="ws-b", ctx=_ctx("rl_live_good"))
    assert backend.await_args.kwargs["json"]["workspace"] == "ws-a:ws-b"


@pytest.mark.asyncio
async def test_auth_can_be_disabled_for_local_dev_only() -> None:
    app = _load("false")
    with patch.object(app, "_call", AsyncMock(return_value={})) as backend:
        await app.skill_list(ctx=_ctx(None))
    assert backend.await_args.kwargs["params"]["workspace"] == "local"
