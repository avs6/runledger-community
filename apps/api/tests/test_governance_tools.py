"""W1-H governance: one tool-policy evaluator, holds, MCP proxy, capture, auto-tags.

Review IDs: S-01, cd:S-04, S-06, S-07, S-08, S-09, S-11, S-19, S-21, S-23, S-26.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from runledger_api.services import auto_tagging, mcp_client, tool_holds
from runledger_api.services import tool_policy_engine as engine
from runledger_api.services.capture_policy import CaptureResolver
from runledger_api.services.tool_policy_impact import proposed_rules, replay


def rule(tool: str, action: str, **kw: Any) -> engine.PolicyRule:
    base: dict[str, Any] = dict(
        id=uuid.uuid4(),
        name=f"{action}:{tool}",
        tool_name=tool,
        action=action,
        condition_type="all",
        condition_config={},
        scope_type="workspace",
        scope_id=None,
        priority=100,
    )
    base.update(kw)
    return engine.PolicyRule(**base)


# ── The evaluator ─────────────────────────────────────────────────────────────


def test_first_match_by_priority_decides() -> None:
    rules = [rule("*", "block", priority=1000), rule("search", "allow", priority=10)]
    assert engine.evaluate(rules, engine.ToolCallContext(tool_name="search")).action == "allow"
    assert engine.evaluate(rules, engine.ToolCallContext(tool_name="shell")).action == "block"


def test_no_policy_means_allow() -> None:
    decision = engine.evaluate([], engine.ToolCallContext(tool_name="x"))
    assert decision.action == "allow" and decision.allowed


def test_glob_and_case_insensitive_names() -> None:
    rules = [rule("GitHub_*", "require_approval")]
    ctx = engine.ToolCallContext(tool_name="github_create_issue")
    assert engine.evaluate(rules, ctx).action == "require_approval"


def test_scope_access_group_uses_caller_groups_only() -> None:
    group = uuid.uuid4()
    rules = [rule("*", "block", scope_type="access_group", scope_id=group)]
    outsider = engine.ToolCallContext(tool_name="x")
    member = engine.ToolCallContext(tool_name="x", access_group_ids=frozenset({group}))
    assert engine.evaluate(rules, outsider).action == "allow"
    assert engine.evaluate(rules, member).action == "block"


def test_scope_api_key_and_mcp_server() -> None:
    key, server = uuid.uuid4(), uuid.uuid4()
    rules = [
        rule("*", "block", scope_type="api_key", scope_id=key, priority=1),
        rule("*", "audit", scope_type="mcp_server", scope_id=server, priority=2),
    ]
    assert engine.evaluate(rules, engine.ToolCallContext("t", api_key_id=key)).action == "block"
    assert engine.evaluate(rules, engine.ToolCallContext("t", server_id=server)).action == "audit"
    assert engine.evaluate(rules, engine.ToolCallContext("t")).action == "allow"


@pytest.mark.parametrize(
    ("condition", "config", "ctx_kw", "expected"),
    [
        ("risk_score_gte", {"threshold": 70}, {"risk_score": 80}, "block"),
        ("risk_score_gte", {"threshold": 70}, {"risk_score": 10}, "allow"),
        ("feature_tag", {"feature_tag": "checkout"}, {"feature_tag": "checkout"}, "block"),
        ("end_user", {"end_user_id": "u1"}, {"end_user_id": "u2"}, "allow"),
        ("argument_contains", {"value": "DROP"}, {"arguments": {"sql": "drop table"}}, "block"),
        ("unknown_condition", {}, {}, "allow"),
    ],
)
def test_conditions(
    condition: str, config: dict[str, Any], ctx_kw: dict[str, Any], expected: str
) -> None:
    rules = [rule("t", "block", condition_type=condition, condition_config=config)]
    assert engine.evaluate(rules, engine.ToolCallContext("t", **ctx_kw)).action == expected


def test_deny_alias_normalizes_to_block() -> None:
    row = SimpleNamespace(
        id=uuid.uuid4(),
        name="old",
        tool_name="t",
        action="deny",
        condition_type=None,
        condition_config=None,
        scope_type="group",
        scope_id=None,
        priority=None,
        created_at=datetime.now(UTC),
    )
    parsed = engine.PolicyRule.from_row(row)  # type: ignore[arg-type]
    assert parsed.action == "block" and parsed.scope_type == "access_group"


def test_validation_refuses_unenforceable_policies() -> None:
    assert engine.validate_policy_fields(
        action="explode", condition_type=None, scope_type=None, scope_id=None
    )
    assert engine.validate_policy_fields(
        action="block", condition_type="all", scope_type="access_group", scope_id=None
    )
    assert not engine.validate_policy_fields(
        action="block", condition_type="all", scope_type="workspace", scope_id=None
    )


def test_tool_names_from_request_and_calls() -> None:
    tools = [{"type": "function", "function": {"name": "a"}}, {"name": "b"}, {"type": "x"}]
    assert engine.tool_names_from_request(tools) == ["a", "b"]
    assert engine.tool_name_of_call({"function": {"name": "a", "arguments": "{}"}}) == "a"


# ── Policy simulator (ENH) ────────────────────────────────────────────────────


def test_replay_reports_newly_blocked_calls() -> None:
    from runledger_api.schemas.workspace_controls import ToolPolicyCreate

    calls = [
        ("ingest", engine.ToolCallContext("shell", end_user_id="u1"), {"run_id": uuid.uuid4()}),
        ("ingest", engine.ToolCallContext("shell", end_user_id="u2"), {"run_id": uuid.uuid4()}),
        ("mcp", engine.ToolCallContext("search"), {}),
    ]
    draft = ToolPolicyCreate(name="no shell", tool_name="shell", action="block")
    after = proposed_rules([], draft, None, remove=False)
    out = replay(calls, [], after)
    assert out["changed"] == 2
    assert out["newly_blocked"] == 2
    assert out["affected_end_users"] == 2
    assert out["by_tool"][0].tool_name == "shell"
    assert out["by_tool"][0].after == {"block": 2}


def test_replay_remove_policy_restores_allow() -> None:
    existing = rule("shell", "block")
    after = proposed_rules([existing], None, existing.id, remove=True)
    out = replay([("ingest", engine.ToolCallContext("shell"), {})], [existing], after)
    assert out["newly_allowed"] == 1


# ── Capture scopes at ingest (S-09) ───────────────────────────────────────────


def test_capture_resolver_precedence() -> None:
    key = str(uuid.uuid4())
    resolver = CaptureResolver(
        default=("METADATA_ONLY", 0.0),
        scopes={
            ("feature_tag", "checkout"): ("FULL", 1.0),
            ("api_key", key): ("ERRORS_ONLY", 0.0),
        },
    )
    assert resolver.resolve({"feature_tag": "checkout"})[0] == "FULL"
    assert resolver.resolve({"feature_tag": "checkout", "api_key_id": key})[0] == "ERRORS_ONLY"
    assert resolver.resolve({"feature_tag": "other"})[0] == "METADATA_ONLY"


# ── Auto-tagging (S-19) ───────────────────────────────────────────────────────


def test_auto_tag_rules_apply_and_refuse_redos() -> None:
    rules = [
        auto_tagging.TagRule(
            uuid.uuid4(), "r1", "prefix", "feature_tag", "pay", "team", "billing", 1
        ),
        auto_tagging.TagRule(
            uuid.uuid4(), "r2", "equals", "metadata.env", "prod", "env", "prod", 2
        ),
        auto_tagging.TagRule(uuid.uuid4(), "r3", "contains", "feature_tag", "pay", "team", "x", 9),
    ]
    tags = auto_tagging.apply_rules(rules, {"feature_tag": "payments", "metadata": {"env": "prod"}})
    assert tags == {"team": "billing", "env": "prod"}
    assert auto_tagging.validate_rule_pattern("regex", "(a+)+$")
    assert auto_tagging.validate_rule_pattern("regex", "^ok$") is None


# ── MCP client (cd:S-04) ──────────────────────────────────────────────────────


def _server(**kw: Any) -> Any:
    base = dict(
        transport="http",
        url="https://mcp.example.com/mcp",
        auth_type="bearer",
        auth_config={"token": "t0k"},
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _mcp_transport(seen: list[dict[str, Any]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"body": body, "auth": request.headers.get("authorization")})
        if body.get("method") == "initialize":
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": 1, "result": {}},
                headers={"mcp-session-id": "s1"},
            )
        if "id" not in body:
            return httpx.Response(202)
        if body["method"] == "tools/list":
            result = {"tools": [{"name": "echo", "description": "Echo"}]}
        else:
            result = {"content": [{"type": "text", "text": json.dumps(body["params"])}]}
        sse = (
            f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'id': 2, 'result': result})}\n\n"
        )
        return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_mcp_client_calls_the_tool() -> None:
    seen: list[dict[str, Any]] = []
    with patch("runledger_api.services.mcp_client.check_url"):
        out = await mcp_client.call_tool(
            _server(), "echo", {"x": 1}, transport=_mcp_transport(seen)
        )
    assert out.is_error is False
    assert "echo" in out.result["content"][0]["text"]
    assert [s["body"].get("method") for s in seen] == [
        "initialize",
        "notifications/initialized",
        "tools/call",
    ]
    assert seen[0]["auth"] == "Bearer t0k"


@pytest.mark.asyncio
async def test_mcp_client_lists_tools() -> None:
    with patch("runledger_api.services.mcp_client.check_url"):
        tools = await mcp_client.list_tools(_server(), transport=_mcp_transport([]))
    assert tools == [{"name": "echo", "description": "Echo", "input_schema": None}]


@pytest.mark.asyncio
async def test_mcp_client_refuses_stdio() -> None:
    with pytest.raises(mcp_client.McpNotExecutable):
        await mcp_client.call_tool(_server(transport="stdio", url=None), "x", {})


# ── MCP governed call (S-01, cd:S-04) ─────────────────────────────────────────


def _mcp_db(mock_db_session: AsyncMock, srv: Any) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = srv
    result.scalars.return_value.first.return_value = None
    result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=result)


def _srv(ws_id: uuid.UUID) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(), workspace_id=ws_id, name="echo", is_active=True, **_server().__dict__
    )


@pytest.mark.asyncio
async def test_mcp_tool_call_blocked_is_recorded(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    _mcp_db(mock_db_session, _srv(mock_workspace.id))
    with patch.object(engine, "load_rules", new=AsyncMock(return_value=[rule("echo", "block")])):
        resp = await authed_client.post(
            "/mcp-registry/tools/call",
            json={"server_id": str(uuid.uuid4()), "tool_name": "echo", "arguments": {}},
        )
    assert resp.status_code == 403
    added = [c.args[0] for c in mock_db_session.add.call_args_list]
    assert any(getattr(o, "status", None) == "blocked" for o in added)
    assert any(getattr(o, "event_type", None) == "tool_call_blocked" for o in added)


@pytest.mark.asyncio
async def test_mcp_tool_call_hold_returns_real_approval(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    _mcp_db(mock_db_session, _srv(mock_workspace.id))
    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, "created_at", datetime.now(UTC))
    )
    with patch.object(
        engine, "load_rules", new=AsyncMock(return_value=[rule("echo", "require_approval")])
    ):
        resp = await authed_client.post(
            "/mcp-registry/tools/call",
            json={"server_id": str(uuid.uuid4()), "tool_name": "echo"},
        )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending_approval"
    added = [c.args[0] for c in mock_db_session.add.call_args_list]
    approvals = [o for o in added if type(o).__name__ == "Approval"]
    assert approvals and str(approvals[0].id) == body["approval_id"]
    assert approvals[0].request_type == "external_mcp_tool"


@pytest.mark.asyncio
async def test_mcp_tool_call_allowed_executes(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    _mcp_db(mock_db_session, _srv(mock_workspace.id))
    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, "created_at", datetime.now(UTC))
    )
    outcome = mcp_client.McpCallResult(result={"content": []}, latency_ms=5, is_error=False)
    with (
        patch.object(engine, "load_rules", new=AsyncMock(return_value=[])),
        patch.object(mcp_client, "call_tool", new=AsyncMock(return_value=outcome)) as call,
    ):
        resp = await authed_client.post(
            "/mcp-registry/tools/call",
            json={"server_id": str(uuid.uuid4()), "tool_name": "echo", "arguments": {"a": 1}},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["latency_ms"] == 5
    call.assert_awaited_once()


def test_identity_fields_are_not_accepted_from_body() -> None:
    from runledger_api.schemas.mcp_registry import McpToolCallRequest

    assert "api_key_id" not in McpToolCallRequest.model_fields
    assert "access_group_id" not in McpToolCallRequest.model_fields


# ── Gateway holds (approvals as gateway decisions) ────────────────────────────


def _gw_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    result.scalars.return_value.__iter__ = lambda self: iter([])
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_gateway_preflight_strips_blocked_tools() -> None:
    tools = [{"type": "function", "function": {"name": n}} for n in ("search", "shell")]
    with patch.object(engine, "load_rules", new=AsyncMock(return_value=[rule("shell", "block")])):
        kept = await tool_holds.govern_request_tools(
            _gw_db(),
            uuid.uuid4(),
            tools,
            api_key_id=None,
            principal_user_id=None,
            end_user_id=None,
            feature_tag=None,
            metadata={},
        )
    assert engine.tool_names_from_request(kept) == ["search"]


@pytest.mark.asyncio
async def test_gateway_preflight_holds_for_approval() -> None:
    tools = [{"type": "function", "function": {"name": "wire"}}]
    with (
        patch.object(
            engine, "load_rules", new=AsyncMock(return_value=[rule("wire", "require_approval")])
        ),
        pytest.raises(HTTPException) as exc,
    ):
        await tool_holds.govern_request_tools(
            _gw_db(),
            uuid.uuid4(),
            tools,
            api_key_id=None,
            principal_user_id=None,
            end_user_id=None,
            feature_tag=None,
            metadata={},
        )
    assert exc.value.status_code == 202
    assert exc.value.detail["status"] == "held"
    assert exc.value.headers["X-RunLedger-Approval-Id"] == exc.value.detail["approval_id"]


@pytest.mark.asyncio
async def test_gateway_finalize_blocks_disallowed_tool_call() -> None:
    calls = [{"id": "c1", "type": "function", "function": {"name": "shell", "arguments": "{}"}}]
    with patch.object(engine, "load_rules", new=AsyncMock(return_value=[rule("shell", "block")])):
        reason, held = await tool_holds.govern_response_tool_calls(
            _gw_db(),
            uuid.uuid4(),
            calls,
            api_key_id=None,
            principal_user_id=None,
            end_user_id=None,
            feature_tag=None,
            metadata={},
        )
    assert reason and "shell" in reason and held is None


def test_approval_id_read_from_metadata() -> None:
    assert tool_holds.approval_id_from({"runledger.approval_id": "abc"}) == "abc"
    assert tool_holds.approval_id_from({}) is None
