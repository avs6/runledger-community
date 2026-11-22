"""Workspace summary and spend breakdowns."""

from __future__ import annotations

from ._shared import *  # noqa: F403

# ── /analytics/summary ────────────────────────────────────────────────────────


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> AnalyticsSummary:
    """Total cost, tokens, run count and call count for the time window."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    # Prior period: same duration, shifted back
    duration = t_to - t_from
    prev_from = t_from - duration
    prev_to = t_from

    def _summary_stmt(period_from: datetime, period_to: datetime) -> Any:
        # Spend uses the shared billable-cost definition (billing, budgets and
        # chargeback agree); usage counters cover successful calls.
        ok = ProviderCall.status == "success"
        stmt = select(
            billable_cost_sum().label("total_cost"),
            func.coalesce(func.sum(case((ok, ProviderCall.input_tokens))), 0).label("total_input"),
            func.coalesce(func.sum(case((ok, ProviderCall.output_tokens))), 0).label(
                "total_output"
            ),
            func.count(case((ok, ProviderCall.run_id)).distinct()).label("run_count"),
            func.count(case((ok, ProviderCall.id))).label("call_count"),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= period_from,
            ProviderCall.created_at < period_to,
        )
        if api_key_id is not None:
            stmt = stmt.where(ProviderCall.api_key_id == api_key_id)
        return stmt

    result = await db.execute(_summary_stmt(t_from, t_to))
    row = result.one()

    prev_result = await db.execute(_summary_stmt(prev_from, prev_to))
    prev_row = prev_result.one()

    if int(row.call_count or 0) == 0:

        def _run_summary_stmt(period_from: datetime, period_to: datetime) -> Any:
            filters = _successful_run_filter(workspace.id, period_from, period_to)
            if api_key_id is not None:
                filters.append(AgentRun.api_key_id == api_key_id)
            return select(
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("total_cost"),
                func.coalesce(func.sum(AgentRun.total_input_tokens), 0).label("total_input"),
                func.coalesce(func.sum(AgentRun.total_output_tokens), 0).label("total_output"),
                func.count(AgentRun.id).label("run_count"),
                func.count(AgentRun.id).label("call_count"),
            ).where(*filters)

        row = (await db.execute(_run_summary_stmt(t_from, t_to))).one()
        prev_row = (await db.execute(_run_summary_stmt(prev_from, prev_to))).one()

    prev_cost: Decimal = prev_row.total_cost
    cost_delta_pct: Decimal | None = None
    if prev_cost and prev_cost > Decimal(0):
        cost_delta_pct = (row.total_cost - prev_cost) / prev_cost * Decimal(100)

    return AnalyticsSummary(
        total_cost_usd=row.total_cost,
        total_input_tokens=row.total_input,
        total_output_tokens=row.total_output,
        run_count=row.run_count,
        call_count=row.call_count,
        prev_cost_usd=prev_cost,
        cost_delta_pct=cost_delta_pct,
    )


# ── /analytics/spend-over-time ────────────────────────────────────────────────


@router.get("/spend-over-time", response_model=SpendOverTime)
async def spend_over_time(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    granularity: Annotated[str, Query(pattern="^(minute|5min|hourly|daily)$")] = "daily",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendOverTime:
    """Time-series of cost and token usage, bucketed by minute, 5 minutes, hour, or day."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    if granularity == "minute":
        period_col = func.date_trunc("minute", ProviderCall.created_at).label("period")
    elif granularity == "5min":
        period_col = func.to_timestamp(
            func.floor(func.extract("epoch", ProviderCall.created_at) / 300) * 300
        ).label("period")
    else:
        trunc_unit = "hour" if granularity == "hourly" else "day"
        period_col = func.date_trunc(trunc_unit, ProviderCall.created_at).label("period")

    sot_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if api_key_id is not None:
        sot_filters.append(ProviderCall.api_key_id == api_key_id)

    stmt = (
        select(
            period_col,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*sot_filters)
        .group_by(period_col)
        .order_by(period_col)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        if granularity == "minute":
            run_period_col = func.date_trunc("minute", AgentRun.started_at).label("period")
        elif granularity == "5min":
            run_period_col = func.to_timestamp(
                func.floor(func.extract("epoch", AgentRun.started_at) / 300) * 300
            ).label("period")
        else:
            trunc_unit = "hour" if granularity == "hourly" else "day"
            run_period_col = func.date_trunc(trunc_unit, AgentRun.started_at).label("period")

        run_filters = _successful_run_filter(workspace.id, t_from, t_to)
        if api_key_id is not None:
            run_filters.append(AgentRun.api_key_id == api_key_id)

        run_stmt = (
            select(
                run_period_col,
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost_usd"),
                func.coalesce(func.sum(AgentRun.total_input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(AgentRun.total_output_tokens), 0).label("output_tokens"),
                func.count(AgentRun.id).label("call_count"),
            )
            .where(*run_filters)
            .group_by(run_period_col)
            .order_by(run_period_col)
        )
        rows = (await db.execute(run_stmt)).all()

    return SpendOverTime(
        granularity=granularity,
        points=[
            SpendPoint(
                period=row.period.isoformat(),
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in rows
        ],
    )


# ── /analytics/spend-by-model ─────────────────────────────────────────────────


@router.get("/spend-by-model", response_model=SpendByModel)
async def spend_by_model(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByModel:
    """Cost and token usage broken down by provider + model."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    sbm_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if api_key_id is not None:
        sbm_filters.append(ProviderCall.api_key_id == api_key_id)

    stmt = (
        select(
            ProviderCall.provider,
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*sbm_filters)
        .group_by(ProviderCall.provider, ProviderCall.model)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        run_filters = _successful_run_filter(workspace.id, t_from, t_to)
        if api_key_id is not None:
            run_filters.append(AgentRun.api_key_id == api_key_id)
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
            .where(*run_filters)
            .group_by(run_model)
            .order_by(func.sum(AgentRun.total_cost_usd).desc().nulls_last())
        )
        rows = (await db.execute(run_stmt)).all()

    return SpendByModel(
        items=[
            ModelSpend(
                provider=row.provider,
                model=row.model,
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in rows
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
) -> SpendByUser:
    """Top end-users by spend."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    sbu_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
        ProviderCall.end_user_id.is_not(None),
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
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SpendByFeature:
    """Cost and run count broken down by feature_tag."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    sbf_filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
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
        run_filters = _successful_run_filter(workspace.id, t_from, t_to)
        if api_key_id is not None:
            run_filters.append(AgentRun.api_key_id == api_key_id)
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
