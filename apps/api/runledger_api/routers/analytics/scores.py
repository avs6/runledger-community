"""Score summaries, score regressions, cost-quality and best-value models."""

from __future__ import annotations

from ._shared import *  # noqa: F403


@router.get("/scores/summary", response_model=ScoreSummary)
async def score_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> ScoreSummary:
    """Average score values per score name for the current window vs prior window."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, _default_from())
    duration = t_to - t_from
    prior_from = t_from - duration
    prior_to = t_from

    def _score_window_stmt(w_from: object, w_to: object) -> Any:
        return (
            select(
                ScoreEvent.name,
                func.avg(ScoreEvent.value).label("avg_value"),
                func.count(ScoreEvent.id).label("sample_count"),
            )
            .where(
                ScoreEvent.workspace_id == workspace.id,
                ScoreEvent.created_at >= w_from,
                ScoreEvent.created_at < w_to,
            )
            .group_by(ScoreEvent.name)
        )

    curr_result = await db.execute(_score_window_stmt(t_from, t_to))
    curr_rows = curr_result.all()

    prior_result = await db.execute(_score_window_stmt(prior_from, prior_to))
    prior_rows = prior_result.all()

    prior_map: dict[str, tuple[Decimal, int]] = {
        row.name: (Decimal(str(row.avg_value)), row.sample_count) for row in prior_rows
    }

    items: list[ScoreSummaryItem] = []
    for row in curr_rows:
        curr_avg = Decimal(str(row.avg_value))
        prior = prior_map.get(row.name)
        prev_avg: Decimal | None = None
        change_pct: Decimal | None = None
        if prior is not None:
            prev_avg, prior_count = prior
            if prior_count > 0 and prev_avg and prev_avg != Decimal(0):
                change_pct = (curr_avg - prev_avg) / prev_avg * Decimal(100)

        items.append(
            ScoreSummaryItem(
                name=row.name,
                avg_value=curr_avg,
                p50=None,
                p90=None,
                sample_count=row.sample_count,
                prev_avg_value=prev_avg,
                change_pct=change_pct,
            )
        )

    return ScoreSummary(items=items)


# ── /analytics/scores/regressions ─────────────────────────────────────────────


@router.get("/scores/regressions", response_model=list[ScoreRegressionItem])
async def score_regressions(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> list[ScoreRegressionItem]:
    """Detect score names where avg value dropped >20% vs prior window (sample_count >= 3)."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, _default_from())
    duration = t_to - t_from
    prior_from = t_from - duration
    prior_to = t_from

    def _score_window_stmt(w_from: object, w_to: object) -> Any:
        return (
            select(
                ScoreEvent.name,
                func.avg(ScoreEvent.value).label("avg_value"),
                func.count(ScoreEvent.id).label("sample_count"),
            )
            .where(
                ScoreEvent.workspace_id == workspace.id,
                ScoreEvent.created_at >= w_from,
                ScoreEvent.created_at < w_to,
            )
            .group_by(ScoreEvent.name)
        )

    curr_result = await db.execute(_score_window_stmt(t_from, t_to))
    curr_rows = curr_result.all()

    prior_result = await db.execute(_score_window_stmt(prior_from, prior_to))
    prior_rows = prior_result.all()

    prior_map: dict[str, Decimal] = {row.name: Decimal(str(row.avg_value)) for row in prior_rows}

    regressions: list[ScoreRegressionItem] = []
    for row in curr_rows:
        if row.sample_count < _SCORE_REGRESSION_MIN_SAMPLES:
            continue
        prior_avg = prior_map.get(row.name)
        if prior_avg is None or prior_avg == Decimal(0):
            continue
        curr_avg = Decimal(str(row.avg_value))
        change = (curr_avg - prior_avg) / prior_avg
        # Negative change means degradation; threshold is >20% drop
        if change < -_SCORE_REGRESSION_THRESHOLD:
            regressions.append(
                ScoreRegressionItem(
                    name=row.name,
                    current_avg=curr_avg,
                    prior_avg=prior_avg,
                    change_pct=change * Decimal(100),
                    sample_count=row.sample_count,
                )
            )

    return regressions


# ── Cost-quality analytics ─────────────────────────────────────────────────────


@router.get("/scores/cost-quality", response_model=CostQualityResponse)
async def cost_quality(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    score_name: Annotated[str | None, Query()] = None,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> CostQualityResponse:
    """
    Return avg cost vs avg score per model over the selected window.
    Joins agent_runs → provider_calls → score_events on run_id.
    """
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    from runledger_api.models.evaluators import Evaluator  # noqa: F401

    # Subquery: avg cost per run (from provider_calls)
    cost_sq = (
        select(
            ProviderCall.run_id.label("run_id"),
            ProviderCall.model.label("model"),
            func.sum(ProviderCall.cost_usd).label("run_cost"),
        )
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
        )
        .group_by(ProviderCall.run_id, ProviderCall.model)
        .subquery()
    )

    # Subquery: avg score per run
    score_filter = [
        ScoreEvent.workspace_id == workspace.id,
        ScoreEvent.created_at >= t_from,
        ScoreEvent.created_at < t_to,
    ]
    if score_name:
        score_filter.append(ScoreEvent.name == score_name)

    score_sq = (
        select(
            ScoreEvent.run_id.label("run_id"),
            func.avg(ScoreEvent.value).label("avg_score"),
        )
        .where(*score_filter)
        .group_by(ScoreEvent.run_id)
        .subquery()
    )

    stmt = (
        select(
            cost_sq.c.model,
            func.avg(cost_sq.c.run_cost).label("avg_cost_usd"),
            func.avg(score_sq.c.avg_score).label("avg_score"),
            func.count(cost_sq.c.run_id.distinct()).label("run_count"),
        )
        .outerjoin(score_sq, cost_sq.c.run_id == score_sq.c.run_id)
        .group_by(cost_sq.c.model)
        .order_by(func.avg(cost_sq.c.run_cost).asc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        CostQualityPoint(
            model=row.model or "unknown",
            avg_cost_usd=str(round(Decimal(str(row.avg_cost_usd or 0)), 6)),
            avg_score=str(round(Decimal(str(row.avg_score)), 4))
            if row.avg_score is not None
            else None,
            run_count=row.run_count,
        )
        for row in rows
    ]
    return CostQualityResponse(items=items)


@router.get("/scores/best-value", response_model=BestValueResponse)
async def best_value_models(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    score_name: Annotated[str | None, Query()] = None,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    min_runs: Annotated[int, Query(ge=1)] = 3,
) -> BestValueResponse:
    """
    Return models ranked by quality/cost ratio (best value = high score, low cost).
    Excludes models with avg_cost_usd == 0 to avoid division by zero.
    """
    cq = await cost_quality(workspace, db, score_name, from_dt, to_dt)

    best: list[BestValueModel] = []
    for pt in cq.items:
        if pt.avg_score is None:
            continue
        avg_cost = float(pt.avg_cost_usd)
        avg_score = float(pt.avg_score)
        if avg_cost <= 0 or pt.run_count < min_runs:
            continue
        value_score = avg_score / avg_cost
        best.append(
            BestValueModel(
                model=pt.model,
                avg_cost_usd=pt.avg_cost_usd,
                avg_score=pt.avg_score,
                value_score=str(round(value_score, 4)),
                run_count=pt.run_count,
            )
        )

    best.sort(key=lambda x: float(x.value_score), reverse=True)
    return BestValueResponse(items=best)
