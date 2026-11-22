"""Optimization simulator, model scorecards, API key footprint and model budget utilization."""

from __future__ import annotations

from ._shared import *  # noqa: F403


@router.post("/simulate-optimization", response_model=SimulationResult)
async def simulate_optimization(
    body: SimulationRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SimulationResult:
    """Simulate savings from a proposed route/model/cache/compression change."""
    t_from = _parse_dt(
        body.from_dt.isoformat() if body.from_dt else None,
        _default_from(),
    )
    t_to = _parse_dt(
        body.to_dt.isoformat() if body.to_dt else None,
        _default_to(),
    )

    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= t_from,
        ProviderCall.created_at < t_to,
    ]
    if body.intent:
        run_ids_q = select(AgentRun.id).where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.intent == body.intent,
        )
        filters.append(ProviderCall.run_id.in_(run_ids_q))
    if body.current_model:
        filters.append(func.lower(ProviderCall.model).contains(body.current_model.lower()))
    if body.current_provider:
        filters.append(func.lower(ProviderCall.provider).contains(body.current_provider.lower()))

    q = select(
        func.count().label("total"),
        func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost"),
        func.avg(ProviderCall.latency_ms).label("avg_lat"),
        func.sum(ProviderCall.input_tokens).label("in_tok"),
        func.sum(ProviderCall.output_tokens).label("out_tok"),
        func.sum(case((ProviderCall.cached_input_tokens > 0, 1), else_=0)).label("cached"),
    ).where(*filters)

    row = (await db.execute(q)).one()

    affected = row.total or 0
    current_cost = Decimal(str(row.cost or 0))
    current_lat = float(row.avg_lat) if row.avg_lat else None
    cached_count = row.cached or 0

    if affected == 0:
        return SimulationResult(
            affected_requests=0,
            current_cost_usd=Decimal(0),
            projected_cost_usd=Decimal(0),
            projected_savings_usd=Decimal(0),
            savings_pct=Decimal(0),
            current_avg_latency_ms=None,
            projected_latency_ms=None,
            latency_delta_pct=None,
            quality_risk="unknown",
            confidence="low",
            impacts=[],
            description="No matching requests found for the given filters.",
        )

    current_key = _match_model_key(body.current_model)
    proposed_key = _match_model_key(body.proposed_model)

    model_cost_ratio = Decimal(1)
    if current_key and proposed_key:
        cur_ratio = MODEL_COST_RATIOS.get(current_key, 1.0)
        new_ratio = MODEL_COST_RATIOS.get(proposed_key, 1.0)
        if cur_ratio > 0:
            model_cost_ratio = Decimal(str(round(new_ratio / cur_ratio, 4)))

    cache_savings_pct = Decimal(0)
    if body.enable_cache:
        current_cache_rate = cached_count / affected if affected > 0 else 0
        target_cache_rate = max(current_cache_rate, 0.40)
        cache_savings_pct = Decimal(str(round((target_cache_rate - current_cache_rate) * 0.50, 4)))

    compression_pct = Decimal("0.15") if body.enable_compression else Decimal(0)

    projected_cost = (
        current_cost * model_cost_ratio * (1 - cache_savings_pct) * (1 - compression_pct)
    )
    projected_savings = current_cost - projected_cost
    savings_pct = (projected_savings / current_cost * 100) if current_cost > 0 else Decimal(0)

    proposed_lat = None
    lat_delta = None
    if current_lat and proposed_key:
        proposed_lat_est = MODEL_LATENCY_MS.get(proposed_key)
        if proposed_lat_est:
            proposed_lat = Decimal(str(round(proposed_lat_est, 1)))
            if current_lat > 0:
                lat_delta = Decimal(
                    str(round((proposed_lat_est - current_lat) / current_lat * 100, 1))
                )

    quality_risk = "low"
    if proposed_key:
        quality_risk = QUALITY_RISK_MAP.get(proposed_key, "medium")

    confidence = "high" if affected >= 100 else "medium" if affected >= 20 else "directional"

    impacts: list[SimulationImpact] = []
    if body.proposed_model and body.current_model:
        impacts.append(
            SimulationImpact(
                label="Model change",
                current_value=body.current_model,
                projected_value=body.proposed_model,
                delta_pct=Decimal(str(round((float(model_cost_ratio) - 1) * 100, 1))),
            )
        )
    if body.enable_cache:
        impacts.append(
            SimulationImpact(
                label="Cache policy",
                current_value=f"{round(cached_count / affected * 100)}% hit rate"
                if affected > 0
                else "0%",
                projected_value=f"~{round(float(cache_savings_pct) * 100 + cached_count / affected * 100)}% hit rate"
                if affected > 0
                else "40%",
                delta_pct=Decimal(str(round(float(cache_savings_pct) * -100, 1))),
            )
        )
    if body.enable_compression:
        impacts.append(
            SimulationImpact(
                label="Prompt compression",
                current_value="Disabled",
                projected_value="Enabled (~15% token reduction)",
                delta_pct=Decimal("-15"),
            )
        )

    parts: list[str] = []
    if body.proposed_model:
        parts.append(f"route from {body.current_model or 'current'} to {body.proposed_model}")
    if body.enable_cache:
        parts.append("enable caching")
    if body.enable_compression:
        parts.append("enable compression")
    desc = (
        f"Simulating: {', '.join(parts) or 'no changes'}. "
        f"Affects {affected:,} requests with ${float(current_cost):.4f} current spend. "
        f"Projected savings: ${float(projected_savings):.4f} ({float(savings_pct):.1f}%)."
    )

    return SimulationResult(
        affected_requests=affected,
        current_cost_usd=current_cost,
        projected_cost_usd=projected_cost,
        projected_savings_usd=projected_savings,
        savings_pct=savings_pct,
        current_avg_latency_ms=Decimal(str(round(current_lat, 1))) if current_lat else None,
        projected_latency_ms=proposed_lat,
        latency_delta_pct=lat_delta,
        quality_risk=quality_risk,
        confidence=confidence,
        impacts=impacts,
        description=desc,
    )


# ── Model Scorecards ────────────────────────────────────────────────────────


@router.get("/model-scorecards", response_model=ModelScorecardList)
async def model_scorecards(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    access_group_id: Annotated[str | None, Query()] = None,
    api_key_id: Annotated[str | None, Query()] = None,
) -> ModelScorecardList:
    """Aggregate quality scorecards per model: cost, latency, errors, cache, quality."""
    now = datetime.now(UTC)
    start = datetime.fromisoformat(from_dt) if from_dt else now - timedelta(days=30)
    end = datetime.fromisoformat(to_dt) if to_dt else now

    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= start,
        ProviderCall.created_at <= end,
    ]
    if access_group_id:
        import uuid as _uuid

        from runledger_api.models.access_groups import AccessGroupMember

        member_rows = (
            (
                await db.execute(
                    select(AccessGroupMember.user_id).where(
                        AccessGroupMember.group_id == _uuid.UUID(access_group_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        member_ids = [str(uid) for uid in member_rows]
        filters.append(ProviderCall.end_user_id.in_(member_ids))
    if api_key_id:
        import uuid as _uuid

        filters.append(ProviderCall.api_key_id == _uuid.UUID(api_key_id))

    stmt = (
        select(
            ProviderCall.model,
            ProviderCall.provider,
            func.sum(ProviderCall.cost_usd).label("total_cost"),
            func.count().label("call_count"),
            func.avg(ProviderCall.cost_usd).label("avg_cost"),
            func.avg(ProviderCall.latency_ms).label("avg_latency"),
            func.percentile_cont(0.95).within_group(ProviderCall.latency_ms).label("p95_latency"),
            func.sum(case((ProviderCall.status == "failed", 1), else_=0)).label("error_count"),
            func.sum(ProviderCall.input_tokens).label("input_tokens"),
            func.sum(ProviderCall.output_tokens).label("output_tokens"),
        )
        .where(*filters)
        .group_by(ProviderCall.model, ProviderCall.provider)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )

    rows = (await db.execute(stmt)).all()

    from runledger_api.models.gateway import GatewayRequest

    cache_stmt = (
        select(
            GatewayRequest.model_used,
            func.count().label("total"),
            func.sum(case((GatewayRequest.cache_hit.is_(True), 1), else_=0)).label("hits"),
        )
        .where(
            GatewayRequest.workspace_id == workspace.id,
            GatewayRequest.created_at >= start,
            GatewayRequest.created_at <= end,
        )
        .group_by(GatewayRequest.model_used)
    )
    cache_rows = {r.model_used: r for r in (await db.execute(cache_stmt)).all()}

    score_stmt = (
        select(
            ProviderCall.model,
            func.avg(ScoreEvent.value).label("avg_score"),
        )
        .join(ScoreEvent, ScoreEvent.run_id == ProviderCall.run_id)
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= start,
            ProviderCall.created_at <= end,
        )
        .group_by(ProviderCall.model)
    )
    score_map = {r.model: r.avg_score for r in (await db.execute(score_stmt)).all()}

    items = []
    for r in rows:
        cache_info = cache_rows.get(r.model)
        cache_hit_rate = None
        if cache_info and cache_info.total > 0:
            cache_hit_rate = Decimal(str(round(cache_info.hits / cache_info.total * 100, 1)))

        avg_score = score_map.get(r.model)

        items.append(
            ModelScorecard(
                model=r.model,
                provider=r.provider,
                total_cost_usd=Decimal(str(r.total_cost or 0)),
                call_count=r.call_count,
                avg_cost_per_call=Decimal(str(round(float(r.avg_cost or 0), 6))),
                avg_latency_ms=Decimal(str(round(float(r.avg_latency or 0), 1)))
                if r.avg_latency
                else None,
                p95_latency_ms=Decimal(str(round(float(r.p95_latency or 0), 1)))
                if r.p95_latency
                else None,
                error_rate=Decimal(str(round(r.error_count / r.call_count * 100, 2)))
                if r.call_count > 0
                else Decimal("0"),
                cache_hit_rate=cache_hit_rate,
                avg_quality_score=Decimal(str(round(float(avg_score), 2))) if avg_score else None,
                input_tokens=r.input_tokens or 0,
                output_tokens=r.output_tokens or 0,
            )
        )

    return ModelScorecardList(items=items, from_dt=start, to_dt=end)


@router.get("/api-key-footprint/{api_key_id}")
async def api_key_observe_footprint(
    api_key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    key = (
        await db.execute(
            select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.workspace_id == workspace.id)
        )
    ).scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found in this workspace")

    since = datetime.now(UTC) - timedelta(days=30)

    run_stmt = select(
        func.count(AgentRun.id).label("run_count"),
        func.coalesce(func.sum(AgentRun.total_cost_usd), 0).label("total_cost"),
        func.coalesce(
            func.sum(
                func.coalesce(AgentRun.total_input_tokens, 0)
                + func.coalesce(AgentRun.total_output_tokens, 0)
            ),
            0,
        ).label("total_tokens"),
    ).where(
        AgentRun.workspace_id == workspace.id,
        AgentRun.api_key_id == api_key_id,
        AgentRun.started_at >= since,
    )
    run_row = (await db.execute(run_stmt)).one()

    model_stmt = (
        select(ProviderCall.model)
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.api_key_id == api_key_id,
            ProviderCall.created_at >= since,
        )
        .group_by(ProviderCall.model)
    )
    models_used = [r.model for r in (await db.execute(model_stmt)).all()]

    recent_stmt = (
        select(AgentRun.id, AgentRun.status, AgentRun.total_cost_usd, AgentRun.started_at)
        .where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.api_key_id == api_key_id,
        )
        .order_by(AgentRun.started_at.desc())
        .limit(10)
    )
    recent_runs = [
        {
            "id": str(r.id),
            "status": r.status,
            "cost_usd": float(r.total_cost_usd or 0),
            "created_at": r.created_at.isoformat(),
        }
        for r in (await db.execute(recent_stmt)).all()
    ]

    return {
        "api_key_id": str(api_key_id),
        "key_name": key.name,
        "period_days": 30,
        "run_count": run_row.run_count,
        "total_cost_usd": float(run_row.total_cost),
        "total_tokens": int(run_row.total_tokens),
        "models_used": models_used,
        "recent_runs": recent_runs,
    }


@router.get("/model-budget-utilization", response_model=ModelBudgetUtilization)
async def model_budget_utilization(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _user: TenantUser = Depends(get_current_user),
    _rl: None = Depends(analytics_rate_limit),
):
    t_from = _default_from()
    t_to = _default_to()

    api_key_ids_result = await db.execute(
        select(ApiKey.id).where(ApiKey.workspace_id == workspace.id)
    )
    api_key_ids = [row[0] for row in api_key_ids_result.fetchall()]

    model_budgets_result = await db.execute(
        select(ModelBudget).where(
            ModelBudget.api_key_id.in_(api_key_ids) if api_key_ids else sa.literal(False)
        )
    )
    model_budgets = model_budgets_result.scalars().all()

    model_spend_result = await db.execute(
        select(
            ProviderCall.model,
            func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("spend"),
            func.count(ProviderCall.id).label("request_count"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
        )
        .group_by(ProviderCall.model)
    )
    spend_by_model = {
        row.model: (float(row.spend), row.request_count) for row in model_spend_result.fetchall()
    }

    budget_by_pattern: dict[str, ModelBudget] = {}
    for mb in model_budgets:
        budget_by_pattern[mb.model_pattern] = mb

    all_models = set(spend_by_model.keys()) | set(budget_by_pattern.keys())
    items: list[dict] = []
    for model in sorted(all_models):
        spend_info = spend_by_model.get(model, (0.0, 0))
        budget = budget_by_pattern.get(model)
        items.append(
            {
                "model": model,
                "spend_30d": spend_info[0],
                "request_count": spend_info[1],
                "budget_limit_usd": float(budget.max_spend_usd)
                if budget and budget.max_spend_usd
                else None,
                "budget_action": budget.action if budget else None,
                "period_type": budget.period_type if budget else None,
                "is_active": budget.is_active if budget else False,
            }
        )

    total_model_budgets = len(model_budgets)
    active_model_budgets = sum(1 for mb in model_budgets if mb.is_active)

    billing_period_count = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(BillingPeriod.workspace_id == workspace.id)
        )
    ).scalar() or 0

    open_billing_periods = (
        await db.execute(
            select(func.count(BillingPeriod.id)).where(
                BillingPeriod.workspace_id == workspace.id,
                BillingPeriod.status == "open",
            )
        )
    ).scalar() or 0

    chargeback_rule_count = (
        await db.execute(
            select(func.count(ChargebackRule.id)).where(ChargebackRule.workspace_id == workspace.id)
        )
    ).scalar() or 0

    return {
        "workspace_id": str(workspace.id),
        "period_days": 30,
        "models": items,
        "total_model_budgets": total_model_budgets,
        "active_model_budgets": active_model_budgets,
        "billing_periods": billing_period_count,
        "open_billing_periods": open_billing_periods,
        "chargeback_rules": chargeback_rule_count,
    }
