"""Org/access-group scoped summary, savings, optimization opportunities and trends."""

from __future__ import annotations

from ._shared import *  # noqa: F403

# ── Phase 3: Scoped summary ─────────────────────────────────────────────────


@router.get("/scoped-summary", response_model=ScopedSummary)
async def scoped_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Annotated[str, Query(pattern="^(workspace|org|platform)$")] = "workspace",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    access_group_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ScopedSummary:
    """Summary with workspace/org/platform scope, including savings, intents, and top models."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    if access_group_id is not None and scope != "workspace":
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            "access_group_id is only supported for workspace scope",
        )
    ws_ids = await _resolve_scoped_workspace_ids(scope, workspace, user, db)
    duration = t_to - t_from
    access_group_filters = (
        await _resolve_access_group_observe_filters(db, workspace.id, access_group_id)
        if access_group_id is not None
        else None
    )

    base_filter = [
        ProviderCall.workspace_id.in_(ws_ids),
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if access_group_filters:
        if access_group_filters["end_user_ids"]:
            base_filter.append(ProviderCall.end_user_id.in_(access_group_filters["end_user_ids"]))
        if access_group_filters["models"]:
            base_filter.append(ProviderCall.model.in_(access_group_filters["models"]))
        if access_group_filters["providers"]:
            base_filter.append(ProviderCall.provider.in_(access_group_filters["providers"]))
        if access_group_filters["statuses"]:
            base_filter.append(ProviderCall.status.in_(access_group_filters["statuses"]))

    agg = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("inp"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("out"),
            func.count(ProviderCall.run_id.distinct()).label("runs"),
            func.count(ProviderCall.id).label("calls"),
            func.count(ProviderCall.end_user_id.distinct()).label("users"),
        ).where(*base_filter)
    )
    row = agg.one()

    prev_agg = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
        ).where(
            ProviderCall.workspace_id.in_(ws_ids),
            ProviderCall.created_at >= t_from - duration,
            ProviderCall.created_at < t_from,
            ProviderCall.status == "success",
        )
    )
    prev_cost = prev_agg.scalar_one()
    cost_delta = None
    if prev_cost and prev_cost > 0:
        cost_delta = (row.cost - prev_cost) / prev_cost * Decimal(100)

    intent_rows = (
        await db.execute(
            select(
                AgentRun.intent,
                func.count(AgentRun.id).label("cnt"),
                func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost"),
            )
            .where(
                AgentRun.workspace_id.in_(ws_ids),
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
                AgentRun.intent.isnot(None),
            )
            .group_by(AgentRun.intent)
            .order_by(func.count(AgentRun.id).desc())
            .limit(10)
        )
    ).all()
    if access_group_filters:
        # Re-run the intent query with access-group-aware run filters.
        intent_query = select(
            AgentRun.intent,
            func.count(AgentRun.id).label("cnt"),
            func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("cost"),
        ).where(
            AgentRun.workspace_id.in_(ws_ids),
            AgentRun.started_at >= t_from,
            AgentRun.started_at < t_to,
            AgentRun.intent.isnot(None),
        )
        if access_group_filters["end_user_ids"]:
            intent_query = intent_query.where(
                AgentRun.end_user_id.in_(access_group_filters["end_user_ids"])
            )
        if access_group_filters["feature_tags"]:
            intent_query = intent_query.where(
                AgentRun.feature_tag.in_(access_group_filters["feature_tags"])
            )
        if access_group_filters["statuses"]:
            intent_query = intent_query.where(AgentRun.status.in_(access_group_filters["statuses"]))
        if access_group_filters["models"]:
            intent_query = intent_query.where(
                AgentRun.id.in_(
                    select(ProviderCall.run_id)
                    .where(
                        ProviderCall.workspace_id == workspace.id,
                        ProviderCall.model.in_(access_group_filters["models"]),
                    )
                    .distinct()
                )
            )
        if access_group_filters["providers"]:
            intent_query = intent_query.where(
                AgentRun.id.in_(
                    select(ProviderCall.run_id)
                    .where(
                        ProviderCall.workspace_id == workspace.id,
                        ProviderCall.provider.in_(access_group_filters["providers"]),
                    )
                    .distinct()
                )
            )
        intent_rows = (
            await db.execute(
                intent_query.group_by(AgentRun.intent)
                .order_by(func.count(AgentRun.id).desc())
                .limit(10)
            )
        ).all()

    model_rows = (
        await db.execute(
            select(
                ProviderCall.provider,
                ProviderCall.model,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("inp"),
                func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("out"),
                func.count(ProviderCall.id).label("calls"),
            )
            .where(*base_filter)
            .group_by(ProviderCall.provider, ProviderCall.model)
            .order_by(func.sum(ProviderCall.cost_usd).desc())
            .limit(10)
        )
    ).all()

    return ScopedSummary(
        scope=scope,
        total_cost_usd=row.cost,
        total_savings_usd=row.savings,
        total_input_tokens=row.inp,
        total_output_tokens=row.out,
        run_count=row.runs,
        call_count=row.calls,
        workspace_count=len(ws_ids),
        active_users=row.users,
        avg_cost_per_run=row.cost / row.runs if row.runs > 0 else None,
        top_intents=[
            IntentCount(intent=r.intent, count=r.cnt, cost_usd=r.cost) for r in intent_rows
        ],
        top_models=[
            ModelSpend(
                provider=r.provider,
                model=r.model,
                cost_usd=r.cost,
                input_tokens=r.inp,
                output_tokens=r.out,
                call_count=r.calls,
            )
            for r in model_rows
        ],
        cost_delta_pct=cost_delta,
    )


# ── Phase 3: Savings analytics ──────────────────────────────────────────────


@router.get("/savings", response_model=SavingsResponse)
async def savings_analytics(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    api_key_id: Annotated[uuid.UUID | None, Query()] = None,
) -> SavingsResponse:
    """Savings breakdown by category and over time."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    base = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]
    if api_key_id is not None:
        base.append(ProviderCall.api_key_id == api_key_id)

    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                func.coalesce(func.sum(ProviderCall.baseline_cost_usd), Decimal(0)).label(
                    "baseline"
                ),
                billable_cost_sum().label("actual"),
            ).where(*base)
        )
    ).one()

    by_cat = (
        await db.execute(
            select(
                ProviderCall.savings_category,
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                func.count(ProviderCall.id).label("calls"),
            )
            .where(*base, ProviderCall.savings_category.isnot(None))
            .group_by(ProviderCall.savings_category)
            .order_by(func.sum(ProviderCall.savings_usd).desc())
        )
    ).all()

    # Build the bucket once: separate date_trunc() calls bind 'day' as separate
    # parameters, and Postgres then rejects the GROUP BY.
    day_col = func.date_trunc("day", ProviderCall.created_at).label("day")
    timeline = (
        await db.execute(
            select(
                day_col,
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
                func.coalesce(func.sum(ProviderCall.baseline_cost_usd), Decimal(0)).label(
                    "baseline"
                ),
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("actual"),
            )
            .where(*base)
            .group_by(day_col)
            .order_by(day_col)
        )
    ).all()

    savings_rate = None
    if totals.baseline > 0:
        savings_rate = totals.savings / totals.baseline * Decimal(100)

    return SavingsResponse(
        total_savings_usd=totals.savings,
        total_baseline_usd=totals.baseline,
        total_actual_usd=totals.actual,
        savings_rate_pct=savings_rate,
        by_category=[
            SavingsByCategory(
                category=r.savings_category, savings_usd=r.savings, call_count=r.calls
            )
            for r in by_cat
        ],
        timeline=[
            SavingsTimeline(
                period=str(r.day),
                savings_usd=r.savings,
                baseline_cost_usd=r.baseline,
                actual_cost_usd=r.actual,
            )
            for r in timeline
        ],
    )


# ── Phase 3: Optimization opportunities ─────────────────────────────────────


@router.get("/optimization-opportunities", response_model=OptimizationOpportunitiesResponse)
async def optimization_opportunities(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> OptimizationOpportunitiesResponse:
    """Optimization opportunities from the Flywheel (review B-20).

    One engine: each item is a pending Flywheel recommendation learned from observed
    cost and quality, applied with ``POST /gateway/flywheel/recommendations/{id}/apply``.
    ``from``/``to`` are accepted for compatibility; the Flywheel's own lookback
    window applies.
    """
    from runledger_api.services.optimization import flywheel_opportunities  # noqa: PLC0415

    del from_dt, to_dt
    rows = await flywheel_opportunities(db, workspace.id)
    opportunities = [OptimizationOpportunity(**r) for r in rows]
    total_potential = sum((o.potential_savings_usd for o in opportunities), Decimal(0))
    return OptimizationOpportunitiesResponse(
        items=opportunities, total_potential_savings_usd=total_potential
    )


# ── Phase 3: Trends ─────────────────────────────────────────────────────────


@router.get("/trends", response_model=TrendsResponse)
async def trends(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    granularity: Annotated[str, Query(pattern="^(hourly|daily|weekly)$")] = "daily",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> TrendsResponse:
    """Cost, usage, and savings trends over time with period-over-period comparison."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())
    duration = t_to - t_from

    trunc = {"hourly": "hour", "daily": "day", "weekly": "week"}[granularity]

    base = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]

    period_col = func.date_trunc(trunc, ProviderCall.created_at).label("period")
    rows = (
        await db.execute(
            select(
                period_col,
                func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
                func.count(ProviderCall.run_id.distinct()).label("runs"),
                func.count(ProviderCall.id).label("calls"),
                func.coalesce(
                    func.sum(ProviderCall.input_tokens) + func.sum(ProviderCall.output_tokens), 0
                ).label("tokens"),
                func.avg(ProviderCall.latency_ms).label("latency"),
                func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
            )
            .where(*base)
            .group_by(period_col)
            .order_by(period_col)
        )
    ).all()

    # Current and previous period totals for metrics
    cur = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            func.count(ProviderCall.run_id.distinct()).label("runs"),
            func.count(ProviderCall.id).label("calls"),
            func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
        ).where(*base)
    )
    cur_row = cur.one()

    prev = await db.execute(
        select(
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
            func.count(ProviderCall.run_id.distinct()).label("runs"),
            func.count(ProviderCall.id).label("calls"),
            func.coalesce(func.sum(ProviderCall.savings_usd), Decimal(0)).label("savings"),
        ).where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from - duration,
            ProviderCall.created_at < t_from,
            ProviderCall.status == "success",
        )
    )
    prev_row = prev.one()

    def _pct(cur_val: Decimal, prev_val: Decimal) -> Decimal | None:
        if prev_val and prev_val > 0:
            return (cur_val - prev_val) / prev_val * Decimal(100)
        return None

    return TrendsResponse(
        points=[
            TrendPoint(
                period=str(r.period),
                cost_usd=r.cost,
                run_count=r.runs,
                call_count=r.calls,
                tokens=r.tokens,
                avg_latency_ms=Decimal(str(round(r.latency, 1))) if r.latency else None,
                savings_usd=r.savings,
            )
            for r in rows
        ],
        metrics=[
            TrendMetric(
                name="cost_usd",
                current=cur_row.cost,
                previous=prev_row.cost,
                change_pct=_pct(cur_row.cost, prev_row.cost),
            ),
            TrendMetric(
                name="run_count",
                current=Decimal(cur_row.runs),
                previous=Decimal(prev_row.runs),
                change_pct=_pct(Decimal(cur_row.runs), Decimal(prev_row.runs)),
            ),
            TrendMetric(
                name="call_count",
                current=Decimal(cur_row.calls),
                previous=Decimal(prev_row.calls),
                change_pct=_pct(Decimal(cur_row.calls), Decimal(prev_row.calls)),
            ),
            TrendMetric(
                name="savings_usd",
                current=cur_row.savings,
                previous=prev_row.savings,
                change_pct=_pct(cur_row.savings, prev_row.savings),
            ),
        ],
        granularity=granularity,
    )
