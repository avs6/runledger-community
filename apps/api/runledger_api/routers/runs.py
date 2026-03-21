from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.models.events import AgentRun, ProviderCall, Span, ToolCall
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.runs import (
    GraphEdge,
    GraphNode,
    GraphNodeData,
    ProviderCallDetail,
    RunDetailResponse,
    RunGraphResponse,
    RunListItem,
    RunListResponse,
    SpanDetail,
    ToolCallDetail,
)

router = APIRouter(prefix="/runs", tags=["runs"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


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
    model_filter: str | None = Query(None, alias="model", description="Substring match on model name"),
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
            "run_id", "status", "feature_tag", "end_user_id", "session_id",
            "deployment_version", "model", "cost_usd", "input_tokens",
            "output_tokens", "duration_ms", "started_at", "ended_at",
        ],
    )
    writer.writeheader()
    for r in runs:
        writer.writerow({
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
        })

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=runs.csv"},
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

    run.status = "cancelled"
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
