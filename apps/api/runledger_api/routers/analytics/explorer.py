"""Request explorer and engineering metrics."""

from __future__ import annotations

from runledger_api.models.outcomes import Outcome
from runledger_api.services.observe import (
    call_access_clauses,
    call_statuses_for,
    resolve_access_group,
)

from ._shared import *  # noqa: F403

# ── Phase 3: Request explorer ───────────────────────────────────────────────


@router.get("/request-explorer", response_model=RequestExplorerResponse)
async def request_explorer(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    q: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    model: Annotated[str | None, Query()] = None,
    provider: Annotated[str | None, Query()] = None,
    intent: Annotated[str | None, Query()] = None,
    feature_tag: Annotated[str | None, Query()] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    end_user_id: Annotated[str | None, Query()] = None,
    optimization: Annotated[str | None, Query()] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
    tag: Annotated[str | None, Query()] = None,
    tool_name: Annotated[str | None, Query()] = None,
    security_event_only: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RequestExplorerResponse:
    """Paginated request explorer with filtering by run, user, status, model, provider, intent, and optimization."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    access = await resolve_access_group(db, workspace.id, access_group_id)

    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        *call_access_clauses(access),
    ]
    if api_key_id is not None:
        filters.append(ProviderCall.api_key_id == api_key_id)
    if model:
        filters.append(ProviderCall.model == model)
    if provider:
        filters.append(ProviderCall.provider == provider)
    # Accept either vocabulary: the UI speaks run statuses (succeeded/failed),
    # provider calls store success/error (review O-01).
    call_statuses = call_statuses_for(status)
    if call_statuses is not None:
        filters.append(ProviderCall.status.in_(call_statuses or ["__none__"]))
    if optimization:
        filters.append(ProviderCall.optimization_applied == optimization)
    if end_user_id:
        filters.append(ProviderCall.end_user_id == end_user_id)
    if tool_name:
        filters.append(
            ProviderCall.run_id.in_(
                select(ToolCall.run_id)
                .where(
                    ToolCall.workspace_id == workspace.id,
                    ToolCall.tool_name == tool_name,
                )
                .distinct()
            )
        )
    if security_event_only:
        filters.append(
            ProviderCall.run_id.in_(
                select(SecurityEvent.run_id)
                .where(
                    SecurityEvent.workspace_id == workspace.id,
                    SecurityEvent.run_id.is_not(None),
                )
                .distinct()
            )
        )

    # Join with AgentRun for intent filtering
    query = (
        select(
            ProviderCall.id,
            ProviderCall.run_id,
            ProviderCall.provider,
            ProviderCall.model,
            AgentRun.intent,
            AgentRun.feature_tag,
            AgentRun.run_metadata,
            ProviderCall.end_user_id,
            ProviderCall.cost_usd,
            ProviderCall.baseline_cost_usd,
            ProviderCall.savings_usd,
            ProviderCall.optimization_applied,
            ProviderCall.input_tokens,
            ProviderCall.output_tokens,
            ProviderCall.latency_ms,
            ProviderCall.status,
            ProviderCall.created_at,
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(*filters)
    )
    if intent:
        query = query.where(AgentRun.intent == intent)
    if feature_tag:
        query = query.where(AgentRun.feature_tag == feature_tag)
    if tag:
        pattern = f'%"{tag}"%'
        query = query.where(
            or_(
                AgentRun.feature_tag == tag,
                cast(AgentRun.run_metadata, String).ilike(pattern),
            )
        )
    if q:
        q_like = f"%{q.strip()}%"
        if q.strip():
            query = query.where(
                or_(
                    cast(ProviderCall.run_id, String).ilike(q_like),
                    ProviderCall.model.ilike(q_like),
                    ProviderCall.provider.ilike(q_like),
                    ProviderCall.end_user_id.ilike(q_like),
                    AgentRun.intent.ilike(q_like),
                    AgentRun.feature_tag.ilike(q_like),
                )
            )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows = (
        await db.execute(
            query.order_by(ProviderCall.created_at.desc(), ProviderCall.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return RequestExplorerResponse(
        items=[
            RequestRecord(
                id=str(r.id),
                run_id=str(r.run_id),
                provider=r.provider,
                model=r.model,
                intent=r.intent,
                feature_tag=r.feature_tag,
                end_user_id=r.end_user_id,
                cost_usd=r.cost_usd,
                baseline_cost_usd=r.baseline_cost_usd,
                savings_usd=r.savings_usd,
                optimization_applied=r.optimization_applied,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                latency_ms=r.latency_ms,
                status=r.status,
                created_at=str(r.created_at),
                tags=(
                    [
                        item.strip()
                        for item in ((r.run_metadata or {}).get("tags") or [])
                        if isinstance(item, str) and item.strip()
                    ]
                    + ([r.feature_tag] if r.feature_tag else [])
                ),
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Phase 8: Engineering metrics ─────────────────────────────────────────────


@router.get("/engineering", response_model=EngineeringMetrics)
async def engineering_metrics(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> EngineeringMetrics:
    """Engineering dashboard: latency, errors, retries, cache, cost breakdowns, quality funnel."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    base = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
    ]

    # Core metrics
    agg = (
        await db.execute(
            select(
                func.count(ProviderCall.id).label("total"),
                func.avg(ProviderCall.latency_ms).label("avg_lat"),
                func.percentile_cont(0.95).within_group(ProviderCall.latency_ms).label("p95_lat"),
                func.count(case((ProviderCall.status == "error", 1))).label("errors"),
                func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("out"),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(case((ProviderCall.cached_input_tokens > 0, 1))).label("cached"),
            ).where(*base)
        )
    ).one()

    total = agg.total or 1
    total_tokens = agg.inp + agg.out

    # Retry count: spans with parent_span_id that are LLM type (re-attempts)
    retry_count = (
        await db.execute(
            select(func.count(Span.id))
            .join(AgentRun, AgentRun.id == Span.run_id)
            .where(
                AgentRun.workspace_id == workspace.id,
                Span.started_at >= t_from,
                Span.started_at < t_to,
                Span.span_type == "llm",
                Span.parent_span_id.isnot(None),
            )
        )
    ).scalar_one()

    # Cost by feature_tag
    feature_rows = (
        await db.execute(
            select(
                AgentRun.feature_tag,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(ProviderCall.id).label("calls"),
            )
            .join(AgentRun, AgentRun.id == ProviderCall.run_id)
            .where(*base)
            .group_by(AgentRun.feature_tag)
            .order_by(func.sum(ProviderCall.cost_usd).desc())
            .limit(10)
        )
    ).all()

    # Cost by model
    model_rows = (
        await db.execute(
            select(
                ProviderCall.model,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(ProviderCall.id).label("calls"),
            )
            .where(*base)
            .group_by(ProviderCall.model)
            .order_by(func.sum(ProviderCall.cost_usd).desc())
            .limit(10)
        )
    ).all()

    # Cost by tool
    tool_rows = (
        await db.execute(
            select(
                ToolCall.tool_name,
                func.count(ToolCall.id).label("calls"),
            )
            .where(
                ToolCall.workspace_id == workspace.id,
                ToolCall.created_at >= t_from,
                ToolCall.created_at < t_to,
            )
            .group_by(ToolCall.tool_name)
            .order_by(func.count(ToolCall.id).desc())
            .limit(10)
        )
    ).all()

    # Quality funnel
    run_base = [
        AgentRun.workspace_id == workspace.id,
        AgentRun.started_at >= t_from,
        AgentRun.started_at < t_to,
    ]
    total_runs = (await db.execute(select(func.count(AgentRun.id)).where(*run_base))).scalar_one()
    succeeded_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(*run_base, AgentRun.status == "succeeded")
        )
    ).scalar_one()

    # Gateway-routed count
    from runledger_api.models.gateway import GatewayRequest

    routed = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= t_from,
                GatewayRequest.created_at < t_to,
            )
        )
    ).scalar_one()

    cache_hits = (
        await db.execute(
            select(func.count(GatewayRequest.id)).where(
                GatewayRequest.workspace_id == workspace.id,
                GatewayRequest.created_at >= t_from,
                GatewayRequest.created_at < t_to,
                GatewayRequest.cache_hit.is_(True),
            )
        )
    ).scalar_one()

    with_outcome = (
        await db.execute(
            select(func.count(Outcome.run_id.distinct())).where(
                Outcome.workspace_id == workspace.id,
                Outcome.run_id.is_not(None),
                Outcome.created_at >= t_from,
                Outcome.created_at < t_to,
            )
        )
    ).scalar_one()

    positive_outcome = (
        await db.execute(
            select(func.count(Outcome.run_id.distinct())).where(
                Outcome.workspace_id == workspace.id,
                Outcome.run_id.is_not(None),
                Outcome.created_at >= t_from,
                Outcome.created_at < t_to,
                Outcome.success.is_(True),
            )
        )
    ).scalar_one()

    # Lifecycle stages
    stages = [
        LifecycleStage(stage="Received", count=total_runs, pct=Decimal(100)),
        LifecycleStage(
            stage="Routed",
            count=routed,
            pct=Decimal(round(routed / total_runs * 100, 1)) if total_runs > 0 else Decimal(0),
        ),
        LifecycleStage(
            stage="Cached",
            count=cache_hits,
            pct=Decimal(round(cache_hits / total_runs * 100, 1)) if total_runs > 0 else Decimal(0),
        ),
        LifecycleStage(
            stage="Completed",
            count=succeeded_runs,
            pct=Decimal(round(succeeded_runs / total_runs * 100, 1))
            if total_runs > 0
            else Decimal(0),
        ),
        LifecycleStage(
            stage="With outcome",
            count=with_outcome,
            pct=Decimal(round(with_outcome / total_runs * 100, 1))
            if total_runs > 0
            else Decimal(0),
        ),
        LifecycleStage(
            stage="Positive",
            count=positive_outcome,
            pct=Decimal(round(positive_outcome / total_runs * 100, 1))
            if total_runs > 0
            else Decimal(0),
        ),
    ]

    return EngineeringMetrics(
        avg_latency_ms=Decimal(str(round(agg.avg_lat, 1))) if agg.avg_lat else None,
        p95_latency_ms=Decimal(str(round(agg.p95_lat, 1))) if agg.p95_lat else None,
        error_pct=Decimal(str(round(agg.errors / total * 100, 2))),
        retry_pct=Decimal(str(round(retry_count / total * 100, 2))),
        cache_pct=Decimal(str(round(agg.cached / total * 100, 2))),
        total_requests=agg.total,
        total_tokens=total_tokens,
        avg_cost_per_request=agg.cost / agg.total if agg.total > 0 else None,
        cost_by_feature=[
            CostByDimension(name=r.feature_tag or "Untagged", cost_usd=r.cost, call_count=r.calls)
            for r in feature_rows
        ],
        cost_by_model=[
            CostByDimension(name=r.model, cost_usd=r.cost, call_count=r.calls) for r in model_rows
        ],
        cost_by_tool=[
            CostByDimension(name=r.tool_name, cost_usd=Decimal(0), call_count=r.calls)
            for r in tool_rows
        ],
        quality_funnel=QualityFunnel(
            total_requests=total_runs,
            successful=succeeded_runs,
            routed=routed,
            cached=cache_hits,
            with_outcome=with_outcome,
            positive_outcome=positive_outcome,
        ),
        lifecycle_stages=stages,
    )
