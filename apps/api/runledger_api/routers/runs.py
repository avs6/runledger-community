from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_user, get_current_workspace
from runledger_api.models.events import (
    AgentRun,
    OutcomeEvent,
    ProviderCall,
    RunStatusEnum,
    Span,
    ToolCall,
)
from runledger_api.models.gateway import GatewayRequest, GatewayRoute
from runledger_api.models.tenant import Application, Tenant, TenantRoleEnum, TenantUser, Workspace
from runledger_api.schemas.runs import (
    GraphEdge,
    GraphNode,
    GraphNodeData,
    ProviderCallDetail,
    RunDetailResponse,
    RunFlowRecord,
    RunFlowResponse,
    RunGraphResponse,
    RunListItem,
    RunListResponse,
    SpanDetail,
    ToolCallDetail,
)

router = APIRouter(prefix="/runs", tags=["runs"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
UserDep = Annotated[Any, Depends(get_current_user)]

_ORG_FLOW_ROLES = {TenantRoleEnum.org_admin, TenantRoleEnum.org_manager}


def _duration_ms(started: datetime, ended: datetime | None) -> int | None:
    if ended is None:
        return None
    return int((ended - started).total_seconds() * 1000)


# ── List runs ─────────────────────────────────────────────────────────────────


def _apply_run_filters(
    stmt: Any,
    *,
    workspace_id: Any,
    status_filter: str | None,
    feature_tag: str | None,
    end_user_id: str | None,
    search: str | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    model_filter: str | None,
    min_cost: Decimal | None,
    max_cost: Decimal | None,
) -> Any:
    stmt = stmt.where(AgentRun.workspace_id == workspace_id)
    if status_filter:
        stmt = stmt.where(AgentRun.status == status_filter)
    if feature_tag:
        stmt = stmt.where(AgentRun.feature_tag == feature_tag)
    if end_user_id:
        stmt = stmt.where(AgentRun.end_user_id == end_user_id)
    if search:
        stmt = stmt.where(func.cast(AgentRun.id, sa.Text()).like(f"{search}%"))
    if from_dt:
        stmt = stmt.where(AgentRun.started_at >= from_dt)
    if to_dt:
        stmt = stmt.where(AgentRun.started_at <= to_dt)
    if model_filter:
        model_sub = (
            select(ProviderCall.run_id)
            .where(ProviderCall.model.ilike(f"%{model_filter}%"))
            .distinct()
        )
        stmt = stmt.where(AgentRun.id.in_(model_sub))
    if min_cost is not None:
        stmt = stmt.where(AgentRun.total_cost_usd >= min_cost)
    if max_cost is not None:
        stmt = stmt.where(AgentRun.total_cost_usd <= max_cost)
    return stmt


def _clean_label(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (bool, int, float)):
        return str(value)
    return fallback


def _metadata_value(metadata: dict[str, Any] | None, keys: list[str]) -> str | None:
    if not metadata:
        return None
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (bool, int, float)):
            return str(value)
    return None


def _provider_from_model(model: str | None) -> str:
    value = (model or "").lower()
    if "/" in value:
        return value.split("/", 1)[0]
    if "claude" in value:
        return "Anthropic"
    if "gpt" in value or value.startswith("o3") or value.startswith("o4"):
        return "OpenAI"
    if "gemini" in value:
        return "Google"
    if any(name in value for name in ("llama", "qwen", "deepseek", "mistral")):
        return "Local / Ollama"
    return "Provider unknown"


def _cost_band(cost: Decimal) -> str:
    if cost <= 0:
        return "No cost"
    if cost < Decimal("0.001"):
        return "< $0.001"
    if cost < Decimal("0.01"):
        return "$0.001 - $0.01"
    if cost < Decimal("0.10"):
        return "$0.01 - $0.10"
    return "$0.10+"


def _fallback_savings_category(
    *,
    cached_input_tokens: int,
    total_tokens: int,
    total_cost: Decimal,
    model: str | None,
    provider: str | None,
    gateway_request: GatewayRequest | None,
) -> tuple[Decimal, str | None, str | None]:
    if cached_input_tokens > 0 and total_tokens > cached_input_tokens and total_cost > 0:
        return (
            total_cost * Decimal(cached_input_tokens) / Decimal(total_tokens - cached_input_tokens),
            "cache_hits",
            "Cached input tokens avoided repeated prompt cost.",
        )
    if gateway_request is not None and gateway_request.cache_hit:
        return (
            max(total_cost, Decimal("0.000001")),
            "cache_hits",
            "Gateway cache hit avoided a fresh provider call.",
        )

    text = f"{model or ''} {provider or ''}".lower()
    if any(name in text for name in ("llama", "local", "ollama")) and total_cost > 0:
        return (
            total_cost * Decimal("0.25"),
            "local_models",
            "Local or self-hosted model lane reduced provider spend.",
        )
    return Decimal("0"), None, None


def _duration_or_latency(run: AgentRun, primary_call: ProviderCall | None) -> int | None:
    duration = _duration_ms(run.started_at, run.ended_at)
    if duration is not None:
        return duration
    return primary_call.latency_ms if primary_call is not None else None


async def _flow_workspace_ids(
    *,
    scope: str,
    workspace: Workspace,
    user: Any,
    db: AsyncSession,
) -> list[uuid.UUID]:
    if scope == "workspace":
        return [workspace.id]

    if user is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A dashboard user session is required for org or platform flow scope",
        )

    if scope == "org":
        if not user.is_platform_admin:
            tenant_user = (
                await db.execute(
                    select(TenantUser).where(
                        TenantUser.user_id == user.id,
                        TenantUser.tenant_id == workspace.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if tenant_user is None or tenant_user.role not in _ORG_FLOW_ROLES:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Organization admin access required for org flow scope",
                )
        result = await db.execute(select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id))
        return list(result.scalars().all())

    if scope == "platform":
        if not user.is_platform_admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Platform admin access required for platform flow scope",
            )
        result = await db.execute(select(Workspace.id))
        return list(result.scalars().all())

    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "scope must be workspace, org, or platform")


def _first_metadata(spans: list[Span], keys: list[str]) -> str | None:
    for span in spans:
        value = _metadata_value(span.span_metadata, keys)
        if value:
            return value
    return None


def _matching_gateway_request(
    run: AgentRun,
    primary_call: ProviderCall | None,
    gateway_requests: list[GatewayRequest],
) -> GatewayRequest | None:
    model = (primary_call.model if primary_call else None) or ""
    model_lower = model.lower()
    best: tuple[int, GatewayRequest] | None = None
    for request in gateway_requests:
        if request.workspace_id != run.workspace_id:
            continue
        request_model = (request.model_used or request.model_requested or "").lower()
        if model_lower and request_model != model_lower:
            continue
        distance = abs(int((request.created_at - run.started_at).total_seconds() * 1000))
        if distance > 5 * 60 * 1000:
            continue
        if best is None or distance < best[0]:
            best = (distance, request)
    return best[1] if best else None


@router.get("", response_model=RunListResponse)
async def list_runs(
    workspace: WorkspaceDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, description="ISO timestamp — return runs started before this"),
    status_filter: str | None = Query(None, alias="status"),
    feature_tag: str | None = Query(None),
    end_user_id: str | None = Query(None),
    search: str | None = Query(None, description="Prefix match on run_id"),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    model_filter: str | None = Query(
        None, alias="model", description="Substring match on model name"
    ),
    min_cost: Decimal | None = Query(None, description="Minimum total cost (USD)"),
    max_cost: Decimal | None = Query(None, description="Maximum total cost (USD)"),
) -> RunListResponse:
    # Total count query (without cursor/limit)
    count_stmt = _apply_run_filters(
        select(func.count()).select_from(AgentRun),
        workspace_id=workspace.id,
        status_filter=status_filter,
        feature_tag=feature_tag,
        end_user_id=end_user_id,
        search=search,
        from_dt=from_dt,
        to_dt=to_dt,
        model_filter=model_filter,
        min_cost=min_cost,
        max_cost=max_cost,
    )
    total = (await db.execute(count_stmt)).scalar_one()

    # Data query
    stmt = _apply_run_filters(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit + 1),
        workspace_id=workspace.id,
        status_filter=status_filter,
        feature_tag=feature_tag,
        end_user_id=end_user_id,
        search=search,
        from_dt=from_dt,
        to_dt=to_dt,
        model_filter=model_filter,
        min_cost=min_cost,
        max_cost=max_cost,
    )
    if cursor:
        cursor_dt = datetime.fromisoformat(cursor)
        stmt = stmt.where(AgentRun.started_at < cursor_dt)

    result = await db.execute(stmt)
    runs = list(result.scalars().all())

    # Determine next cursor
    has_more = len(runs) > limit
    if has_more:
        runs = runs[:limit]
    next_cursor = runs[-1].started_at.isoformat() if (has_more and runs) else None

    # Fetch primary model for each run (most expensive provider_call)
    run_ids = [r.id for r in runs]
    primary_models: dict[uuid.UUID, str | None] = {}
    if run_ids:
        pc_stmt = (
            select(ProviderCall.run_id, ProviderCall.model)
            .where(ProviderCall.run_id.in_(run_ids))
            .order_by(ProviderCall.run_id, ProviderCall.cost_usd.desc().nulls_last())
            .distinct(ProviderCall.run_id)
        )
        pc_result = await db.execute(pc_stmt)
        for row in pc_result.all():
            primary_models[row.run_id] = row.model

    items = [
        RunListItem(
            id=r.id,
            status=r.status,
            end_user_id=r.end_user_id,
            session_id=r.session_id,
            feature_tag=r.feature_tag,
            deployment_version=r.deployment_version,
            total_cost_usd=r.total_cost_usd,
            total_input_tokens=r.total_input_tokens,
            total_output_tokens=r.total_output_tokens,
            started_at=r.started_at,
            ended_at=r.ended_at,
            duration_ms=_duration_ms(r.started_at, r.ended_at),
            primary_model=primary_models.get(r.id),
        )
        for r in runs
    ]

    return RunListResponse(items=items, next_cursor=next_cursor, total=total)


# ── Export runs as CSV ────────────────────────────────────────────────────────


@router.get("/export", response_model=None)
async def export_runs(
    workspace: WorkspaceDep,
    db: DbDep,
    status_filter: str | None = Query(None, alias="status"),
    feature_tag: str | None = Query(None),
    end_user_id: str | None = Query(None),
    search: str | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    model_filter: str | None = Query(None, alias="model"),
    min_cost: Decimal | None = Query(None),
    max_cost: Decimal | None = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
) -> StreamingResponse:
    stmt = _apply_run_filters(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit),
        workspace_id=workspace.id,
        status_filter=status_filter,
        feature_tag=feature_tag,
        end_user_id=end_user_id,
        search=search,
        from_dt=from_dt,
        to_dt=to_dt,
        model_filter=model_filter,
        min_cost=min_cost,
        max_cost=max_cost,
    )
    result = await db.execute(stmt)
    runs = list(result.scalars().all())

    # Fetch primary models
    run_ids = [r.id for r in runs]
    primary_models: dict[uuid.UUID, str | None] = {}
    if run_ids:
        pc_stmt = (
            select(ProviderCall.run_id, ProviderCall.model)
            .where(ProviderCall.run_id.in_(run_ids))
            .order_by(ProviderCall.run_id, ProviderCall.cost_usd.desc().nulls_last())
            .distinct(ProviderCall.run_id)
        )
        for row in (await db.execute(pc_stmt)).all():
            primary_models[row.run_id] = row.model

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "run_id",
            "status",
            "feature_tag",
            "end_user_id",
            "session_id",
            "deployment_version",
            "model",
            "cost_usd",
            "input_tokens",
            "output_tokens",
            "duration_ms",
            "started_at",
            "ended_at",
        ],
    )
    writer.writeheader()
    for r in runs:
        writer.writerow(
            {
                "run_id": str(r.id),
                "status": r.status,
                "feature_tag": r.feature_tag or "",
                "end_user_id": r.end_user_id or "",
                "session_id": r.session_id or "",
                "deployment_version": r.deployment_version or "",
                "model": primary_models.get(r.id) or "",
                "cost_usd": str(r.total_cost_usd) if r.total_cost_usd is not None else "",
                "input_tokens": r.total_input_tokens or "",
                "output_tokens": r.total_output_tokens or "",
                "duration_ms": _duration_ms(r.started_at, r.ended_at) or "",
                "started_at": r.started_at.isoformat(),
                "ended_at": r.ended_at.isoformat() if r.ended_at else "",
            }
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=runs.csv"},
    )


# ── Request flow aggregate ────────────────────────────────────────────────────


@router.get("/flow", response_model=RunFlowResponse)
async def get_run_flow(
    workspace: WorkspaceDep,
    user: UserDep,
    db: DbDep,
    scope: str = Query("workspace", pattern="^(workspace|org|platform)$"),
    mode: str = Query("request-intent-model-result"),
    metric: str = Query("requests", pattern="^(requests|cost|tokens|savings)$"),
    limit: int = Query(500, ge=1, le=1000),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
) -> RunFlowResponse:
    """
    Safe request-flow records for Sankey dashboards.

    This endpoint returns labels and metrics only. It avoids returning captured
    prompt/response payloads so org/platform flow views do not broaden sensitive
    content access.
    """
    workspace_ids = await _flow_workspace_ids(scope=scope, workspace=workspace, user=user, db=db)
    if not workspace_ids:
        return RunFlowResponse(
            scope=scope,
            mode=mode,
            metric=metric,
            sampled_runs=0,
            total_runs=0,
            workspace_count=0,
            generated_at=datetime.now(UTC),
            items=[],
        )

    filters = [AgentRun.workspace_id.in_(workspace_ids)]
    if from_dt is not None:
        filters.append(AgentRun.started_at >= from_dt)
    if to_dt is not None:
        filters.append(AgentRun.started_at <= to_dt)

    total_runs = (
        await db.execute(select(func.count()).select_from(AgentRun).where(*filters))
    ).scalar_one()

    run_rows = list(
        (
            await db.execute(
                select(
                    AgentRun,
                    Workspace.name.label("workspace_name"),
                    Workspace.tenant_id.label("tenant_id"),
                    Tenant.name.label("tenant_name"),
                    Application.name.label("application_name"),
                )
                .join(Workspace, Workspace.id == AgentRun.workspace_id)
                .join(Tenant, Tenant.id == Workspace.tenant_id)
                .outerjoin(Application, Application.id == AgentRun.application_id)
                .where(*filters)
                .order_by(AgentRun.started_at.desc())
                .limit(limit)
            )
        ).all()
    )
    runs = [row.AgentRun for row in run_rows]
    run_ids = [run.id for run in runs]

    primary_calls: dict[uuid.UUID, ProviderCall] = {}
    spans_by_run: dict[uuid.UUID, list[Span]] = {run_id: [] for run_id in run_ids}
    tools_by_run: dict[uuid.UUID, list[ToolCall]] = {run_id: [] for run_id in run_ids}
    outcomes_by_run: dict[uuid.UUID, OutcomeEvent] = {}
    gateway_requests: list[GatewayRequest] = []
    gateway_routes: dict[uuid.UUID, GatewayRoute] = {}

    if run_ids:
        provider_calls = list(
            (
                await db.execute(
                    select(ProviderCall)
                    .where(ProviderCall.run_id.in_(run_ids))
                    .order_by(
                        ProviderCall.run_id,
                        ProviderCall.cost_usd.desc().nulls_last(),
                        ProviderCall.created_at,
                    )
                )
            )
            .scalars()
            .all()
        )
        for call in provider_calls:
            primary_calls.setdefault(call.run_id, call)

        for span in (
            await db.execute(select(Span).where(Span.run_id.in_(run_ids)).order_by(Span.started_at))
        ).scalars():
            spans_by_run.setdefault(span.run_id, []).append(span)

        for tool in (
            await db.execute(
                select(ToolCall).where(ToolCall.run_id.in_(run_ids)).order_by(ToolCall.created_at)
            )
        ).scalars():
            tools_by_run.setdefault(tool.run_id, []).append(tool)

        for outcome in (
            await db.execute(
                select(OutcomeEvent)
                .where(OutcomeEvent.run_id.in_(run_ids))
                .order_by(OutcomeEvent.created_at.desc())
            )
        ).scalars():
            outcomes_by_run.setdefault(outcome.run_id, outcome)

        min_started = min(run.started_at for run in runs) - timedelta(minutes=5)
        max_started = max(run.started_at for run in runs) + timedelta(minutes=5)
        gateway_requests = list(
            (
                await db.execute(
                    select(GatewayRequest)
                    .where(
                        GatewayRequest.workspace_id.in_(workspace_ids),
                        GatewayRequest.created_at >= min_started,
                        GatewayRequest.created_at <= max_started,
                    )
                    .order_by(GatewayRequest.created_at.desc())
                    .limit(limit * 2)
                )
            )
            .scalars()
            .all()
        )
        route_ids = [request.route_id for request in gateway_requests if request.route_id is not None]
        if route_ids:
            gateway_routes = {
                route.id: route
                for route in (
                    await db.execute(select(GatewayRoute).where(GatewayRoute.id.in_(route_ids)))
                ).scalars()
            }

    row_by_run_id = {row.AgentRun.id: row for row in run_rows}
    items: list[RunFlowRecord] = []
    for run in runs:
        row = row_by_run_id[run.id]
        spans = spans_by_run.get(run.id, [])
        tools = tools_by_run.get(run.id, [])
        primary_call = primary_calls.get(run.id)
        outcome = outcomes_by_run.get(run.id)
        gateway_request = _matching_gateway_request(run, primary_call, gateway_requests)
        route = (
            gateway_routes.get(gateway_request.route_id)
            if gateway_request is not None and gateway_request.route_id is not None
            else None
        )
        metadata = run.run_metadata or {}
        resource_metadata = run.resource_attributes or {}

        input_tokens = run.total_input_tokens
        if input_tokens is None and primary_call is not None:
            input_tokens = primary_call.input_tokens
        output_tokens = run.total_output_tokens
        if output_tokens is None and primary_call is not None:
            output_tokens = primary_call.output_tokens
        input_tokens = input_tokens or 0
        output_tokens = output_tokens or 0
        cached_input_tokens = primary_call.cached_input_tokens if primary_call else None
        cached_input_tokens = cached_input_tokens or (
            gateway_request.input_tokens if gateway_request is not None and gateway_request.cache_hit else 0
        )
        agent_name = (
            _metadata_value(metadata, ["agent_name", "agent", "agent_client", "selected_agent"])
            or _metadata_value(resource_metadata, ["agent_name", "agent", "agent_client", "service.name"])
            or _first_metadata(spans, ["agent_name", "agent", "agent_client", "selected_agent", "workflow_agent"])
            or next((span.name for span in spans if span.span_type == "agent"), None)
        )
        skill_name = (
            _metadata_value(metadata, ["skill", "skill_name", "selected_skill", "runledger.skill"])
            or _first_metadata(spans, ["skill", "skill_name", "selected_skill", "runledger.skill"])
        )
        team = (
            _metadata_value(metadata, ["team", "department", "cost_center"])
            or _metadata_value(resource_metadata, ["team", "department", "cost_center"])
            or _first_metadata(spans, ["team", "department", "cost_center"])
        )
        app_name = (
            row.application_name
            or _metadata_value(metadata, ["application", "app", "service"])
            or _metadata_value(resource_metadata, ["application", "app", "service.name", "service"])
            or _first_metadata(spans, ["application", "app", "service.name", "service"])
        )
        prompt = (
            "Prompt captured"
            if any(span.span_metadata and "messages" in span.span_metadata for span in spans)
            else run.feature_tag
        )
        provider = (
            primary_call.provider
            if primary_call is not None
            else _provider_from_model(gateway_request.model_used if gateway_request else None)
        )
        model = primary_call.model if primary_call is not None else (gateway_request.model_used if gateway_request else None)
        total_cost = run.total_cost_usd or Decimal("0")
        total_tokens = input_tokens + output_tokens
        savings = primary_call.savings_usd if primary_call is not None and primary_call.savings_usd is not None else Decimal("0")
        savings_category = primary_call.savings_category if primary_call is not None else None
        savings_reason = primary_call.savings_reason if primary_call is not None else None
        if savings <= 0:
            savings, savings_category, savings_reason = _fallback_savings_category(
                cached_input_tokens=cached_input_tokens,
                total_tokens=total_tokens,
                total_cost=total_cost,
                model=model,
                provider=provider,
                gateway_request=gateway_request,
            )
        elif not savings_category:
            text = f"{model or ''} {provider or ''}".lower()
            savings_category = (
                "local_models"
                if any(name in text for name in ("llama", "local", "ollama"))
                else "smart_routing"
            )
            savings_reason = savings_reason or "RunLedger recorded realized savings for this provider call."
        route_label = (
            route.alias
            if route is not None
            else (gateway_request.model_requested if gateway_request is not None else "Direct SDK / OTLP")
        )

        items.append(
            RunFlowRecord(
                id=run.id,
                workspace_id=run.workspace_id,
                workspace_name=row.workspace_name,
                tenant_id=row.tenant_id,
                tenant_name=row.tenant_name,
                status=run.status,
                end_user_id=run.end_user_id,
                feature_tag=run.feature_tag,
                primary_model=model,
                provider=provider,
                route=route_label,
                outcome=(
                    f"{outcome.event_type}: {'Success' if outcome.success else 'Miss'}"
                    if outcome is not None
                    else str(run.status)
                ),
                prompt=_clean_label(prompt, "Prompt metadata only"),
                skill=_clean_label(skill_name, "No skill captured"),
                agent=_clean_label(agent_name, _clean_label(run.feature_tag, "Agent unknown")),
                tool=_clean_label(tools[0].tool_name if tools else None, "No tool called"),
                team=_clean_label(team, "Team unknown"),
                application=_clean_label(app_name, "App unknown"),
                cost_band=_cost_band(total_cost),
                total_cost_usd=total_cost,
                total_input_tokens=input_tokens,
                total_output_tokens=output_tokens,
                cached_input_tokens=cached_input_tokens,
                latency_ms=_duration_or_latency(run, primary_call),
                success=(outcome.success if outcome is not None else run.status == RunStatusEnum.succeeded),
                savings_usd=savings,
                savings_category=savings_category,
                savings_reason=savings_reason,
                started_at=run.started_at,
            )
        )

    return RunFlowResponse(
        scope=scope,
        mode=mode,
        metric=metric,
        sampled_runs=len(items),
        total_runs=total_runs,
        workspace_count=len(set(workspace_ids)),
        generated_at=datetime.now(UTC),
        items=items,
    )


# ── Cancel a stuck run ────────────────────────────────────────────────────────


@router.patch("/{run_id}/cancel", response_model=RunListItem)
async def cancel_run(
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> RunListItem:
    """Mark a running run as cancelled (useful when a script crashes mid-run)."""
    run = await db.get(AgentRun, run_id)
    if run is None or run.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    if run.status != "running":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Run is in '{run.status}' state, only 'running' runs can be cancelled",
        )

    run.status = RunStatusEnum.cancelled
    run.ended_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(run)

    return RunListItem(
        id=run.id,
        status=run.status,
        end_user_id=run.end_user_id,
        session_id=run.session_id,
        feature_tag=run.feature_tag,
        deployment_version=run.deployment_version,
        total_cost_usd=run.total_cost_usd,
        total_input_tokens=run.total_input_tokens,
        total_output_tokens=run.total_output_tokens,
        started_at=run.started_at,
        ended_at=run.ended_at,
        duration_ms=_duration_ms(run.started_at, run.ended_at),
        primary_model=None,
    )


# ── Run detail ────────────────────────────────────────────────────────────────


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> RunDetailResponse:
    run = await db.get(AgentRun, run_id)
    if run is None or run.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")

    spans_result = await db.execute(
        select(Span).where(Span.run_id == run_id).order_by(Span.started_at)
    )
    spans = list(spans_result.scalars().all())

    pc_result = await db.execute(
        select(ProviderCall).where(ProviderCall.run_id == run_id).order_by(ProviderCall.created_at)
    )
    provider_calls = list(pc_result.scalars().all())

    tc_result = await db.execute(
        select(ToolCall).where(ToolCall.run_id == run_id).order_by(ToolCall.created_at)
    )
    tool_calls = list(tc_result.scalars().all())

    # Extract payloads from span metadata (only present when capture policy is SAMPLED/FULL)
    input_payload: list[dict[str, Any]] | None = None
    output_payload: Any | None = None
    span_payloads: dict[str, dict[str, Any]] = {}
    for s in spans:
        if s.span_metadata:
            span_payload: dict[str, Any] = {}
            if "messages" in s.span_metadata:
                span_payload["input"] = s.span_metadata["messages"]
                if input_payload is None:
                    input_payload = s.span_metadata["messages"]
            if "response" in s.span_metadata:
                span_payload["output"] = s.span_metadata["response"]
                if output_payload is None:
                    output_payload = s.span_metadata["response"]
            if span_payload:
                span_payloads[str(s.id)] = span_payload

    return RunDetailResponse(
        id=run.id,
        status=run.status,
        end_user_id=run.end_user_id,
        session_id=run.session_id,
        feature_tag=run.feature_tag,
        deployment_version=run.deployment_version,
        total_cost_usd=run.total_cost_usd,
        total_input_tokens=run.total_input_tokens,
        total_output_tokens=run.total_output_tokens,
        started_at=run.started_at,
        ended_at=run.ended_at,
        duration_ms=_duration_ms(run.started_at, run.ended_at),
        input_payload=input_payload,
        output_payload=output_payload,
        span_payloads=span_payloads if span_payloads else None,
        spans=[
            SpanDetail(
                id=s.id,
                run_id=s.run_id,
                parent_span_id=s.parent_span_id,
                span_type=s.span_type,
                name=s.name,
                started_at=s.started_at,
                ended_at=s.ended_at,
                status=s.status,
                cost_usd=s.cost_usd,
                metadata=s.span_metadata,
            )
            for s in spans
        ],
        provider_calls=[
            ProviderCallDetail(
                id=pc.id,
                span_id=pc.span_id,
                run_id=pc.run_id,
                provider=pc.provider,
                model=pc.model,
                input_tokens=pc.input_tokens,
                output_tokens=pc.output_tokens,
                cached_input_tokens=pc.cached_input_tokens,
                latency_ms=pc.latency_ms,
                cost_usd=pc.cost_usd,
                status=pc.status,
                error_type=pc.error_type,
                created_at=pc.created_at,
            )
            for pc in provider_calls
        ],
        tool_calls=[
            ToolCallDetail(
                id=tc.id,
                span_id=tc.span_id,
                run_id=tc.run_id,
                tool_name=tc.tool_name,
                tool_type=tc.tool_type,
                risk_score=tc.risk_score,
                duration_ms=tc.duration_ms,
                status=tc.status,
                created_at=tc.created_at,
            )
            for tc in tool_calls
        ],
    )


# ── Run graph (DAG) ───────────────────────────────────────────────────────────


@router.get("/{run_id}/graph", response_model=RunGraphResponse)
async def get_run_graph(
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> RunGraphResponse:
    run = await db.get(AgentRun, run_id)
    if run is None or run.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")

    spans_result = await db.execute(
        select(Span).where(Span.run_id == run_id).order_by(Span.started_at)
    )
    spans = list(spans_result.scalars().all())

    # Build a map of span_id → provider_call for enriching LLM nodes
    pc_result = await db.execute(select(ProviderCall).where(ProviderCall.run_id == run_id))
    pc_by_span: dict[str, ProviderCall] = {}
    for row_pc in pc_result.scalars().all():
        if row_pc.span_id:
            pc_by_span[str(row_pc.span_id)] = row_pc

    # Build nodes
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # Virtual root node representing the run itself
    root_id = f"run-{run_id}"
    nodes.append(
        GraphNode(
            id=root_id,
            label=f"Run ({run.feature_tag or 'unnamed'})",
            data=GraphNodeData(
                span_type="run",
                status=run.status,
                cost_usd=run.total_cost_usd,
                input_tokens=run.total_input_tokens,
                output_tokens=run.total_output_tokens,
                latency_ms=_duration_ms(run.started_at, run.ended_at),
                model=None,
                provider=None,
                error_type=None,
                started_at=run.started_at,
                ended_at=run.ended_at,
                duration_ms=_duration_ms(run.started_at, run.ended_at),
                metadata=None,
            ),
        )
    )

    for span in spans:
        span_node_id = str(span.id)
        span_pc: ProviderCall | None = pc_by_span.get(span_node_id)

        nodes.append(
            GraphNode(
                id=span_node_id,
                label=span.name,
                data=GraphNodeData(
                    span_type=span.span_type,
                    status=span.status,
                    cost_usd=span.cost_usd,
                    input_tokens=span_pc.input_tokens if span_pc else None,
                    output_tokens=span_pc.output_tokens if span_pc else None,
                    latency_ms=span_pc.latency_ms if span_pc else None,
                    model=span_pc.model if span_pc else None,
                    provider=span_pc.provider if span_pc else None,
                    error_type=span_pc.error_type if span_pc else None,
                    started_at=span.started_at,
                    ended_at=span.ended_at,
                    duration_ms=_duration_ms(span.started_at, span.ended_at),
                    metadata=span.span_metadata,
                ),
            )
        )

        # Edge: parent → this span (or run root if no parent)
        source = str(span.parent_span_id) if span.parent_span_id else root_id
        edges.append(
            GraphEdge(
                id=f"e-{source}-{span_node_id}",
                source=source,
                target=span_node_id,
            )
        )

    return RunGraphResponse(run_id=run_id, nodes=nodes, edges=edges)
