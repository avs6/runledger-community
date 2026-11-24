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
        runtime_enforcement=False,
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
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalars_list_result([tool]), _scalars_list_result([])]
    )

    with _patch_rules([_rule("search", "block")]):
        resp = await authed_client.get("/tools/registry")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["tool_name"] == "search"
    assert data["items"][0]["effective_action"] == "block"


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


# ── test_check_tool_allow (cache miss → DB allow) ─────────────────────────────


def _rule(tool: str, action: str, **kw: object) -> object:
    from runledger_api.services.tool_policy_engine import PolicyRule

    base: dict[str, object] = dict(
        id=uuid.uuid4(),
        name=f"registry:{tool}",
        tool_name=tool,
        action=action,
        condition_type="all",
        condition_config={},
        scope_type="workspace",
        scope_id=None,
        priority=50,
    )
    base.update(kw)
    return PolicyRule(**base)  # type: ignore[arg-type]


def _patch_rules(rules: list[object]) -> object:
    from unittest.mock import patch

    return patch(
        "runledger_api.services.tool_policy_engine.load_rules",
        new=AsyncMock(return_value=rules),
    )


@pytest.mark.asyncio
async def test_check_tool_allow_no_policy(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    """No matching ToolPolicy → allow (shared evaluator)."""
    with _patch_rules([]):
        resp = await authed_client.get("/tools/check/unknown_tool")
    assert resp.status_code == 200
    data = resp.json()
    assert data["policy"] == "allow"
    assert data["runtime_enforcement"] is True
    assert data["allowed"] is True


@pytest.mark.asyncio
async def test_check_tool_audit_records_event(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    with _patch_rules([_rule("read_file", "audit")]):
        resp = await authed_client.get("/tools/check/read_file")
    assert resp.status_code == 200
    assert resp.json()["policy"] == "audit"
    added = [c.args[0] for c in mock_db_session.add.call_args_list]
    assert any(getattr(o, "event_type", None) == "tool_call_audited" for o in added)


@pytest.mark.asyncio
async def test_check_tool_blocked_returns_403(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    with _patch_rules([_rule("delete_record", "block")]):
        resp = await authed_client.get("/tools/check/delete_record")
    assert resp.status_code == 403
    assert "blocked" in resp.json()["detail"].lower()
    added = [c.args[0] for c in mock_db_session.add.call_args_list]
    assert any(getattr(o, "event_type", None) == "tool_call_blocked" for o in added)


@pytest.mark.asyncio
async def test_check_tool_glob_allow_beats_lower_priority_block(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    rules = [
        _rule("*", "block", name="deny-all", priority=1000),
        _rule("search_*", "allow", name="allow-search", priority=10),
    ]
    with _patch_rules(rules):
        ok = await authed_client.get("/tools/check/search_web")
        blocked = await authed_client.get("/tools/check/send_email")
    assert ok.status_code == 200
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_check_tool_require_approval_opens_real_approval(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None
    with _patch_rules([_rule("wire_transfer", "require_approval")]):
        resp = await authed_client.get("/tools/check/wire_transfer")
    assert resp.status_code == 403
    approval_id = resp.headers["x-runledger-approval-id"]
    added = [c.args[0] for c in mock_db_session.add.call_args_list]
    approvals = [o for o in added if type(o).__name__ == "Approval"]
    assert approvals and str(approvals[0].id) == approval_id
    assert approvals[0].status == "pending"


# ── test_check_tool_requires_auth ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_tool_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/tools/check/web_search")
    assert resp.status_code == 401


# ── test_tools_requires_auth ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tools_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/tools/registry")
    assert resp.status_code == 401
