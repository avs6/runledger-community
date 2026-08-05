"""Unified policy decision service."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.gateway import GatewayRoute
from runledger_api.models.ledger import SecurityEvent, ToolRegistry
from runledger_api.models.scores import ScoreEvent
from runledger_api.schemas.policies import (
    PolicyCheckRequest,
    PolicyCheckResponse,
    PolicyDryRunDetail,
)
from runledger_api.services.budgets import check_budgets

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - import guard for static tooling
    Redis = object  # type: ignore[misc,assignment]


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
