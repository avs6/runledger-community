"""Policy simulator: replay recent real tool calls against a draft policy.

``POST /tool-policies/simulate-impact`` answers "what would this policy have done to
the last N days of traffic?" before the policy is saved. It replays

* ingested tool calls (``tool_calls``, joined to their run for end user, feature tag
  and API key), and
* governed MCP calls (``mcp_tool_calls``),

through the shared evaluator twice: once with the active policy set (``before``) and
once with the draft applied (``after``). Access-group membership is not historical,
so access-group-scoped rules are evaluated against today's membership of the key's
owner only when it can be resolved; the response says so in ``notes``.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun, ToolCall
from runledger_api.models.mcp_registry import McpToolCall
from runledger_api.schemas.workspace_controls import (
    ToolPolicyCreate,
    ToolPolicyImpactResponse,
    ToolPolicyImpactSample,
    ToolPolicyImpactToolRow,
)
from runledger_api.services import tool_policy_engine as engine

MAX_CALLS = 20_000
MAX_SAMPLES = 25


def draft_rule(draft: ToolPolicyCreate, policy_id: uuid.UUID | None) -> engine.PolicyRule:
    return engine.PolicyRule(
        id=policy_id or uuid.uuid4(),
        name=draft.name,
        tool_name=draft.tool_name or "*",
        action=engine.normalize_action(draft.action),
        condition_type=draft.condition_type or "all",
        condition_config=dict(draft.condition_config or {}),
        scope_type=engine.normalize_scope(draft.scope_type),
        scope_id=draft.scope_id,
        priority=draft.priority,
        order=datetime.now(UTC).timestamp(),
    )


def proposed_rules(
    current: list[engine.PolicyRule],
    draft: ToolPolicyCreate | None,
    policy_id: uuid.UUID | None,
    *,
    remove: bool,
) -> list[engine.PolicyRule]:
    rules = [r for r in current if policy_id is None or r.id != policy_id]
    if draft is not None and not remove and draft.is_active:
        rules.append(draft_rule(draft, policy_id))
    return engine.sort_rules(rules)


def _ctx_from_tool_call(row: Any) -> tuple[str, engine.ToolCallContext, dict[str, Any]]:
    tool_type = getattr(row, "tool_type", None)
    ctx = engine.ToolCallContext(
        tool_name=row.tool_name or "",
        tool_type=str(getattr(tool_type, "value", tool_type)) if tool_type is not None else None,
        risk_score=row.risk_score,
        end_user_id=row.end_user_id,
        feature_tag=row.feature_tag,
        api_key_id=row.api_key_id,
    )
    meta = {
        "occurred_at": row.created_at,
        "end_user_id": row.end_user_id,
        "feature_tag": row.feature_tag,
        "run_id": row.run_id,
    }
    return "ingest", ctx, meta


def _ctx_from_mcp(row: McpToolCall) -> tuple[str, engine.ToolCallContext, dict[str, Any]]:
    ctx = engine.ToolCallContext(
        tool_name=row.tool_name or "",
        tool_type="mcp",
        end_user_id=row.end_user_id,
        api_key_id=row.api_key_id,
        server_id=row.mcp_server_id,
        arguments=row.arguments or {},
    )
    meta = {
        "occurred_at": row.created_at,
        "end_user_id": row.end_user_id,
        "feature_tag": None,
        "run_id": None,
    }
    return "mcp", ctx, meta


def replay(
    calls: list[tuple[str, engine.ToolCallContext, dict[str, Any]]],
    before_rules: list[engine.PolicyRule],
    after_rules: list[engine.PolicyRule],
) -> dict[str, Any]:
    """Pure replay so it can be unit-tested without a database."""
    per_tool: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "before": Counter(), "after": Counter(), "changed": 0}
    )
    transitions: Counter[str] = Counter()
    samples: list[ToolPolicyImpactSample] = []
    users: set[str] = set()
    runs: set[uuid.UUID] = set()
    for source, ctx, meta in calls:
        before = engine.evaluate(before_rules, ctx).action
        after = engine.evaluate(after_rules, ctx).action
        row = per_tool[ctx.tool_name]
        row["calls"] += 1
        row["before"][before] += 1
        row["after"][after] += 1
        if before == after:
            continue
        row["changed"] += 1
        transitions[after] += 1
        end_user = meta.get("end_user_id") or ctx.end_user_id
        if end_user:
            users.add(str(end_user))
        if meta.get("run_id"):
            runs.add(meta["run_id"])
        if len(samples) < MAX_SAMPLES:
            samples.append(
                ToolPolicyImpactSample(
                    source=source,
                    tool_name=ctx.tool_name,
                    occurred_at=meta.get("occurred_at"),
                    before=before,
                    after=after,
                    end_user_id=meta.get("end_user_id"),
                    feature_tag=meta.get("feature_tag"),
                    run_id=meta.get("run_id"),
                )
            )
    by_tool = sorted(
        (
            ToolPolicyImpactToolRow(
                tool_name=name,
                calls=data["calls"],
                before=dict(data["before"]),
                after=dict(data["after"]),
                changed=data["changed"],
            )
            for name, data in per_tool.items()
        ),
        key=lambda r: (-r.changed, -r.calls, r.tool_name),
    )
    return {
        "changed": sum(transitions.values()),
        "newly_blocked": transitions["block"],
        "newly_held": transitions["require_approval"],
        "newly_audited": transitions["audit"],
        "newly_allowed": transitions["allow"],
        "affected_end_users": len(users),
        "affected_runs": len(runs),
        "by_tool": by_tool,
        "samples": samples,
    }


async def simulate_impact(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    draft: ToolPolicyCreate | None,
    policy_id: uuid.UUID | None,
    remove: bool,
    days: int,
) -> ToolPolicyImpactResponse:
    window_end = datetime.now(UTC)
    window_start = window_end - timedelta(days=days)
    current = await engine.load_rules(db, workspace_id, use_cache=False)
    after = proposed_rules(current, draft, policy_id, remove=remove)

    tool_rows = (
        await db.execute(
            select(
                ToolCall.tool_name,
                ToolCall.tool_type,
                ToolCall.risk_score,
                ToolCall.created_at,
                ToolCall.run_id,
                AgentRun.end_user_id,
                AgentRun.feature_tag,
                AgentRun.api_key_id,
            )
            .join(AgentRun, AgentRun.id == ToolCall.run_id, isouter=True)
            .where(
                ToolCall.workspace_id == workspace_id,
                ToolCall.created_at >= window_start,
                ToolCall.created_at < window_end,
            )
            .order_by(ToolCall.created_at.desc())
            .limit(MAX_CALLS + 1)
        )
    ).all()
    mcp_rows = (
        (
            await db.execute(
                select(McpToolCall)
                .where(
                    McpToolCall.workspace_id == workspace_id,
                    McpToolCall.created_at >= window_start,
                    McpToolCall.created_at < window_end,
                )
                .order_by(McpToolCall.created_at.desc())
                .limit(MAX_CALLS + 1)
            )
        )
        .scalars()
        .all()
    )
    truncated = len(tool_rows) > MAX_CALLS or len(mcp_rows) > MAX_CALLS
    calls = [_ctx_from_tool_call(r) for r in tool_rows[:MAX_CALLS]] + [
        _ctx_from_mcp(r) for r in mcp_rows[:MAX_CALLS]
    ]
    result = replay(calls, current, after)
    notes: list[str] = []
    if any(r.scope_type == "access_group" for r in after):
        notes.append(
            "Access-group rules can't be replayed against past membership; "
            "calls are evaluated without group membership."
        )
    if truncated:
        notes.append(f"Only the most recent {MAX_CALLS:,} calls per source were replayed.")
    return ToolPolicyImpactResponse(
        days=days,
        window_start=window_start,
        window_end=window_end,
        calls_replayed=len(calls),
        truncated=truncated,
        notes=notes,
        **result,
    )
