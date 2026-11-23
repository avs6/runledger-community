"""Related context for one entity (replaces the per-page posture endpoints).

``GET /context?entity=<type>&id=<id>`` returns a small set of counts and links about one
entity — its recent runs and spend, the budgets and policies that apply to it — so a page
can open a "Related" drawer on demand instead of loading a dozen posture cards on mount.

Entities: ``workspace`` (id ignored), ``workflow`` (workflow id, or a feature tag), ``api_key``, ``route``
(id), ``budget`` (id) and ``prompt`` (id).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit
from runledger_api.core.redis import get_redis
from runledger_api.models.agents import WorkflowDefinition
from runledger_api.models.budgets import Budget
from runledger_api.models.events import AgentRun, RunStatusEnum
from runledger_api.models.gateway import GatewayRequest, GatewayRoute, RoutingPolicy
from runledger_api.models.guardrails import GuardrailRule
from runledger_api.models.prompts import Prompt, PromptVersion
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.services.budgets import get_budget_spend

router = APIRouter(tags=["context"], dependencies=[Depends(analytics_rate_limit)])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

ENTITIES = ("workspace", "workflow", "api_key", "route", "budget", "prompt")
WINDOW_DAYS = 30


class ContextItem(BaseModel):
    key: str
    label: str
    value: str
    href: str | None = None


class EntityContext(BaseModel):
    entity: str
    id: str | None
    title: str
    window_days: int = WINDOW_DAYS
    items: list[ContextItem]


def _money(value: Decimal | float | None) -> str:
    return f"${Decimal(str(value or 0)):.2f}"


async def _run_stats(
    db: AsyncSession, workspace_id: uuid.UUID, *conds: Any
) -> tuple[int, Decimal, int]:
    since = datetime.now(UTC) - timedelta(days=WINDOW_DAYS)
    row = (
        await db.execute(
            select(
                func.count(AgentRun.id),
                func.coalesce(func.sum(AgentRun.total_cost_usd), 0),
                func.count(AgentRun.id).filter(AgentRun.status == RunStatusEnum.failed),
            ).where(AgentRun.workspace_id == workspace_id, AgentRun.started_at >= since, *conds)
        )
    ).one()
    return int(row[0] or 0), Decimal(str(row[1] or 0)), int(row[2] or 0)


async def _budget_count(db: AsyncSession, workspace_id: uuid.UUID, *conds: Any) -> int:
    return int(
        (
            await db.execute(
                select(func.count(Budget.id)).where(
                    Budget.workspace_id == workspace_id, Budget.is_active.is_(True), *conds
                )
            )
        ).scalar_one()
    )


def _run_items(runs: int, cost: Decimal, failed: int, href: str) -> list[ContextItem]:
    return [
        ContextItem(key="runs", label=f"Runs ({WINDOW_DAYS}d)", value=f"{runs:,}", href=href),
        ContextItem(key="spend", label=f"Spend ({WINDOW_DAYS}d)", value=_money(cost), href=href),
        ContextItem(key="failed", label="Failed runs", value=f"{failed:,}", href=href),
    ]


@router.get("/context", response_model=EntityContext)
async def get_entity_context(
    workspace: WorkspaceDep,
    db: DbDep,
    entity: Annotated[str, Query(pattern="^(" + "|".join(ENTITIES) + ")$")],
    id: Annotated[str | None, Query(max_length=255)] = None,  # noqa: A002
) -> EntityContext:
    ws = workspace.id
    if entity == "workspace":
        return await _workspace_context(db, workspace)
    if not id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "id is required")
    if entity == "workflow":
        return await _workflow_context(db, ws, id)
    try:
        entity_id = uuid.UUID(id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "id must be a UUID") from exc
    builders = {
        "api_key": _api_key_context,
        "route": _route_context,
        "budget": _budget_context,
        "prompt": _prompt_context,
    }
    return await builders[entity](db, ws, entity_id)


async def _workspace_context(db: AsyncSession, workspace: Workspace) -> EntityContext:
    ws = workspace.id
    runs, cost, failed = await _run_stats(db, ws)
    routes = int(
        (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(
                    GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)
                )
            )
        ).scalar_one()
    )
    rules = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws, GuardrailRule.status == "active"
                )
            )
        ).scalar_one()
    )
    keys = int(
        (
            await db.execute(
                select(func.count(ApiKey.id)).where(
                    ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)
                )
            )
        ).scalar_one()
    )
    return EntityContext(
        entity="workspace",
        id=str(ws),
        title=workspace.name,
        items=[
            *_run_items(runs, cost, failed, "/runs"),
            ContextItem(
                key="routes",
                label="Active gateway routes",
                value=str(routes),
                href="/gateway?tab=routes",
            ),
            ContextItem(
                key="budgets",
                label="Active budgets",
                value=str(await _budget_count(db, ws)),
                href="/budgets",
            ),
            ContextItem(
                key="guardrails",
                label="Active guardrail rules",
                value=str(rules),
                href="/guardrails",
            ),
            ContextItem(key="api_keys", label="Active API keys", value=str(keys), href="/api-keys"),
        ],
    )


async def _workflow_context(db: AsyncSession, ws: uuid.UUID, ref: str) -> EntityContext:
    """Workflow by id (``agent_runs.workflow_id``); a bare feature tag still works for
    tags that no workflow is linked to yet."""
    wf: WorkflowDefinition | None = None
    try:
        wf = await db.get(WorkflowDefinition, uuid.UUID(ref))
    except ValueError:
        wf = (
            (
                await db.execute(
                    select(WorkflowDefinition).where(
                        WorkflowDefinition.workspace_id == ws,
                        WorkflowDefinition.feature_tag == ref,
                        WorkflowDefinition.status != "archived",
                    )
                )
            )
            .scalars()
            .first()
        )
    if wf is not None and wf.workspace_id != ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    if wf is None:
        try:
            uuid.UUID(ref)
        except ValueError:
            pass
        else:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    tag = wf.feature_tag if wf is not None else ref
    run_cond = AgentRun.workflow_id == wf.id if wf is not None else AgentRun.feature_tag == ref
    runs, cost, failed = await _run_stats(db, ws, run_cond)
    budgets = (
        await _budget_count(db, ws, Budget.scope_type == "feature_tag", Budget.scope_id == tag)
        if tag
        else 0
    )
    success = f"{(runs - failed) / runs:.0%}" if runs else "—"
    href = f"/workflows/{wf.id}" if wf is not None else f"/runs?feature_tag={ref}"
    return EntityContext(
        entity="workflow",
        id=str(wf.id) if wf is not None else ref,
        title=wf.name if wf is not None else ref,
        items=[
            *_run_items(runs, cost, failed, href),
            ContextItem(key="success_rate", label="Success rate", value=success),
            ContextItem(
                key="cost_per_run",
                label="Cost per run",
                value=_money(cost / runs) if runs else "—",
            ),
            ContextItem(
                key="budgets",
                label="Budgets on this workflow",
                value=str(budgets),
                href=f"/budgets?scope_type=feature_tag&scope_id={tag}" if tag else "/budgets",
            ),
        ],
    )


async def _api_key_context(db: AsyncSession, ws: uuid.UUID, key_id: uuid.UUID) -> EntityContext:
    key = await db.get(ApiKey, key_id)
    if key is None or key.workspace_id != ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    runs, cost, failed = await _run_stats(db, ws, AgentRun.api_key_id == key_id)
    budgets = await _budget_count(
        db, ws, Budget.scope_type == "api_key", Budget.scope_id == str(key_id)
    )
    guardrails = (key.guardrail_config or {}).get("guardrail_ids") or []
    return EntityContext(
        entity="api_key",
        id=str(key_id),
        title=key.name or key.key_prefix,
        items=[
            *_run_items(runs, cost, failed, "/runs"),
            ContextItem(
                key="budgets", label="Budgets on this key", value=str(budgets), href="/budgets"
            ),
            ContextItem(key="scopes", label="Scopes", value=", ".join(key.scopes or []) or "all"),
            ContextItem(
                key="guardrails",
                label="Key guardrail set",
                value=str(len(guardrails)) if guardrails else "workspace default",
                href="/guardrails",
            ),
        ],
    )


async def _route_context(db: AsyncSession, ws: uuid.UUID, route_id: uuid.UUID) -> EntityContext:
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    since = datetime.now(UTC) - timedelta(days=WINDOW_DAYS)
    total, errors, blocked = (
        await db.execute(
            select(
                func.count(GatewayRequest.id),
                func.count(GatewayRequest.id).filter(GatewayRequest.status == "error"),
                func.count(GatewayRequest.id).filter(GatewayRequest.status == "blocked"),
            ).where(
                GatewayRequest.workspace_id == ws,
                GatewayRequest.route_id == route_id,
                GatewayRequest.created_at >= since,
            )
        )
    ).one()
    policies = int(
        (
            await db.execute(
                select(func.count(RoutingPolicy.id)).where(
                    RoutingPolicy.workspace_id == ws, RoutingPolicy.alias == route.alias
                )
            )
        ).scalar_one()
    )
    href = "/gateway?tab=routes"
    return EntityContext(
        entity="route",
        id=str(route_id),
        title=f"{route.alias} → {route.target_model}",
        items=[
            ContextItem(
                key="requests",
                label=f"Requests ({WINDOW_DAYS}d)",
                value=f"{int(total or 0):,}",
                href=href,
            ),
            ContextItem(key="errors", label="Errors", value=f"{int(errors or 0):,}", href=href),
            ContextItem(
                key="blocked",
                label="Guardrail blocks",
                value=f"{int(blocked or 0):,}",
                href="/guardrails/violations",
            ),
            ContextItem(
                key="policies",
                label="Routing policies on alias",
                value=str(policies),
                href="/gateway?tab=policies",
            ),
            ContextItem(
                key="caps",
                label="Cost caps",
                value=" / ".join(
                    part
                    for part in (
                        f"daily {_money(route.daily_cost_limit_usd)}"
                        if route.daily_cost_limit_usd is not None
                        else "",
                        f"monthly {_money(route.monthly_cost_limit_usd)}"
                        if route.monthly_cost_limit_usd is not None
                        else "",
                    )
                    if part
                )
                or "none",
            ),
        ],
    )


async def _budget_context(db: AsyncSession, ws: uuid.UUID, budget_id: uuid.UUID) -> EntityContext:
    budget = await db.get(Budget, budget_id)
    if budget is None or budget.workspace_id != ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget not found")
    try:
        spend = await get_budget_spend(await get_redis(), budget.id, budget.period_type)
    except Exception:  # noqa: BLE001 - context is best effort
        spend = Decimal(0)
    limit = Decimal(str(budget.limit_usd or 0))
    used = f"{spend / limit:.0%}" if limit > 0 else "—"
    return EntityContext(
        entity="budget",
        id=str(budget_id),
        title=f"{budget.scope_type}{':' + budget.scope_id if budget.scope_id else ''}",
        items=[
            ContextItem(
                key="spend",
                label=f"Spend this {budget.period_type}",
                value=_money(spend),
                href="/budgets",
            ),
            ContextItem(key="limit", label="Limit", value=_money(limit)),
            ContextItem(key="used", label="Used", value=used),
            ContextItem(key="action", label="On breach", value=budget.action),
        ],
    )


async def _prompt_context(db: AsyncSession, ws: uuid.UUID, prompt_id: uuid.UUID) -> EntityContext:
    prompt = await db.get(Prompt, prompt_id)
    if prompt is None or prompt.workspace_id != ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prompt not found")
    versions = int(
        (
            await db.execute(
                select(func.count(PromptVersion.id)).where(PromptVersion.prompt_id == prompt_id)
            )
        ).scalar_one()
    )
    return EntityContext(
        entity="prompt",
        id=str(prompt_id),
        title=prompt.name,
        items=[
            ContextItem(
                key="versions", label="Versions", value=str(versions), href=f"/prompts/{prompt_id}"
            ),
            ContextItem(
                key="environment",
                label="Default environment",
                value=str(prompt.default_environment),
            ),
        ],
    )
