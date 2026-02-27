from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
import sqlalchemy as sa
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
) -> RunListResponse:
    # Total count query (without cursor/limit)
    count_stmt = select(func.count()).select_from(AgentRun).where(
        AgentRun.workspace_id == workspace.id
    )
    if status_filter:
        count_stmt = count_stmt.where(AgentRun.status == status_filter)
    if feature_tag:
        count_stmt = count_stmt.where(AgentRun.feature_tag == feature_tag)
    if end_user_id:
        count_stmt = count_stmt.where(AgentRun.end_user_id == end_user_id)
    if from_dt:
        count_stmt = count_stmt.where(AgentRun.started_at >= from_dt)
    if to_dt:
        count_stmt = count_stmt.where(AgentRun.started_at <= to_dt)

    total = (await db.execute(count_stmt)).scalar_one()

    # Data query
    stmt = (
        select(AgentRun)
        .where(AgentRun.workspace_id == workspace.id)
        .order_by(AgentRun.started_at.desc())
        .limit(limit + 1)
    )
    if status_filter:
        stmt = stmt.where(AgentRun.status == status_filter)
    if feature_tag:
        stmt = stmt.where(AgentRun.feature_tag == feature_tag)
    if end_user_id:
        stmt = stmt.where(AgentRun.end_user_id == end_user_id)
    if search:
        # Prefix match on string representation of UUID
        stmt = stmt.where(func.cast(AgentRun.id, sa.Text()).like(f"{search}%"))
    if cursor:
        cursor_dt = datetime.fromisoformat(cursor)
        stmt = stmt.where(AgentRun.started_at < cursor_dt)
    if from_dt:
        stmt = stmt.where(AgentRun.started_at >= from_dt)
    if to_dt:
        stmt = stmt.where(AgentRun.started_at <= to_dt)

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
    pc_result = await db.execute(
        select(ProviderCall).where(ProviderCall.run_id == run_id)
    )
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
