"""Unified policy decision service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun, ToolCall
from runledger_api.models.gateway import GatewayRoute
from runledger_api.models.ledger import SecurityEvent, ToolRegistry
from runledger_api.models.mcp_registry import McpToolCall
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.search_tools import SearchTool
from runledger_api.schemas.policies import (
    FinopsSimulationRequest,
    FinopsSimulationResponse,
    PolicyCheckRequest,
    PolicyCheckResponse,
    PolicyDryRunDetail,
    SimulationImpact,
    ToolCostAccountingResponse,
    ToolCostBreakdownItem,
)
from runledger_api.services.budgets import check_budgets

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - import guard for static tooling
    Redis = object  # type: ignore[misc,assignment]


MODEL_COST_RATIOS: dict[str, float] = {
    "gpt-4o": 1.0,
    "gpt-4o-mini": 0.15,
    "gpt-4.1": 1.0,
    "gpt-4.1-mini": 0.18,
    "gpt-4.1-nano": 0.05,
    "gpt-5": 2.5,
    "o3": 3.0,
    "o4-mini": 0.55,
    "claude-sonnet-4": 0.6,
    "claude-opus-4": 1.5,
    "claude-haiku-3.5": 0.08,
    "claude-3-haiku": 0.05,
    "gemini-2.5-pro": 0.5,
    "gemini-2.5-flash": 0.08,
    "deepseek-v3": 0.07,
    "deepseek-r1": 0.22,
    "llama-3.3-70b": 0.04,
    "llama-4-scout": 0.06,
    "llama-4-maverick": 0.12,
    "qwen-3-235b": 0.08,
    "local/ollama": 0.0,
}

MODEL_LATENCY_MS: dict[str, float] = {
    "gpt-4o": 800,
    "gpt-4o-mini": 400,
    "gpt-4.1": 900,
    "gpt-4.1-mini": 350,
    "gpt-4.1-nano": 180,
    "gpt-5": 1400,
    "o3": 5000,
    "o4-mini": 2000,
    "claude-sonnet-4": 700,
    "claude-opus-4": 1200,
    "claude-haiku-3.5": 250,
    "claude-3-haiku": 200,
    "gemini-2.5-pro": 600,
    "gemini-2.5-flash": 250,
    "deepseek-v3": 500,
    "deepseek-r1": 1800,
    "llama-3.3-70b": 300,
    "llama-4-scout": 280,
    "llama-4-maverick": 450,
    "qwen-3-235b": 600,
    "local/ollama": 600,
}

QUALITY_RISK_MAP: dict[str, str] = {
    "gpt-4o": "low",
    "gpt-4o-mini": "medium",
    "gpt-4.1": "low",
    "gpt-4.1-mini": "medium",
    "gpt-4.1-nano": "high",
    "gpt-5": "low",
    "o3": "low",
    "o4-mini": "low",
    "claude-sonnet-4": "low",
    "claude-opus-4": "low",
    "claude-haiku-3.5": "medium",
    "claude-3-haiku": "high",
    "gemini-2.5-pro": "low",
    "gemini-2.5-flash": "medium",
    "deepseek-v3": "medium",
    "deepseek-r1": "low",
    "llama-3.3-70b": "medium",
    "llama-4-scout": "medium",
    "llama-4-maverick": "low",
    "qwen-3-235b": "medium",
    "local/ollama": "high",
}


def _match_model_key(model_name: str | None) -> str | None:
    if not model_name:
        return None
    normalized = model_name.lower().strip()
    for key in MODEL_COST_RATIOS:
        if key in normalized or normalized in key:
            return key
    return None


async def _get_tool_policy(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    tool_name: str,
) -> str | None:
    result = await db.execute(
        select(ToolRegistry.policy).where(
            ToolRegistry.workspace_id == workspace_id,
            ToolRegistry.tool_name == tool_name,
        )
    )
    return result.scalar_one_or_none()


async def _has_active_gateway_route(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    model_alias: str,
) -> bool:
    result = await db.execute(
        select(GatewayRoute.id).where(
            GatewayRoute.workspace_id == workspace_id,
            GatewayRoute.alias == model_alias,
            GatewayRoute.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


async def _passes_score_gate(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    gate_name: str,
    min_value: Decimal,
    source: str | None,
    run_id: uuid.UUID | None,
) -> bool:
    stmt = (
        select(ScoreEvent.value)
        .where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.name == gate_name,
        )
        .order_by(ScoreEvent.created_at.desc())
        .limit(1)
    )
    if source is not None:
        stmt = stmt.where(ScoreEvent.source == source)
    if run_id is not None:
        stmt = stmt.where(ScoreEvent.run_id == run_id)

    result = await db.execute(stmt)
    value = result.scalar_one_or_none()
    if value is None:
        return False
    return Decimal(str(value)) >= min_value


async def _record_policy_violation(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    event_type: str,
    details: dict[str, str],
    tool_name: str | None = None,
    end_user_id: str | None = None,
) -> None:
    db.add(
        SecurityEvent(
            workspace_id=workspace_id,
            event_type=event_type,
            tool_name=tool_name,
            end_user_id=end_user_id,
            details=details,
        )
    )
    await db.commit()


async def _collect_dry_run_detail(
    db: AsyncSession,
    redis: Redis,
    workspace_id: uuid.UUID,
    body: PolicyCheckRequest,
    budget_check: object,
) -> PolicyDryRunDetail:
    """Gather diagnostic detail for each policy dimension."""
    detail = PolicyDryRunDetail()

    if hasattr(budget_check, "remaining_usd"):
        detail.budget_remaining_usd = getattr(budget_check, "remaining_usd", None)
    if hasattr(budget_check, "limit_usd"):
        detail.budget_limit_usd = getattr(budget_check, "limit_usd", None)
    if hasattr(budget_check, "period"):
        detail.budget_period = getattr(budget_check, "period", None)

    if body.tool_name:
        tool_exists = await db.execute(
            select(ToolRegistry.tool_name).where(
                ToolRegistry.workspace_id == workspace_id,
                ToolRegistry.tool_name == body.tool_name,
            )
        )
        detail.tool_registered = tool_exists.scalar_one_or_none() is not None
        detail.tool_policy_setting = await _get_tool_policy(db, workspace_id, body.tool_name)

    if body.model_alias:
        routes_result = await db.execute(
            select(GatewayRoute.alias).where(
                GatewayRoute.workspace_id == workspace_id,
                GatewayRoute.is_active.is_(True),
            )
        )
        aliases = [r for r in routes_result.scalars().all()]
        detail.gateway_routes_found = len(aliases)
        detail.gateway_route_aliases = aliases[:20]

    if body.score_gate is not None:
        stmt = (
            select(ScoreEvent.value)
            .where(
                ScoreEvent.workspace_id == workspace_id,
                ScoreEvent.name == body.score_gate.name,
            )
            .order_by(ScoreEvent.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        val = result.scalar_one_or_none()
        detail.score_latest_value = Decimal(str(val)) if val is not None else None
        detail.score_gate_threshold = body.score_gate.min_value

    return detail


async def evaluate_policy_check(
    db: AsyncSession,
    redis: Redis,
    workspace_id: uuid.UUID,
    body: PolicyCheckRequest,
) -> PolicyCheckResponse:
    reasons: list[str] = []
    decision = "allow"
    allowed = True
    budget_action: str | None = None
    budget_id: str | None = None
    downgrade_model: str | None = None
    tool_policy: str | None = None
    gateway_route_available: bool | None = None
    score_gate_passed: bool | None = None

    budget_check = await check_budgets(
        redis=redis,
        db=db,
        workspace_id=workspace_id,
        end_user_id=body.end_user_id,
        feature_tag=body.feature_tag,
    )
    if not budget_check.allowed:
        budget_action = budget_check.action
        budget_id = budget_check.budget_id
        if budget_check.action == "downgrade":
            decision = "downgrade"
            allowed = True
            downgrade_model = budget_check.downgrade_model
            reasons.append("Budget exceeded: downgrade required")
        else:
            decision = "block"
            allowed = False
            reasons.append("Budget exceeded: request blocked")

    if body.tool_name:
        tool_policy = await _get_tool_policy(db, workspace_id, body.tool_name)
        if tool_policy == "block":
            decision = "block"
            allowed = False
            reasons.append(f"Tool '{body.tool_name}' is blocked by policy")
        elif tool_policy == "audit":
            reasons.append(f"Tool '{body.tool_name}' requires audit")

    if body.model_alias:
        gateway_route_available = await _has_active_gateway_route(
            db, workspace_id, body.model_alias
        )
        if not gateway_route_available:
            decision = "block"
            allowed = False
            reasons.append(f"No active gateway route for alias '{body.model_alias}'")

    if body.score_gate is not None:
        score_gate_passed = await _passes_score_gate(
            db=db,
            workspace_id=workspace_id,
            gate_name=body.score_gate.name,
            min_value=body.score_gate.min_value,
            source=body.score_gate.source,
            run_id=body.score_gate.run_id,
        )
        if not score_gate_passed:
            decision = "block"
            allowed = False
            reasons.append(
                f"Score gate failed: {body.score_gate.name} < {body.score_gate.min_value}"
            )

    detail: PolicyDryRunDetail | None = None
    if body.dry_run:
        detail = await _collect_dry_run_detail(db, redis, workspace_id, body, budget_check)
    elif not allowed:
        await _record_policy_violation(
            db=db,
            workspace_id=workspace_id,
            event_type="policy_violation",
            tool_name=body.tool_name,
            end_user_id=body.end_user_id,
            details={
                "decision": decision,
                "reasons": "; ".join(reasons),
            },
        )

    return PolicyCheckResponse(
        allowed=allowed,
        decision=decision,
        reasons=reasons,
        budget_action=budget_action,
        budget_id=budget_id,
        downgrade_model=downgrade_model,
        tool_policy=tool_policy,
        gateway_route_available=gateway_route_available,
        score_gate_passed=score_gate_passed,
        detail=detail,
    )


async def simulate_finops_policy(
    db: AsyncSession,
    redis: Redis,
    workspace_id: uuid.UUID,
    body: FinopsSimulationRequest,
) -> FinopsSimulationResponse:
    policy_result = await evaluate_policy_check(
        db=db,
        redis=redis,
        workspace_id=workspace_id,
        body=PolicyCheckRequest(
            end_user_id=body.end_user_id,
            feature_tag=body.feature_tag,
            tool_name=body.tool_name,
            model_alias=body.model_alias,
            dry_run=True,
        ),
    )
    policy = PolicyCheckResponse.model_validate(policy_result, from_attributes=True)

    t_from = body.from_dt or (datetime.now(UTC) - timedelta(days=7))
    t_to = body.to_dt or datetime.now(UTC)

    filters = [
        ToolCall.workspace_id == workspace_id,
        ToolCall.created_at >= t_from,
        ToolCall.created_at < t_to,
    ]
    run_filters = [
        AgentRun.workspace_id == workspace_id,
    ]
    if body.intent:
        run_filters.append(AgentRun.intent == body.intent)
    if body.end_user_id:
        run_filters.append(AgentRun.end_user_id == body.end_user_id)
    if body.feature_tag:
        run_filters.append(AgentRun.feature_tag == body.feature_tag)

    run_ids_q = select(AgentRun.id).where(*run_filters)
    mcp_filters = [
        McpToolCall.workspace_id == workspace_id,
        McpToolCall.created_at >= t_from,
        McpToolCall.created_at < t_to,
    ]
    if body.tool_name:
        filters.append(ToolCall.tool_name == body.tool_name)
        mcp_filters.append(McpToolCall.tool_name == body.tool_name)

    current_cost_stmt = select(
        func.coalesce(func.sum(McpToolCall.cost_usd), Decimal(0)).label("mcp_cost"),
        func.count(McpToolCall.id).label("mcp_calls"),
    ).where(*mcp_filters)
    current_cost_row = (await db.execute(current_cost_stmt)).one()

    search_stmt = (
        select(
            func.count(ToolCall.id).label("tool_calls"),
            func.coalesce(func.sum(SearchTool.cost_per_query), Decimal(0)).label("search_cost"),
            func.avg(ToolCall.duration_ms).label("avg_duration"),
        )
        .select_from(ToolCall)
        .join(
            SearchTool,
            (SearchTool.workspace_id == workspace_id)
            & (func.lower(SearchTool.name) == func.lower(ToolCall.tool_name)),
            isouter=True,
        )
        .where(*filters, ToolCall.run_id.in_(run_ids_q))
    )
    search_row = (await db.execute(search_stmt)).one()

    affected = int((current_cost_row.mcp_calls or 0) + (search_row.tool_calls or 0))
    current_cost = Decimal(str(current_cost_row.mcp_cost or 0)) + Decimal(
        str(search_row.search_cost or 0)
    )
    current_latency = (
        Decimal(str(round(float(search_row.avg_duration), 1)))
        if search_row.avg_duration is not None
        else None
    )

    if affected == 0:
        return FinopsSimulationResponse(
            policy=policy,
            affected_requests=0,
            current_cost_usd=Decimal(0),
            projected_cost_usd=Decimal(0),
            projected_savings_usd=Decimal(0),
            savings_pct=Decimal(0),
            current_avg_latency_ms=None,
            projected_latency_ms=None,
            latency_delta_pct=None,
            quality_risk="unknown",
            confidence="low",
            impacts=[],
            description="No matching tool or MCP activity found for the selected policy simulation.",
        )

    current_key = _match_model_key(body.current_model)
    proposed_key = _match_model_key(body.proposed_model)
    model_cost_ratio = Decimal(1)
    if current_key and proposed_key:
        cur_ratio = MODEL_COST_RATIOS.get(current_key, 1.0)
        new_ratio = MODEL_COST_RATIOS.get(proposed_key, 1.0)
        if cur_ratio > 0:
            model_cost_ratio = Decimal(str(round(new_ratio / cur_ratio, 4)))

    cache_savings_pct = Decimal("0.20") if body.enable_cache else Decimal(0)
    compression_pct = Decimal("0.15") if body.enable_compression else Decimal(0)
    projected_cost = (
        current_cost * model_cost_ratio * (1 - cache_savings_pct) * (1 - compression_pct)
    )
    projected_savings = current_cost - projected_cost
    savings_pct = (projected_savings / current_cost * 100) if current_cost > 0 else Decimal(0)

    projected_latency_ms = None
    latency_delta_pct = None
    if current_latency is not None and proposed_key:
        proposed_latency = MODEL_LATENCY_MS.get(proposed_key)
        if proposed_latency is not None:
            projected_latency_ms = Decimal(str(round(proposed_latency, 1)))
            if current_latency > 0:
                latency_delta_pct = Decimal(
                    str(
                        round(
                            (proposed_latency - float(current_latency))
                            / float(current_latency)
                            * 100,
                            1,
                        )
                    )
                )

    quality_risk = QUALITY_RISK_MAP.get(proposed_key or current_key or "", "medium")
    confidence = "high" if affected >= 100 else "medium" if affected >= 20 else "directional"
    impacts: list[SimulationImpact] = []
    if body.current_model and body.proposed_model:
        impacts.append(
            SimulationImpact(
                label="Model routing",
                current_value=body.current_model,
                projected_value=body.proposed_model,
                delta_pct=Decimal(str(round((float(model_cost_ratio) - 1) * 100, 1))),
            )
        )
    if body.enable_cache:
        impacts.append(
            SimulationImpact(
                label="Cache policy",
                current_value="Disabled",
                projected_value="Enabled",
                delta_pct=Decimal("-20"),
            )
        )
    if body.enable_compression:
        impacts.append(
            SimulationImpact(
                label="Prompt compression",
                current_value="Disabled",
                projected_value="Enabled",
                delta_pct=Decimal("-15"),
            )
        )

    return FinopsSimulationResponse(
        policy=policy,
        affected_requests=affected,
        current_cost_usd=current_cost,
        projected_cost_usd=projected_cost,
        projected_savings_usd=projected_savings,
        savings_pct=savings_pct,
        current_avg_latency_ms=current_latency,
        projected_latency_ms=projected_latency_ms,
        latency_delta_pct=latency_delta_pct,
        quality_risk=quality_risk,
        confidence=confidence,
        impacts=impacts,
        description=(
            f"Simulated policy-aware FinOps change across {affected:,} tool and MCP actions. "
            f"Projected savings: ${float(projected_savings):.4f} ({float(savings_pct):.1f}%)."
        ),
    )


async def get_tool_cost_accounting(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    from_dt: datetime,
    to_dt: datetime,
) -> ToolCostAccountingResponse:
    items: list[ToolCostBreakdownItem] = []

    mcp_rows = (
        await db.execute(
            select(
                McpToolCall.tool_name,
                func.count(McpToolCall.id).label("call_count"),
                func.coalesce(func.sum(McpToolCall.cost_usd), Decimal(0)).label("total_cost"),
            )
            .where(
                McpToolCall.workspace_id == workspace_id,
                McpToolCall.created_at >= from_dt,
                McpToolCall.created_at < to_dt,
            )
            .group_by(McpToolCall.tool_name)
            .order_by(func.coalesce(func.sum(McpToolCall.cost_usd), Decimal(0)).desc())
        )
    ).all()
    for row in mcp_rows:
        total_cost = Decimal(str(row.total_cost or 0))
        call_count = int(row.call_count or 0)
        items.append(
            ToolCostBreakdownItem(
                source="mcp_tracked",
                tool_name=row.tool_name,
                classification="tracked",
                call_count=call_count,
                total_cost_usd=total_cost,
                avg_cost_usd=(total_cost / call_count) if call_count else None,
            )
        )

    priced_rows = (
        await db.execute(
            select(
                ToolCall.tool_name,
                ToolCall.tool_type,
                func.count(ToolCall.id).label("call_count"),
                SearchTool.cost_per_query.label("unit_cost"),
            )
            .select_from(ToolCall)
            .join(
                SearchTool,
                (SearchTool.workspace_id == workspace_id)
                & (func.lower(SearchTool.name) == func.lower(ToolCall.tool_name)),
            )
            .where(
                ToolCall.workspace_id == workspace_id,
                ToolCall.created_at >= from_dt,
                ToolCall.created_at < to_dt,
            )
            .group_by(ToolCall.tool_name, ToolCall.tool_type, SearchTool.cost_per_query)
        )
    ).all()
    for row in priced_rows:
        call_count = int(row.call_count or 0)
        unit_cost = Decimal(str(row.unit_cost or 0))
        total_cost = unit_cost * call_count
        items.append(
            ToolCostBreakdownItem(
                source="search_tool_estimated",
                tool_name=row.tool_name,
                classification=str(row.tool_type),
                call_count=call_count,
                total_cost_usd=total_cost,
                avg_cost_usd=unit_cost if call_count else None,
            )
        )

    unpriced_rows = (
        await db.execute(
            select(
                ToolCall.tool_name,
                ToolCall.tool_type,
                func.count(ToolCall.id).label("call_count"),
            )
            .select_from(ToolCall)
            .join(
                SearchTool,
                (SearchTool.workspace_id == workspace_id)
                & (func.lower(SearchTool.name) == func.lower(ToolCall.tool_name)),
                isouter=True,
            )
            .where(
                ToolCall.workspace_id == workspace_id,
                ToolCall.created_at >= from_dt,
                ToolCall.created_at < to_dt,
                SearchTool.id.is_(None),
            )
            .group_by(ToolCall.tool_name, ToolCall.tool_type)
        )
    ).all()
    for row in unpriced_rows:
        items.append(
            ToolCostBreakdownItem(
                source="unpriced_tool_activity",
                tool_name=row.tool_name,
                classification=str(row.tool_type),
                call_count=int(row.call_count or 0),
                total_cost_usd=Decimal(0),
                avg_cost_usd=Decimal(0),
            )
        )

    total_calls = sum(item.call_count for item in items)
    tracked_calls = sum(item.call_count for item in items if item.source == "mcp_tracked")
    estimated_calls = sum(item.call_count for item in items if item.source != "mcp_tracked")
    total_cost = sum((item.total_cost_usd for item in items), Decimal(0))

    return ToolCostAccountingResponse(
        items=items,
        total_calls=total_calls,
        tracked_calls=tracked_calls,
        estimated_calls=estimated_calls,
        total_cost_usd=total_cost,
    )
