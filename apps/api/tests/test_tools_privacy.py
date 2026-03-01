"""
Tests for Phase 11 tool registry and privacy capture policy endpoints.

Covers:
  POST   /tools/registry              — create tool
  POST   /tools/registry              — upsert (same tool_name)
  GET    /tools/registry              — list tools
  DELETE /tools/registry/{tool_name}  — delete tool
  GET    /privacy/capture-policy      — 404 when not set
  PUT    /privacy/capture-policy      — upsert policy
  Auth enforcement

Uses authed_client / mock_db_session fixtures from conftest. No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_tool(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        tool_name="search",
        policy="audit",
        description=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_policy(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        privacy_mode="METADATA_ONLY",
        sampled_rate=None,
        updated_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _scalar_result(value: object) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    return m


def _scalars_list_result(rows: list[object]) -> MagicMock:
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


# ── test_create_tool_registry ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_tool_registry(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    tool = _make_tool(workspace_id=mock_workspace.id)

    mock_db_session.execute = AsyncMock(return_value=_scalar_result(None))
    mock_db_session.flush = AsyncMock()
    mock_db_session.commit = AsyncMock()

    async def _mock_refresh(obj):
        obj.id = tool.id
        obj.workspace_id = mock_workspace.id
        obj.tool_name = "search"
        obj.policy = "audit"
        obj.description = None
        obj.created_at = tool.created_at
        obj.updated_at = tool.updated_at

    mock_db_session.refresh = _mock_refresh

    resp = await authed_client.post(
        "/tools/registry",
        json={"tool_name": "search", "policy": "audit"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tool_name"] == "search"
    assert data["policy"] == "audit"
    assert data["description"] is None


# ── test_upsert_tool_registry ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_tool_registry(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST with same tool_name should update, not create a duplicate."""
    existing = _make_tool(workspace_id=mock_workspace.id, tool_name="calculator", policy="allow")

    # First call: find existing
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(existing))
    mock_db_session.commit = AsyncMock()

    async def _mock_refresh(obj):
        obj.id = existing.id
        obj.workspace_id = mock_workspace.id
        obj.tool_name = "calculator"
        obj.policy = "block"
        obj.description = "blocked"
        obj.created_at = existing.created_at
        obj.updated_at = datetime.now(UTC)

    mock_db_session.refresh = _mock_refresh

    resp = await authed_client.post(
        "/tools/registry",
        json={"tool_name": "calculator", "policy": "block", "description": "blocked"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["policy"] == "block"
    assert data["description"] == "blocked"


# ── test_list_tool_registry ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_tool_registry(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    tool = _make_tool(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result([tool]))

    resp = await authed_client.get("/tools/registry")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["tool_name"] == "search"


# ── test_delete_tool_registry ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_tool_registry(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    tool = _make_tool(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(tool))
    mock_db_session.commit = AsyncMock()

    resp = await authed_client.delete("/tools/registry/search")
    assert resp.status_code == 204


# ── test_get_capture_policy_404 ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_capture_policy_404(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(None))
    resp = await authed_client.get("/privacy/capture-policy")
    assert resp.status_code == 404


# ── test_upsert_capture_policy ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_capture_policy(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    policy = _make_policy(workspace_id=mock_workspace.id, privacy_mode="METADATA_ONLY")

    mock_db_session.execute = AsyncMock(return_value=_scalar_result(None))
    mock_db_session.flush = AsyncMock()
    mock_db_session.commit = AsyncMock()

    async def _mock_refresh(obj):
        obj.id = policy.id
        obj.workspace_id = mock_workspace.id
        obj.privacy_mode = "METADATA_ONLY"
        obj.sampled_rate = None
        obj.updated_at = policy.updated_at
        obj.created_at = policy.created_at

    mock_db_session.refresh = _mock_refresh

    resp = await authed_client.put(
        "/privacy/capture-policy",
        json={"privacy_mode": "METADATA_ONLY"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["privacy_mode"] == "METADATA_ONLY"
    assert data["sampled_rate"] is None


# ── test_tools_requires_auth ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tools_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/tools/registry")
    assert resp.status_code == 401
