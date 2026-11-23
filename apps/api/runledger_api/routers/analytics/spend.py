"""Workspace summary and spend breakdowns."""

from __future__ import annotations

from fastapi import Request

from runledger_api.services.observe import (
    AccessGroupFilters,
    call_access_clauses,
    compute_summary,
    request_user,
    resolve_access_group,
    spend_by_model_rows,
    spend_series,
)
from runledger_api.services.observe import run_filters as run_filters_for

from ._shared import *  # noqa: F403

# ── Shared query parameters ───────────────────────────────────────────────────

ScopeQ = Annotated[str, Query(pattern="^(workspace|org|platform)$")]


async def _scope_and_access(
    *,
    scope: str,
    access_group_id: uuid.UUID | None,
    workspace: Workspace,
    request: Request,
    db: AsyncSession,
) -> tuple[list[uuid.UUID], AccessGroupFilters | None]:
    if access_group_id is not None and scope != "workspace":
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            "access_group_id is only supported for workspace scope",
        )
    user = await request_user(request, db) if scope != "workspace" else None
    ws_ids = await _resolve_scoped_workspace_ids(scope, workspace, user, db)
    access = await resolve_access_group(db, workspace.id, access_group_id)
    return ws_ids, access


# ── /analytics/summary ────────────────────────────────────────────────────────


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    scope: ScopeQ = "workspace",
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> AnalyticsSummary:
    """Total cost, tokens, runs, calls and run success rate for the window.

    Same computation as ``/analytics/scoped-summary`` (services.observe.compute_summary),
    so every KPI tile agrees (review O-06, O-22).
    """
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    ws_ids, access = await _scope_and_access(
        scope=scope, access_group_id=access_group_id, workspace=workspace, request=request, db=db
    )
    result = await compute_summary(
        db, workspace_ids=ws_ids, t_from=t_from, t_to=t_to, access=access, api_key_id=api_key_id
    )
    return AnalyticsSummary(
        total_cost_usd=result.total_cost_usd,
        total_input_tokens=result.total_input_tokens,
        total_output_tokens=result.total_output_tokens,
        run_count=result.run_count,
        call_count=result.call_count,
        prev_cost_usd=result.prev_cost_usd,
        cost_delta_pct=result.cost_delta_pct,
        success_rate=result.success_rate,
        succeeded_runs=result.succeeded_runs,
        finished_runs=result.finished_runs,
        total_savings_usd=result.total_savings_usd,
        active_users=result.active_users,
    )


# ── /analytics/spend-over-time ────────────────────────────────────────────────


@router.get("/spend-over-time", response_model=SpendOverTime)
async def spend_over_time(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    granularity: Annotated[str, Query(pattern="^(minute|5min|hourly|daily)$")] = "daily",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    scope: ScopeQ = "workspace",
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendOverTime:
    """Cost and tokens over time. Hourly and daily buckets read the usage_hourly
    rollup and only fall back to raw provider calls for hours it hasn't covered yet."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    ws_ids, access = await _scope_and_access(
        scope=scope, access_group_id=access_group_id, workspace=workspace, request=request, db=db
    )
    points, source = await spend_series(
        db,
        workspace_ids=ws_ids,
        t_from=t_from,
        t_to=t_to,
        granularity=granularity,
        access=access,
        api_key_id=api_key_id,
    )
    return SpendOverTime(
        granularity=granularity,
        source=source,
        points=[
            SpendPoint(
                period=p.period.isoformat(),
                cost_usd=p.cost_usd,
                input_tokens=p.input_tokens,
                output_tokens=p.output_tokens,
                call_count=p.call_count,
            )
            for p in points
        ],
    )


# ── /analytics/spend-by-model ─────────────────────────────────────────────────


@router.get("/spend-by-model", response_model=SpendByModel)
async def spend_by_model(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    scope: ScopeQ = "workspace",
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByModel:
    """Cost and token usage by provider + model (rollup-backed, see spend-over-time)."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    ws_ids, access = await _scope_and_access(
        scope=scope, access_group_id=access_group_id, workspace=workspace, request=request, db=db
    )
    rows = await spend_by_model_rows(
        db, workspace_ids=ws_ids, t_from=t_from, t_to=t_to, access=access, api_key_id=api_key_id
    )
    if not rows:
        run_filters = run_filters_for(ws_ids, t_from, t_to, access, api_key_id)
        run_model = func.coalesce(
            AgentRun.run_metadata["model"].astext,
            AgentRun.run_metadata["primary_model"].astext,
            AgentRun.intent,
            AgentRun.source_type,
            sa.literal("unknown"),
        )
        run_stmt = (
            select(
                sa.literal("observed").label("provider"),
                run_model.label("model"),
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost_usd"),
                func.coalesce(func.sum(AgentRun.total_input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(AgentRun.total_output_tokens), 0).label("output_tokens"),
                func.count(AgentRun.id).label("call_count"),
            )
            .where(*run_filters, AgentRun.status == "succeeded")
            .group_by(run_model)
            .order_by(func.sum(AgentRun.total_cost_usd).desc().nulls_last())
        )
        fallback = (await db.execute(run_stmt)).all()
        return SpendByModel(
            items=[
                ModelSpend(
                    provider=r.provider,
                    model=r.model,
                    cost_usd=r.cost_usd,
                    input_tokens=r.input_tokens,
                    output_tokens=r.output_tokens,
                    call_count=r.call_count,
                )
                for r in fallback
            ]
        )
    return SpendByModel(
        items=[
            ModelSpend(
                provider=r.provider,
                model=r.model,
                cost_usd=r.cost_usd,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                call_count=r.call_count,
            )
            for r in rows
        ]
    )


# ── /analytics/spend-by-user ──────────────────────────────────────────────────


@router.get("/spend-by-user", response_model=SpendByUser)
async def spend_by_user(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByUser:
    """Top end-users by spend."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    access = await resolve_access_group(db, workspace.id, access_group_id)

    sbu_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
        ProviderCall.end_user_id.is_not(None),
        *call_access_clauses(access),
    ]
    if api_key_id is not None:
        sbu_filters.append(ProviderCall.api_key_id == api_key_id)

    stmt = (
        select(
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
            func.max(ProviderCall.created_at).label("last_active"),
            func.min(ProviderCall.created_at).label("first_seen"),
        )
        .where(*sbu_filters)
        .group_by(ProviderCall.end_user_id)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return SpendByUser(
        items=[
            UserSpend(
                end_user_id=row.end_user_id,
                cost_usd=row.cost_usd,
                run_count=row.run_count,
                call_count=row.call_count,
                avg_cost_per_run=(
                    row.cost_usd / row.run_count if row.run_count > 0 else Decimal(0)
                ),
                last_active=(row.last_active.isoformat() if row.last_active else None),
                first_seen=(row.first_seen.isoformat() if row.first_seen else None),
            )
            for row in rows
        ]
    )


# ── /analytics/spend-by-feature ───────────────────────────────────────────────


@router.get("/spend-by-feature", response_model=SpendByFeature)
async def spend_by_feature(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
    scope: ScopeQ = "workspace",
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByFeature:
    """Cost and run count broken down by feature_tag (workflow)."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    ws_ids, access = await _scope_and_access(
        scope=scope, access_group_id=access_group_id, workspace=workspace, request=request, db=db
    )

    sbf_filters = [
        ProviderCall.workspace_id.in_(ws_ids),
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
        *call_access_clauses(access),
    ]
    if api_key_id is not None:
        sbf_filters.append(AgentRun.api_key_id == api_key_id)

    stmt = (
        select(
            AgentRun.feature_tag,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(*sbf_filters)
        .group_by(AgentRun.feature_tag)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        run_filters = [
            *run_filters_for(ws_ids, t_from, t_to, access, api_key_id),
            AgentRun.status == "succeeded",
        ]
        run_stmt = (
            select(
                AgentRun.feature_tag,
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost_usd"),
                func.count(AgentRun.id).label("run_count"),
                func.count(AgentRun.id).label("call_count"),
            )
            .where(*run_filters)
            .group_by(AgentRun.feature_tag)
            .order_by(func.sum(AgentRun.total_cost_usd).desc().nulls_last())
        )
        rows = (await db.execute(run_stmt)).all()

    return SpendByFeature(
        items=[
            FeatureSpend(
                feature_tag=row.feature_tag,
                cost_usd=row.cost_usd,
                run_count=row.run_count,
                call_count=row.call_count,
            )
            for row in rows
        ]
    )
