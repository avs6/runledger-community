"""End-user cohorts, anomalies and per-user detail."""

from __future__ import annotations

from ._shared import *  # noqa: F403


@router.get("/users/cohorts", response_model=CohortList)
async def user_cohorts(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> CohortList:
    """Classify end-users into P0–P3 spend tiers for the window (default 30d)."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(
        from_dt,
        datetime.now(UTC) - timedelta(days=_DEFAULT_COHORT_DAYS),
    )

    # Inner subquery: per-user total spend
    inner = (
        select(
            ProviderCall.end_user_id,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
            ProviderCall.status == "success",
            ProviderCall.end_user_id.is_not(None),
        )
        .group_by(ProviderCall.end_user_id)
        .subquery()
    )

    tier_col = case(
        (inner.c.cost < Decimal("1"), "P0"),
        (inner.c.cost < Decimal("10"), "P1"),
        (inner.c.cost < Decimal("100"), "P2"),
        else_="P3",
    ).label("tier")

    stmt = (
        select(
            tier_col,
            func.count().label("user_count"),
            func.avg(inner.c.cost).label("avg_cost_usd"),
            func.sum(inner.c.cost).label("total_cost_usd"),
        )
        .select_from(inner)
        .group_by(tier_col)
        .order_by(tier_col)
    )

    result = await db.execute(stmt)
    rows = result.all()

    window_days = int((t_to - t_from).total_seconds() / 86400)
    return CohortList(
        items=[
            CohortSummary(
                cohort_tier=row.tier,
                user_count=row.user_count,
                avg_cost_usd=Decimal(str(row.avg_cost_usd)),
                total_cost_usd=Decimal(str(row.total_cost_usd)),
            )
            for row in rows
        ],
        window_days=window_days,
    )


# ── /analytics/users/anomalies ────────────────────────────────────────────────


@router.get("/users/anomalies", response_model=AnomalyList)
async def user_anomalies(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnomalyList:
    """Most-recent 100 anomaly flags for the workspace (populated by nightly worker)."""
    stmt = (
        select(UserAnomaly)
        .where(UserAnomaly.workspace_id == workspace.id)
        .order_by(UserAnomaly.detected_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return AnomalyList(items=[AnomalyItem.model_validate(r) for r in items])


# ── /analytics/users/{end_user_id} ────────────────────────────────────────────


@router.get("/users/{end_user_id}", response_model=UserSpendDetail)
async def user_spend_detail(
    end_user_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> UserSpendDetail:
    """Spend profile for a single end-user: summary + trend + models + features."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    base_filter = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.end_user_id == end_user_id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
        ProviderCall.status == "success",
    ]

    # ── Summary ──────────────────────────────────────────────────────────────
    summary_stmt = select(
        func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
        func.count(ProviderCall.run_id.distinct()).label("run_count"),
        func.count(ProviderCall.id).label("call_count"),
        func.max(ProviderCall.created_at).label("last_active"),
    ).where(*base_filter)

    # ── Spend over time (daily) ───────────────────────────────────────────────
    period_col = func.date_trunc("day", ProviderCall.created_at).label("period")
    time_stmt = (
        select(
            period_col,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*base_filter)
        .group_by(period_col)
        .order_by(period_col)
    )

    # ── Models used ───────────────────────────────────────────────────────────
    model_stmt = (
        select(
            ProviderCall.provider,
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(*base_filter)
        .group_by(ProviderCall.provider, ProviderCall.model)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    # ── Features used ─────────────────────────────────────────────────────────
    feature_stmt = (
        select(
            AgentRun.feature_tag,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.run_id.distinct()).label("run_count"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(*base_filter)
        .group_by(AgentRun.feature_tag)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    summary_result = await db.execute(summary_stmt)
    summary_row = summary_result.one()

    time_result = await db.execute(time_stmt)
    time_rows = time_result.all()

    model_result = await db.execute(model_stmt)
    model_rows = model_result.all()

    feature_result = await db.execute(feature_stmt)
    feature_rows = feature_result.all()

    avg_cost_per_run = (
        summary_row.cost_usd / summary_row.run_count if summary_row.run_count > 0 else Decimal(0)
    )

    return UserSpendDetail(
        end_user_id=end_user_id,
        cost_usd=summary_row.cost_usd,
        run_count=summary_row.run_count,
        call_count=summary_row.call_count,
        avg_cost_per_run=avg_cost_per_run,
        last_active=(summary_row.last_active.isoformat() if summary_row.last_active else None),
        spend_over_time=[
            SpendPoint(
                period=row.period.isoformat(),
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in time_rows
        ],
        models_used=[
            ModelSpend(
                provider=row.provider,
                model=row.model,
                cost_usd=row.cost_usd,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                call_count=row.call_count,
            )
            for row in model_rows
        ],
        features_used=[
            FeatureSpend(
                feature_tag=row.feature_tag,
                cost_usd=row.cost_usd,
                run_count=row.run_count,
                call_count=row.call_count,
            )
            for row in feature_rows
        ],
    )
