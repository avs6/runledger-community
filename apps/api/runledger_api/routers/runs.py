from __future__ import annotations

import asyncio
import csv
import io
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_user,
    get_current_workspace,
    require_user,
    require_workspace_writer,
)
from runledger_api.models.alerts import AlertFiring, AlertRule
from runledger_api.models.approvals import Approval
from runledger_api.models.audit import AuditEvent
from runledger_api.models.events import (
    AgentRun,
    ProviderCall,
    RunbookEntry,
    RunStatusEnum,
    Span,
    ToolCall,
)
from runledger_api.models.gateway import GatewayRequest, GatewayRoute
from runledger_api.models.ledger import CapturePolicy, SecurityEvent, ToolRegistry
from runledger_api.models.outcomes import Outcome
from runledger_api.models.saved_views import SAVED_VIEW_PAGES, SavedView
from runledger_api.models.tags import Tag
from runledger_api.models.tenant import Application, Tenant, User, Workspace
from runledger_api.models.tool_policies import ToolPolicy
from runledger_api.schemas.runs import (
    GovernanceAlertEvidence,
    GovernanceAuditEvidence,
    GovernanceSecurityEvidence,
    GovernanceToolEvidence,
    GraphEdge,
    GraphNode,
    GraphNodeData,
    ProviderCallDetail,
    RunbookList,
    RunbookResponse,
    RunCompareResponse,
    RunCompareSide,
    RunDetailResponse,
    RunFacetsResponse,
    RunFlowRecord,
    RunFlowResponse,
    RunGovernanceContextResponse,
    RunGraphResponse,
    RunListItem,
    RunListResponse,
    RunStatsResponse,
    SavedViewCreate,
    SavedViewList,
    SavedViewResponse,
    SpanDetail,
    ToolCallDetail,
)
from runledger_api.services.observe import (
    RUN_STATUSES,
    AccessGroupFilters,
    can_view_payloads,
    cursor_clause,
    encode_cursor,
    normalize_run_status,
    resolve_access_group,
    resolve_scope_workspace_ids,
    run_access_clauses,
)
from runledger_api.services.runbooks import generate_runbook

router = APIRouter(prefix="/runs", tags=["runs"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
UserDep = Annotated[Any, Depends(get_current_user)]

_PAYLOAD_KEYS = ("messages", "response")


@dataclass
class _RunOutcome:
    outcome_type: str
    success: bool


def strip_payloads(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Span metadata without captured prompts/responses (they live in span_payloads)."""
    if not metadata:
        return metadata
    return {k: v for k, v in metadata.items() if k not in _PAYLOAD_KEYS}


def _duration_ms(started: datetime, ended: datetime | None) -> int | None:
    if ended is None:
        return None
    return int((ended - started).total_seconds() * 1000)


async def _resolve_access_group_observe_filters(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    access_group_id: uuid.UUID,
) -> AccessGroupFilters:
    filters = await resolve_access_group(db, workspace_id, access_group_id)
    assert filters is not None
    return filters


def _run_lookup(
    run_id: uuid.UUID, workspace_id: uuid.UUID, access: AccessGroupFilters | None
) -> Any:
    """SELECT for one run, honouring an access group (shared by detail/graph/governance)."""
    return select(AgentRun).where(
        AgentRun.id == run_id,
        AgentRun.workspace_id == workspace_id,
        *run_access_clauses(access, [workspace_id]),
    )


# ── List runs ─────────────────────────────────────────────────────────────────


def _apply_run_filters(
    stmt: Any,
    *,
    workspace_id: Any,
    access_group_filters: AccessGroupFilters | None,
    status_filter: str | None,
    feature_tag: str | None,
    end_user_id: str | None,
    search: str | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    model_filter: str | None,
    min_cost: Decimal | None,
    max_cost: Decimal | None,
    api_key_id: uuid.UUID | None = None,
    tag: str | None = None,
    tool_name: str | None = None,
    security_event_only: bool = False,
) -> Any:
    stmt = stmt.where(
        AgentRun.workspace_id == workspace_id,
        *run_access_clauses(access_group_filters, [workspace_id]),
    )
    run_status = normalize_run_status(status_filter)
    if run_status:
        stmt = stmt.where(AgentRun.status == run_status)
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
            .where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.model.ilike(f"%{model_filter}%"),
            )
            .distinct()
        )
        stmt = stmt.where(AgentRun.id.in_(model_sub))
    if min_cost is not None:
        stmt = stmt.where(AgentRun.total_cost_usd >= min_cost)
    if max_cost is not None:
        stmt = stmt.where(AgentRun.total_cost_usd <= max_cost)
    if api_key_id:
        stmt = stmt.where(AgentRun.api_key_id == api_key_id)
    if tag or tool_name or security_event_only:
        stmt = stmt.where(
            AgentRun.id.in_(
                _governance_run_subquery(
                    workspace_id=workspace_id,
                    tag=tag,
                    tool_name=tool_name,
                    security_event_only=security_event_only,
                )
            )
        )
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


def _metadata_tags(run: AgentRun) -> list[str]:
    tags: list[str] = []
    raw = (run.run_metadata or {}).get("tags")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                tags.append(item.strip())
    if run.feature_tag and run.feature_tag not in tags:
        tags.append(run.feature_tag)
    return tags


def _governance_run_subquery(
    *,
    workspace_id: uuid.UUID,
    tag: str | None = None,
    tool_name: str | None = None,
    security_event_only: bool = False,
) -> Any:
    run_stmt = select(AgentRun.id).where(AgentRun.workspace_id == workspace_id)
    if tag:
        pattern = f'%"{tag}"%'
        run_stmt = run_stmt.where(
            sa.or_(
                AgentRun.feature_tag == tag,
                sa.cast(AgentRun.run_metadata, sa.Text).ilike(pattern),
            )
        )
    if tool_name:
        run_stmt = run_stmt.where(
            AgentRun.id.in_(
                select(ToolCall.run_id)
                .where(
                    ToolCall.workspace_id == workspace_id,
                    ToolCall.tool_name == tool_name,
                )
                .distinct()
            )
        )
    if security_event_only:
        run_stmt = run_stmt.where(
            AgentRun.id.in_(
                select(SecurityEvent.run_id)
                .where(
                    SecurityEvent.workspace_id == workspace_id,
                    SecurityEvent.run_id.is_not(None),
                )
                .distinct()
            )
        )
    return run_stmt.distinct()


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
    return await resolve_scope_workspace_ids(scope, workspace, user, db)


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


@dataclass
class RunFilterParams:
    """The one run filter list, shared by list, export, stats and stream (review O-11)."""

    status: str | None
    feature_tag: str | None
    end_user_id: str | None
    search: str | None
    from_dt: datetime | None
    to_dt: datetime | None
    model: str | None
    min_cost: Decimal | None
    max_cost: Decimal | None
    access_group_id: uuid.UUID | None
    api_key_id: uuid.UUID | None
    tag: str | None
    tool_name: str | None
    security_event_only: bool


def run_filter_params(
    status_filter: str | None = Query(
        None, alias="status", description="running, succeeded, failed or cancelled"
    ),
    feature_tag: str | None = Query(None),
    end_user_id: str | None = Query(None),
    search: str | None = Query(None, description="Prefix match on run_id"),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    model_filter: str | None = Query(None, alias="model", description="Substring of model"),
    min_cost: Decimal | None = Query(None, description="Minimum total cost (USD)"),
    max_cost: Decimal | None = Query(None, description="Maximum total cost (USD)"),
    access_group_id: uuid.UUID | None = Query(None),
    api_key_id: uuid.UUID | None = Query(None),
    tag: str | None = Query(None, description="Governance or request tag"),
    tool_name: str | None = Query(None, description="Runs that called this tool"),
    security_event_only: bool = Query(False, description="Only runs with security events"),
) -> RunFilterParams:
    normalize_run_status(status_filter)  # 422 on an unknown status (review O-10)
    return RunFilterParams(
        status=status_filter,
        feature_tag=feature_tag,
        end_user_id=end_user_id,
        search=search,
        from_dt=from_dt,
        to_dt=to_dt,
        model=model_filter,
        min_cost=min_cost,
        max_cost=max_cost,
        access_group_id=access_group_id,
        api_key_id=api_key_id,
        tag=tag,
        tool_name=tool_name,
        security_event_only=security_event_only,
    )


RunFiltersDep = Annotated[RunFilterParams, Depends(run_filter_params)]


async def _filtered(stmt: Any, f: RunFilterParams, workspace: Workspace, db: AsyncSession) -> Any:
    access = await resolve_access_group(db, workspace.id, f.access_group_id)
    return _apply_run_filters(
        stmt,
        workspace_id=workspace.id,
        access_group_filters=access,
        status_filter=f.status,
        feature_tag=f.feature_tag,
        end_user_id=f.end_user_id,
        search=f.search,
        from_dt=f.from_dt,
        to_dt=f.to_dt,
        model_filter=f.model,
        min_cost=f.min_cost,
        max_cost=f.max_cost,
        api_key_id=f.api_key_id,
        tag=f.tag,
        tool_name=f.tool_name,
        security_event_only=f.security_event_only,
    )


async def _primary_models(
    db: AsyncSession, run_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    """Most expensive provider call's model per run."""
    if not run_ids:
        return {}
    rows = await db.execute(
        select(ProviderCall.run_id, ProviderCall.model)
        .where(ProviderCall.run_id.in_(run_ids))
        .order_by(ProviderCall.run_id, ProviderCall.cost_usd.desc().nulls_last())
        .distinct(ProviderCall.run_id)
    )
    return {row.run_id: row.model for row in rows.all()}


def _list_item(r: AgentRun, primary_model: str | None) -> RunListItem:
    return RunListItem(
        id=r.id,
        api_key_id=r.api_key_id,
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
        primary_model=primary_model,
    )


@router.get("", response_model=RunListResponse)
async def list_runs(
    workspace: WorkspaceDep,
    db: DbDep,
    filters: RunFiltersDep,
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, description="Opaque cursor from next_cursor"),
    include_total: bool = Query(
        True, description="Set false to skip the COUNT (live views, deep paging)"
    ),
) -> RunListResponse:
    """Runs, newest first, keyset-paged on (started_at, id) so ties are never skipped."""
    total: int | None = None
    if include_total:
        count_stmt = await _filtered(
            select(func.count()).select_from(AgentRun), filters, workspace, db
        )
        total = int((await db.execute(count_stmt)).scalar_one())
        response.headers["X-Total-Count"] = str(total)

    stmt = await _filtered(
        select(AgentRun).order_by(AgentRun.started_at.desc(), AgentRun.id.desc()).limit(limit + 1),
        filters,
        workspace,
        db,
    )
    if cursor:
        stmt = stmt.where(cursor_clause(cursor))
    runs = list((await db.execute(stmt)).scalars().all())
    has_more = len(runs) > limit
    runs = runs[:limit]
    next_cursor = encode_cursor(runs[-1].started_at, runs[-1].id) if (has_more and runs) else None
    models = await _primary_models(db, [r.id for r in runs])
    return RunListResponse(
        items=[_list_item(r, models.get(r.id)) for r in runs],
        next_cursor=next_cursor,
        total=total,
    )


# ── Aggregates for the Runs hero (review O-20) ────────────────────────────────


@router.get("/stats", response_model=RunStatsResponse)
async def run_stats(workspace: WorkspaceDep, db: DbDep, filters: RunFiltersDep) -> RunStatsResponse:
    """Server-side aggregates over every run matching the filters, not a page sample."""
    duration = sa.extract("epoch", AgentRun.ended_at - AgentRun.started_at) * 1000
    stmt = await _filtered(
        select(
            func.count(AgentRun.id).label("total"),
            func.count(case((AgentRun.status == RunStatusEnum.succeeded, 1))).label("succeeded"),
            func.count(case((AgentRun.status == RunStatusEnum.failed, 1))).label("failed"),
            func.count(case((AgentRun.status == RunStatusEnum.running, 1))).label("running"),
            func.count(case((AgentRun.status == RunStatusEnum.cancelled, 1))).label("cancelled"),
            func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost"),
            func.coalesce(func.sum(AgentRun.total_input_tokens), 0).label("inp"),
            func.coalesce(func.sum(AgentRun.total_output_tokens), 0).label("out"),
            func.avg(duration).label("avg_ms"),
            func.percentile_cont(0.95).within_group(duration).label("p95_ms"),
        ),
        filters,
        workspace,
        db,
    )
    row = (await db.execute(stmt)).one()
    finished = int(row.succeeded) + int(row.failed)
    return RunStatsResponse(
        total=int(row.total),
        succeeded=int(row.succeeded),
        failed=int(row.failed),
        running=int(row.running),
        cancelled=int(row.cancelled),
        success_rate=(Decimal(int(row.succeeded)) / Decimal(finished)).quantize(Decimal("0.0001"))
        if finished
        else None,
        total_cost_usd=Decimal(row.cost or 0),
        avg_cost_usd=(Decimal(row.cost or 0) / int(row.total)) if row.total else None,
        total_input_tokens=int(row.inp),
        total_output_tokens=int(row.out),
        avg_duration_ms=int(row.avg_ms) if row.avg_ms is not None else None,
        p95_duration_ms=int(row.p95_ms) if row.p95_ms is not None else None,
    )


# ── Filter facets (review O-24) ───────────────────────────────────────────────


@router.get("/facets", response_model=RunFacetsResponse)
async def run_facets(
    workspace: WorkspaceDep,
    db: DbDep,
    days: int = Query(30, ge=1, le=365),
) -> RunFacetsResponse:
    """Distinct models, providers, workflows (feature tags) and statuses seen recently."""
    since = datetime.now(UTC) - timedelta(days=days)

    async def _distinct(col: Any, created: Any, ws_col: Any) -> list[str]:
        rows = await db.execute(
            select(col)
            .where(ws_col == workspace.id, created >= since, col.is_not(None))
            .group_by(col)
            .order_by(func.count().desc())
            .limit(200)
        )
        return [str(v) for v in rows.scalars().all() if v]

    return RunFacetsResponse(
        models=await _distinct(
            ProviderCall.model, ProviderCall.created_at, ProviderCall.workspace_id
        ),
        providers=await _distinct(
            ProviderCall.provider, ProviderCall.created_at, ProviderCall.workspace_id
        ),
        feature_tags=await _distinct(
            AgentRun.feature_tag, AgentRun.started_at, AgentRun.workspace_id
        ),
        statuses=list(RUN_STATUSES),
    )


# ── Live stream over SSE (review O-07) ────────────────────────────────────────

_STREAM_POLL_SECONDS = 2.0
_STREAM_MAX_SECONDS = 300.0


@router.get("/stream", response_model=None)
async def stream_runs(
    request: Request,
    workspace: WorkspaceDep,
    filters: RunFiltersDep,
    since: datetime | None = Query(None, description="Only runs started after this instant"),
    max_seconds: float = Query(_STREAM_MAX_SECONDS, ge=1, le=_STREAM_MAX_SECONDS),
) -> StreamingResponse:
    """Server-sent events with new and updated runs.

    The server checks a small keyset window (no COUNT) every two seconds and emits
    ``run`` events for runs that are new or whose status changed. The browser closes
    the stream when the tab is hidden and reopens it with ``since`` when it returns.
    Streams end after ``max_seconds``; EventSource reconnects on its own.
    """
    from runledger_api.core.db import AsyncSessionLocal  # noqa: PLC0415

    start_from = since or datetime.now(UTC) - timedelta(minutes=5)

    async def _events() -> AsyncIterator[str]:
        seen: dict[uuid.UUID, str] = {}
        deadline = asyncio.get_running_loop().time() + max_seconds
        yield "retry: 3000\n\n"
        while asyncio.get_running_loop().time() < deadline:
            if await request.is_disconnected():
                return
            async with AsyncSessionLocal() as session:
                stmt = await _filtered(
                    select(AgentRun)
                    .where(AgentRun.started_at >= start_from)
                    .order_by(AgentRun.started_at.desc(), AgentRun.id.desc())
                    .limit(100),
                    filters,
                    workspace,
                    session,
                )
                runs = list((await session.execute(stmt)).scalars().all())
                changed = [r for r in reversed(runs) if seen.get(r.id) != str(r.status)]
                models = await _primary_models(session, [r.id for r in changed])
            for r in changed:
                seen[r.id] = str(r.status)
                payload = _list_item(r, models.get(r.id)).model_dump_json()
                yield f"event: run\nid: {r.id}\ndata: {payload}\n\n"
            yield ": keep-alive\n\n"
            await asyncio.sleep(_STREAM_POLL_SECONDS)

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Export runs as CSV ────────────────────────────────────────────────────────


@router.get("/export", response_model=None)
async def export_runs(
    workspace: WorkspaceDep,
    db: DbDep,
    filters: RunFiltersDep,
    limit: int = Query(1000, ge=1, le=5000),
) -> StreamingResponse:
    """CSV of the runs matching exactly the list filters."""
    stmt = await _filtered(
        select(AgentRun).order_by(AgentRun.started_at.desc(), AgentRun.id.desc()).limit(limit),
        filters,
        workspace,
        db,
    )
    runs = list((await db.execute(stmt)).scalars().all())
    primary_models = await _primary_models(db, [r.id for r in runs])

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
    access_group_id: uuid.UUID | None = Query(None),
    api_key_id: uuid.UUID | None = Query(None),
    end_user_id: str | None = Query(None),
    tag: str | None = Query(None),
    tool_name: str | None = Query(None),
    security_event_only: bool = Query(False),
) -> RunFlowResponse:
    """
    Safe request-flow records for Sankey dashboards.

    This endpoint returns labels and metrics only. It avoids returning captured
    prompt/response payloads so org/platform flow views do not broaden sensitive
    content access.
    """
    workspace_ids = await _flow_workspace_ids(scope=scope, workspace=workspace, user=user, db=db)
    if access_group_id is not None and scope != "workspace":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "access_group_id is only supported for workspace scope",
        )
    if api_key_id is not None and scope != "workspace":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "api_key_id is only supported for workspace scope",
        )
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

    filters: list[sa.ColumnElement[bool]] = [AgentRun.workspace_id.in_(workspace_ids)]
    if api_key_id is not None:
        filters.append(AgentRun.api_key_id == api_key_id)
    if end_user_id is not None:
        filters.append(AgentRun.end_user_id == end_user_id)
    access = await resolve_access_group(db, workspace.id, access_group_id)
    filters.extend(run_access_clauses(access, workspace_ids))
    if from_dt is not None:
        filters.append(AgentRun.started_at >= from_dt)
    if to_dt is not None:
        filters.append(AgentRun.started_at <= to_dt)
    if tag or tool_name or security_event_only:
        gov_sub = _governance_run_subquery(
            workspace_id=workspace.id,
            tag=tag,
            tool_name=tool_name,
            security_event_only=security_event_only,
        )
        filters.append(AgentRun.id.in_(gov_sub))

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
    savings_by_run: dict[uuid.UUID, Decimal] = {}
    spans_by_run: dict[uuid.UUID, list[Span]] = {run_id: [] for run_id in run_ids}
    tools_by_run: dict[uuid.UUID, list[ToolCall]] = {run_id: [] for run_id in run_ids}
    outcomes_by_run: dict[uuid.UUID, _RunOutcome] = {}
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
            if call.savings_usd is not None and call.savings_usd > 0:
                savings_by_run[call.run_id] = (
                    savings_by_run.get(call.run_id, Decimal("0")) + call.savings_usd
                )

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

        # One outcome per run, however many were recorded (review O-03/O-04): the
        # latest type, and success when any recorded outcome succeeded.
        for outcome in (
            await db.execute(
                select(Outcome)
                .where(Outcome.workspace_id.in_(workspace_ids), Outcome.run_id.in_(run_ids))
                .order_by(Outcome.created_at.desc())
            )
        ).scalars():
            assert outcome.run_id is not None
            agg = outcomes_by_run.setdefault(
                outcome.run_id, _RunOutcome(outcome.outcome_type, False)
            )
            agg.success = agg.success or bool(outcome.success)

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
        route_ids = [
            request.route_id for request in gateway_requests if request.route_id is not None
        ]
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
        run_outcome = outcomes_by_run.get(run.id)
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
        cached_input_tokens: int = (
            (primary_call.cached_input_tokens if primary_call else None)
            or (
                gateway_request.input_tokens
                if gateway_request is not None and gateway_request.cache_hit
                else 0
            )
            or 0
        )
        agent_name = (
            _metadata_value(metadata, ["agent_name", "agent", "agent_client", "selected_agent"])
            or _metadata_value(
                resource_metadata, ["agent_name", "agent", "agent_client", "service.name"]
            )
            or _first_metadata(
                spans, ["agent_name", "agent", "agent_client", "selected_agent", "workflow_agent"]
            )
            or next((span.name for span in spans if span.span_type == "agent"), None)
        )
        skill_name = _metadata_value(
            metadata, ["skill", "skill_name", "selected_skill", "runledger.skill"]
        ) or _first_metadata(spans, ["skill", "skill_name", "selected_skill", "runledger.skill"])
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
        model = (
            primary_call.model
            if primary_call is not None
            else (gateway_request.model_used if gateway_request else None)
        )
        total_cost = run.total_cost_usd or Decimal("0")
        # Recorded savings only (review O-13): the sum of what provider calls
        # reported, never an estimate derived from tokens or the model name.
        savings = savings_by_run.get(run.id, Decimal("0"))
        savings_category = primary_call.savings_category if primary_call is not None else None
        savings_reason = primary_call.savings_reason if primary_call is not None else None
        route_label = (
            route.alias
            if route is not None
            else (
                gateway_request.model_requested
                if gateway_request is not None
                else "Direct SDK / OTLP"
            )
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
                    f"{run_outcome.outcome_type}: {'Success' if run_outcome.success else 'Miss'}"
                    if run_outcome is not None
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
                success=(
                    run_outcome.success
                    if run_outcome is not None
                    else run.status == RunStatusEnum.succeeded
                ),
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


# ── Compare two runs (ENH) ────────────────────────────────────────────────────


async def _compare_side(
    db: AsyncSession, workspace_id: uuid.UUID, run_id: uuid.UUID
) -> RunCompareSide:
    run = (await db.execute(_run_lookup(run_id, workspace_id, None))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Run {run_id} not found")
    calls = list(
        (await db.execute(select(ProviderCall).where(ProviderCall.run_id == run_id)))
        .scalars()
        .all()
    )
    tools = list(
        (await db.execute(select(ToolCall.tool_name).where(ToolCall.run_id == run_id)))
        .scalars()
        .all()
    )
    span_count = (
        await db.execute(select(func.count(Span.id)).where(Span.run_id == run_id))
    ).scalar_one()
    latencies = [c.latency_ms for c in calls if c.latency_ms is not None]
    return RunCompareSide(
        run=_list_item(run, max(calls, key=lambda c: c.cost_usd or 0).model if calls else None),
        models=sorted({c.model for c in calls if c.model}),
        provider_call_count=len(calls),
        tool_call_count=len(tools),
        tools=sorted(set(tools)),
        span_count=int(span_count),
        error_count=sum(1 for c in calls if c.status != "success"),
        total_latency_ms=sum(latencies) if latencies else None,
        cached_input_tokens=sum(c.cached_input_tokens or 0 for c in calls),
        savings_usd=sum((c.savings_usd or Decimal(0) for c in calls), Decimal(0)),
    )


@router.get("/compare", response_model=RunCompareResponse)
async def compare_runs(
    workspace: WorkspaceDep,
    db: DbDep,
    a: uuid.UUID = Query(..., description="First run id"),
    b: uuid.UUID = Query(..., description="Second run id"),
) -> RunCompareResponse:
    """Side-by-side comparison of two runs with deltas (b minus a)."""
    left = await _compare_side(db, workspace.id, a)
    right = await _compare_side(db, workspace.id, b)

    def _d(x: Any, y: Any) -> Decimal | None:
        if x is None or y is None:
            return None
        return Decimal(str(y)) - Decimal(str(x))

    return RunCompareResponse(
        a=left,
        b=right,
        delta={
            "cost_usd": _d(left.run.total_cost_usd, right.run.total_cost_usd),
            "input_tokens": _d(left.run.total_input_tokens, right.run.total_input_tokens),
            "output_tokens": _d(left.run.total_output_tokens, right.run.total_output_tokens),
            "duration_ms": _d(left.run.duration_ms, right.run.duration_ms),
            "provider_calls": _d(left.provider_call_count, right.provider_call_count),
            "tool_calls": _d(left.tool_call_count, right.tool_call_count),
        },
    )


# ── Saved views (ENH; per user, minimal until the W2-C preferences API) ───────

UserSessionDep = Annotated[tuple[Workspace, User], Depends(require_user)]


def _check_page(page: str) -> str:
    if page not in SAVED_VIEW_PAGES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"page must be one of: {', '.join(SAVED_VIEW_PAGES)}",
        )
    return page


@router.get("/saved-views", response_model=SavedViewList)
async def list_saved_views(
    ws_user: UserSessionDep, db: DbDep, page: str = Query("runs")
) -> SavedViewList:
    workspace, user = ws_user
    rows = (
        await db.execute(
            select(SavedView)
            .where(
                SavedView.workspace_id == workspace.id,
                SavedView.user_id == user.id,
                SavedView.page == _check_page(page),
            )
            .order_by(SavedView.name)
        )
    ).scalars()
    return SavedViewList(items=[SavedViewResponse.model_validate(v) for v in rows])


@router.post("/saved-views", response_model=SavedViewResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_view(
    body: SavedViewCreate, ws_user: UserSessionDep, db: DbDep
) -> SavedViewResponse:
    """Create, or replace the query of, the caller's view with this name."""
    workspace, user = ws_user
    _check_page(body.page)
    view = (
        await db.execute(
            select(SavedView).where(
                SavedView.workspace_id == workspace.id,
                SavedView.user_id == user.id,
                SavedView.page == body.page,
                SavedView.name == body.name,
            )
        )
    ).scalar_one_or_none()
    if view is None:
        view = SavedView(
            workspace_id=workspace.id,
            user_id=user.id,
            page=body.page,
            name=body.name,
            query=body.query,
        )
        db.add(view)
    else:
        view.query = body.query
        view.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(view)
    return SavedViewResponse.model_validate(view)


@router.put("/saved-views/{view_id}", response_model=SavedViewResponse)
async def update_saved_view(
    view_id: uuid.UUID, body: SavedViewCreate, ws_user: UserSessionDep, db: DbDep
) -> SavedViewResponse:
    workspace, user = ws_user
    view = await db.get(SavedView, view_id)
    if view is None or view.workspace_id != workspace.id or view.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved view not found")
    view.page = _check_page(body.page)
    view.name = body.name
    view.query = body.query
    view.updated_at = datetime.now(UTC)
    try:
        await db.commit()
    except sa.exc.IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A view with that name exists") from exc
    await db.refresh(view)
    return SavedViewResponse.model_validate(view)


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_view(view_id: uuid.UUID, ws_user: UserSessionDep, db: DbDep) -> Response:
    workspace, user = ws_user
    view = await db.get(SavedView, view_id)
    if view is None or view.workspace_id != workspace.id or view.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved view not found")
    await db.delete(view)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Cancel a stuck run ────────────────────────────────────────────────────────


@router.patch(
    "/{run_id}/cancel", response_model=RunListItem, dependencies=[Depends(require_workspace_writer)]
)
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

    return _list_item(run, None)


# ── Run detail ────────────────────────────────────────────────────────────────


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: uuid.UUID,
    request: Request,
    workspace: WorkspaceDep,
    db: DbDep,
    access_group_id: uuid.UUID | None = Query(None),
) -> RunDetailResponse:
    """Run detail. Captured prompts/responses appear once (``span_payloads``, plus the
    first input/output) and only for callers allowed to read them (review O-05)."""
    access = await resolve_access_group(db, workspace.id, access_group_id)
    run = (await db.execute(_run_lookup(run_id, workspace.id, access))).scalar_one_or_none()
    if run is None:
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

    payload_access = await can_view_payloads(request, workspace, db)
    input_payload: list[dict[str, Any]] | None = None
    output_payload: Any | None = None
    span_payloads: dict[str, dict[str, Any]] = {}
    captured = False
    for s_ in spans:
        meta = s_.span_metadata or {}
        if "messages" not in meta and "response" not in meta:
            continue
        captured = True
        if not payload_access:
            continue
        span_payload: dict[str, Any] = {}
        if "messages" in meta:
            span_payload["input"] = meta["messages"]
            if input_payload is None:
                input_payload = meta["messages"]
        if "response" in meta:
            span_payload["output"] = meta["response"]
            if output_payload is None:
                output_payload = meta["response"]
        span_payloads[str(s_.id)] = span_payload

    return RunDetailResponse(
        id=run.id,
        api_key_id=run.api_key_id,
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
        payloads_captured=captured,
        payloads_redacted=captured and not payload_access,
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
                metadata=strip_payloads(s.span_metadata),
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


@router.get("/{run_id}/governance", response_model=RunGovernanceContextResponse)
async def get_run_governance_context(
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
    access_group_id: uuid.UUID | None = Query(None),
) -> RunGovernanceContextResponse:
    access = await resolve_access_group(db, workspace.id, access_group_id)
    run = (await db.execute(_run_lookup(run_id, workspace.id, access))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")

    tool_calls = list(
        (
            await db.execute(
                select(ToolCall)
                .where(ToolCall.workspace_id == workspace.id, ToolCall.run_id == run.id)
                .order_by(ToolCall.created_at)
            )
        )
        .scalars()
        .all()
    )
    tool_names = sorted({tool.tool_name for tool in tool_calls if tool.tool_name})
    registry_entries = {
        row.tool_name: row
        for row in (
            await db.execute(
                select(ToolRegistry).where(
                    ToolRegistry.workspace_id == workspace.id,
                    ToolRegistry.tool_name.in_(tool_names or [""]),
                )
            )
        )
        .scalars()
        .all()
    }
    policies = list(
        (
            await db.execute(
                select(ToolPolicy)
                .where(
                    ToolPolicy.workspace_id == workspace.id,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.tool_name.in_((tool_names or []) + ["*"]),
                )
                .order_by(ToolPolicy.priority.asc(), ToolPolicy.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    tool_evidence: list[GovernanceToolEvidence] = []
    for tool in tool_calls:
        matched = [policy for policy in policies if policy.tool_name in (tool.tool_name, "*")]
        registry = registry_entries.get(tool.tool_name)
        tool_evidence.append(
            GovernanceToolEvidence(
                tool_name=tool.tool_name,
                tool_type=str(tool.tool_type),
                status=tool.status,
                risk_score=tool.risk_score,
                registry_policy=registry.policy if registry is not None else None,
                registry_runtime_enforcement=bool(registry.runtime_enforcement)
                if registry is not None
                else False,
                matched_policy_count=len(matched),
                matched_policy_names=[policy.name for policy in matched],
                matched_policy_actions=[policy.action for policy in matched],
            )
        )

    security_events = list(
        (
            await db.execute(
                select(SecurityEvent)
                .where(
                    SecurityEvent.workspace_id == workspace.id,
                    sa.or_(
                        SecurityEvent.run_id == run.id,
                        sa.and_(
                            SecurityEvent.end_user_id == run.end_user_id,
                            SecurityEvent.end_user_id.is_not(None),
                        ),
                        SecurityEvent.tool_name.in_(tool_names or [""]),
                    ),
                )
                .order_by(SecurityEvent.detected_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    window_start = run.started_at - timedelta(hours=1)
    window_end = (run.ended_at or run.started_at) + timedelta(hours=1)
    alert_rows = (
        await db.execute(
            select(AlertFiring, AlertRule.name.label("rule_name"))
            .join(AlertRule, AlertFiring.rule_id == AlertRule.id)
            .where(
                AlertFiring.workspace_id == workspace.id,
                AlertFiring.fired_at >= window_start,
                AlertFiring.fired_at <= window_end,
            )
            .order_by(AlertFiring.fired_at.desc())
            .limit(8)
        )
    ).all()
    audit_events = list(
        (
            await db.execute(
                select(AuditEvent)
                .where(
                    sa.or_(
                        sa.and_(
                            AuditEvent.workspace_id == workspace.id,
                            AuditEvent.target_id == str(run.id),
                        ),
                        sa.and_(
                            AuditEvent.workspace_id == workspace.id,
                            AuditEvent.target_id.in_(tool_names or [""]),
                        ),
                        sa.and_(
                            AuditEvent.workspace_id == workspace.id,
                            AuditEvent.created_at >= window_start,
                            AuditEvent.created_at <= window_end,
                            AuditEvent.target_type.in_(
                                [
                                    "tool_policy",
                                    "tool_registry",
                                    "security",
                                    "alert_rule",
                                    "tag",
                                    "governance_pack",
                                    "capture_policy",
                                ]
                            ),
                        ),
                    )
                )
                .order_by(AuditEvent.created_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )

    governance_pack_summary = {
        "approvals": int(
            (
                await db.execute(
                    select(func.count(Approval.id)).where(Approval.workspace_id == workspace.id)
                )
            ).scalar()
            or 0
        ),
        "tool_policies": int(
            (
                await db.execute(
                    select(func.count(ToolPolicy.id)).where(ToolPolicy.workspace_id == workspace.id)
                )
            ).scalar()
            or 0
        ),
        "capture_policies": int(
            (
                await db.execute(
                    select(func.count(CapturePolicy.id)).where(
                        CapturePolicy.workspace_id == workspace.id
                    )
                )
            ).scalar()
            or 0
        ),
        "tags": int(
            (
                await db.execute(select(func.count(Tag.id)).where(Tag.workspace_id == workspace.id))
            ).scalar()
            or 0
        ),
    }

    return RunGovernanceContextResponse(
        run_id=run.id,
        tags=_metadata_tags(run),
        tool_evidence=tool_evidence,
        security_events=[
            GovernanceSecurityEvidence(
                id=str(event.id),
                event_type=event.event_type,
                tool_name=event.tool_name,
                end_user_id=event.end_user_id,
                detected_at=event.detected_at,
                details=event.details or {},
            )
            for event in security_events
        ],
        alert_evidence=[
            GovernanceAlertEvidence(
                id=str(firing.id),
                rule_id=str(firing.rule_id),
                rule_name=rule_name,
                fired_at=firing.fired_at,
                metric_value=firing.metric_value,
                resolved_at=firing.resolved_at,
            )
            for firing, rule_name in alert_rows
        ],
        audit_events=[
            GovernanceAuditEvidence(
                id=str(event.id),
                action=event.action,
                target_type=event.target_type,
                target_id=event.target_id,
                created_at=event.created_at,
            )
            for event in audit_events
        ],
        governance_pack_summary=governance_pack_summary,
    )


# ── Run graph (DAG) ───────────────────────────────────────────────────────────


@router.get("/{run_id}/graph", response_model=RunGraphResponse)
async def get_run_graph(
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
    access_group_id: uuid.UUID | None = Query(None),
) -> RunGraphResponse:
    access = await resolve_access_group(db, workspace.id, access_group_id)
    run = (await db.execute(_run_lookup(run_id, workspace.id, access))).scalar_one_or_none()
    if run is None:
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
                    metadata=strip_payloads(span.span_metadata),
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


# ── Runbooks ─────────────────────────────────────────────────────────────────


@router.post(
    "/{run_id}/runbook",
    response_model=RunbookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def create_runbook(
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> RunbookResponse:
    """Generate an incident-style runbook for a run."""
    try:
        entry = await generate_runbook(db, workspace.id, run_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return RunbookResponse.model_validate(entry)


@router.get("/runbooks/list", response_model=RunbookList)
async def list_runbooks(
    workspace: WorkspaceDep,
    db: DbDep,
    severity: str | None = Query(None, pattern="^(info|warning|critical)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> RunbookList:
    """List generated runbooks for this workspace."""
    base = select(RunbookEntry).where(RunbookEntry.workspace_id == workspace.id)
    if severity:
        base = base.where(RunbookEntry.severity == severity)

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        base.order_by(RunbookEntry.generated_at.desc()).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return RunbookList(
        items=[RunbookResponse.model_validate(e) for e in items],
        total=total,
    )
