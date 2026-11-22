"""Run economics, workflows, version compare, regressions, annotations, export and email report."""

from __future__ import annotations

from ._shared import *  # noqa: F403

# ── /analytics/economics/{run_id} ────────────────────────────────────────────


@router.get("/economics/{run_id}", response_model=RunEconomics)
async def run_economics(
    run_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunEconomics:
    """Per-run cost breakdown by span type and by model."""
    # Verify run belongs to this workspace
    run_stmt = select(AgentRun).where(
        AgentRun.id == run_id,
        AgentRun.workspace_id == workspace.id,
    )
    run_result = await db.execute(run_stmt)
    run = run_result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    # Span-type cost breakdown
    span_stmt = (
        select(
            Span.span_type,
            func.coalesce(func.sum(Span.cost_usd), Decimal(0)).label("cost_usd"),
        )
        .where(Span.run_id == run_id)
        .group_by(Span.span_type)
        .order_by(func.sum(Span.cost_usd).desc().nulls_last())
    )
    span_result = await db.execute(span_stmt)
    span_rows = span_result.all()

    # Model cost breakdown (provider_calls = authoritative cost source)
    model_stmt = (
        select(
            ProviderCall.model,
            ProviderCall.provider,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label("cost_usd"),
            func.count(ProviderCall.id).label("call_count"),
        )
        .where(ProviderCall.run_id == run_id)
        .group_by(ProviderCall.model, ProviderCall.provider)
        .order_by(func.sum(ProviderCall.cost_usd).desc().nulls_last())
    )
    model_result = await db.execute(model_stmt)
    model_rows = model_result.all()

    # Retry cost: child LLM spans (parent_span_id IS NOT NULL, span_type='llm')
    retry_stmt = select(func.coalesce(func.sum(Span.cost_usd), Decimal(0))).where(
        Span.run_id == run_id,
        Span.parent_span_id.is_not(None),
        Span.span_type == "llm",
    )
    retry_result = await db.execute(retry_stmt)
    retry_cost: Decimal = retry_result.scalar() or Decimal(0)

    # Total from provider_calls (authoritative)
    total_cost = sum((row.cost_usd for row in model_rows), Decimal(0))

    return RunEconomics(
        run_id=run_id,
        total_cost_usd=total_cost,
        cost_by_span_type=[
            SpanTypeCost(span_type=str(row.span_type), cost_usd=row.cost_usd) for row in span_rows
        ],
        cost_by_model=[
            ModelCost(
                model=row.model,
                provider=row.provider,
                cost_usd=row.cost_usd,
                call_count=row.call_count,
            )
            for row in model_rows
        ],
        retry_cost=retry_cost,
    )


# ── /analytics/workflows/top ─────────────────────────────────────────────────


@router.get("/workflows/top", response_model=WorkflowTopList)
async def top_workflows(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    metric: Annotated[str, Query(pattern="^(cost|latency)$")] = "cost",
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> WorkflowTopList:
    """Top workflows ranked by average cost or latency."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    order_col = (
        func.avg(AgentRun.total_cost_usd).desc().nulls_last()
        if metric == "cost"
        else func.avg(func.extract("epoch", AgentRun.ended_at - AgentRun.started_at) * 1000)
        .desc()
        .nulls_last()
    )

    # Query 1: run-level aggregates from agent_runs (correct avg/p95)
    run_stmt = (
        select(
            AgentRun.feature_tag,
            AgentRun.application_id,
            func.count(AgentRun.id).label("run_count"),
            func.coalesce(func.avg(AgentRun.total_cost_usd), Decimal(0)).label("avg_cost_usd"),
            func.percentile_cont(0.95).within_group(AgentRun.total_cost_usd).label("p95_cost_usd"),
            func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal(0)).label("total_cost_usd"),
        )
        .where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.started_at >= t_from,
            AgentRun.started_at < t_to,
        )
        .group_by(AgentRun.feature_tag, AgentRun.application_id)
        .order_by(order_col)
        .limit(limit)
    )
    run_result = await db.execute(run_stmt)
    run_rows = run_result.all()

    # Query 2: call counts from provider_calls (separate to avoid join-fan-out)
    call_stmt = (
        select(
            AgentRun.feature_tag,
            AgentRun.application_id,
            func.count(ProviderCall.id).label("call_count"),
        )
        .join(AgentRun, AgentRun.id == ProviderCall.run_id)
        .where(
            ProviderCall.workspace_id == workspace.id,
            ProviderCall.created_at >= t_from,
            ProviderCall.created_at < t_to,
        )
        .group_by(AgentRun.feature_tag, AgentRun.application_id)
    )
    call_result = await db.execute(call_stmt)
    call_rows = call_result.all()

    call_map: dict[tuple[str | None, str | None], int] = {
        (row.feature_tag, str(row.application_id) if row.application_id else None): row.call_count
        for row in call_rows
    }

    items = [
        WorkflowSummary(
            feature_tag=row.feature_tag,
            application_id=str(row.application_id) if row.application_id else None,
            run_count=row.run_count,
            avg_cost_usd=row.avg_cost_usd,
            p95_cost_usd=Decimal(row.p95_cost_usd) if row.p95_cost_usd is not None else Decimal(0),
            total_cost_usd=row.total_cost_usd,
            call_count=call_map.get(
                (row.feature_tag, str(row.application_id) if row.application_id else None), 0
            ),
        )
        for row in run_rows
    ]

    return WorkflowTopList(metric=metric, items=items)


# ── /analytics/compare ────────────────────────────────────────────────────────


@router.get("/compare", response_model=VersionCompareResult)
async def version_compare(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    baseline_version: Annotated[str, Query()],
    comparison_version: Annotated[str, Query()],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> VersionCompareResult:
    """Compare cost, token, and latency metrics between two deployment versions."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    def _run_stats_stmt(version: str) -> Any:
        return select(
            func.count(AgentRun.id).label("run_count"),
            func.coalesce(func.avg(AgentRun.total_cost_usd), Decimal(0)).label("avg_cost_usd"),
            func.coalesce(func.avg(AgentRun.total_input_tokens), Decimal(0)).label(
                "avg_input_tokens"
            ),
            func.coalesce(func.avg(AgentRun.total_output_tokens), Decimal(0)).label(
                "avg_output_tokens"
            ),
            func.avg(func.extract("epoch", AgentRun.ended_at - AgentRun.started_at) * 1000).label(
                "avg_latency_ms"
            ),
        ).where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.deployment_version == version,
            AgentRun.started_at >= t_from,
            AgentRun.started_at < t_to,
        )

    def _span_costs_stmt(version: str) -> Any:
        return (
            select(
                Span.span_type,
                func.coalesce(func.sum(Span.cost_usd), Decimal(0)).label("cost_usd"),
            )
            .join(AgentRun, AgentRun.id == Span.run_id)
            .where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.deployment_version == version,
                AgentRun.started_at >= t_from,
                AgentRun.started_at < t_to,
            )
            .group_by(Span.span_type)
        )

    base_result = await db.execute(_run_stats_stmt(baseline_version))
    base_row = base_result.one()

    cmp_result = await db.execute(_run_stats_stmt(comparison_version))
    cmp_row = cmp_result.one()

    base_span_result = await db.execute(_span_costs_stmt(baseline_version))
    base_span_rows = base_span_result.all()

    cmp_span_result = await db.execute(_span_costs_stmt(comparison_version))
    cmp_span_rows = cmp_span_result.all()

    def _delta(cmp_val: Decimal, base_val: Decimal) -> Decimal | None:
        if not base_val or base_val == Decimal(0):
            return None
        return (cmp_val - base_val) / base_val * Decimal(100)

    base_summary = VersionSummary(
        version=baseline_version,
        run_count=base_row.run_count,
        avg_cost_usd=base_row.avg_cost_usd,
        avg_input_tokens=base_row.avg_input_tokens,
        avg_output_tokens=base_row.avg_output_tokens,
        avg_latency_ms=base_row.avg_latency_ms,
    )
    cmp_summary = VersionSummary(
        version=comparison_version,
        run_count=cmp_row.run_count,
        avg_cost_usd=cmp_row.avg_cost_usd,
        avg_input_tokens=cmp_row.avg_input_tokens,
        avg_output_tokens=cmp_row.avg_output_tokens,
        avg_latency_ms=cmp_row.avg_latency_ms,
    )

    # Build span-type delta map
    base_span_map = {str(r.span_type): r.cost_usd for r in base_span_rows}
    cmp_span_map = {str(r.span_type): r.cost_usd for r in cmp_span_rows}
    all_span_types = sorted(set(base_span_map) | set(cmp_span_map))
    by_span_type = [
        SpanTypeDelta(
            span_type=st,
            baseline_cost=base_span_map.get(st, Decimal(0)),
            comparison_cost=cmp_span_map.get(st, Decimal(0)),
            delta_pct=_delta(cmp_span_map.get(st, Decimal(0)), base_span_map.get(st, Decimal(0))),
        )
        for st in all_span_types
    ]

    base_latency = Decimal(str(base_row.avg_latency_ms)) if base_row.avg_latency_ms else None
    cmp_latency = Decimal(str(cmp_row.avg_latency_ms)) if cmp_row.avg_latency_ms else None

    return VersionCompareResult(
        baseline=base_summary,
        comparison=cmp_summary,
        cost_delta_pct=_delta(cmp_row.avg_cost_usd, base_row.avg_cost_usd),
        token_delta_pct=_delta(cmp_row.avg_input_tokens, base_row.avg_input_tokens),
        latency_delta_pct=(
            _delta(cmp_latency, base_latency) if base_latency and cmp_latency else None
        ),
        by_span_type=by_span_type,
    )


@router.get("/regressions", response_model=RegressionList)
async def regressions(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    page: PageDep = None,  # type: ignore[assignment]
    response: Response = None,  # type: ignore[assignment]
) -> RegressionList:
    """Detect feature workflows where avg cost jumped >20% vs prior week."""
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, _default_from())
    duration = t_to - t_from
    prior_from = t_from - duration
    prior_to = t_from

    def _window_stmt(w_from: object, w_to: object) -> Any:
        return (
            select(
                AgentRun.feature_tag,
                func.avg(AgentRun.total_cost_usd).label("avg_cost"),
                func.count(AgentRun.id).label("run_count"),
            )
            .where(
                AgentRun.workspace_id == workspace.id,
                AgentRun.started_at >= w_from,
                AgentRun.started_at < w_to,
                AgentRun.total_cost_usd.is_not(None),
            )
            .group_by(AgentRun.feature_tag)
        )

    curr_result = await db.execute(_window_stmt(t_from, t_to))
    curr_rows = curr_result.all()

    prior_result = await db.execute(_window_stmt(prior_from, prior_to))
    prior_rows = prior_result.all()

    prior_map: dict[str | None, tuple[Decimal, int]] = {
        row.feature_tag: (row.avg_cost, row.run_count) for row in prior_rows
    }

    items: list[RegressionItem] = []
    for row in curr_rows:
        if row.run_count < _REGRESSION_MIN_RUNS:
            continue
        prior = prior_map.get(row.feature_tag)
        if prior is None:
            continue
        prior_avg, prior_run_count = prior
        if not prior_avg or prior_avg == Decimal(0):
            continue
        curr_avg = Decimal(str(row.avg_cost))
        change = (curr_avg - prior_avg) / prior_avg
        if change > _REGRESSION_THRESHOLD:
            items.append(
                RegressionItem(
                    feature_tag=row.feature_tag,
                    current_avg_cost=curr_avg,
                    prior_avg_cost=prior_avg,
                    change_pct=change * Decimal(100),
                    run_count=row.run_count,
                    prior_run_count=prior_run_count,
                )
            )

    return RegressionList(
        items=paginate_list(items, page, response),
        from_dt=t_from.isoformat(),
        to_dt=t_to.isoformat(),
    )


# ── /analytics/annotations ────────────────────────────────────────────────────


@router.post(
    "/annotations",
    response_model=AnnotationResponse,
    status_code=201,
    dependencies=[Depends(require_workspace_writer)],
)
async def create_annotation(
    body: AnnotationCreate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationResponse:
    """Create a team annotation anchored to a date (and optionally a version)."""
    annotation = Annotation(
        workspace_id=workspace.id,
        note=body.note,
        annotation_date=body.annotation_date,
        version=body.version,
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    return AnnotationResponse(
        id=str(annotation.id),
        note=annotation.note,
        annotation_date=annotation.annotation_date,
        version=annotation.version,
        created_at=annotation.created_at,
    )


@router.get("/annotations", response_model=AnnotationList)
async def list_annotations(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    version: Annotated[str | None, Query()] = None,
    page: PageDep = None,  # type: ignore[assignment]
    response: Response = None,  # type: ignore[assignment]
) -> AnnotationList:
    """List annotations for the workspace, optionally filtered by date range or version."""
    stmt = (
        select(Annotation)
        .where(Annotation.workspace_id == workspace.id)
        .order_by(Annotation.annotation_date.desc())
    )
    if from_dt:
        stmt = stmt.where(Annotation.annotation_date >= _parse_dt(from_dt, _default_from()).date())
    if to_dt:
        stmt = stmt.where(Annotation.annotation_date <= _parse_dt(to_dt, _default_to()).date())
    if version:
        stmt = stmt.where(Annotation.version == version)

    rows = await paginate(db, stmt.order_by(Annotation.id), page, response)

    return AnnotationList(
        items=[
            AnnotationResponse(
                id=str(row.id),
                note=row.note,
                annotation_date=row.annotation_date,
                version=row.version,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


@router.get("/export", response_model=None)
async def analytics_export(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Annotated[str, Query(pattern="^(csv|json)$")] = "json",
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> StreamingResponse | dict[str, Any]:
    """Bulk export of daily spend data from usage_daily, ordered by date desc."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    stmt = (
        select(UsageDaily)
        .where(
            UsageDaily.workspace_id == workspace.id,
            UsageDaily.day >= t_from.date(),
            UsageDaily.day <= t_to.date(),
        )
        .order_by(UsageDaily.day.desc())
    )

    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        {
            "date": str(row.day),
            "provider": row.provider,
            "model": row.model,
            "cost_usd": str(row.cost_usd),
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "call_count": row.call_count,
        }
        for row in rows
    ]

    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(items)
        buf.seek(0)

        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
        )

    return {"items": items}


# ── /analytics/email-report ───────────────────────────────────────────────────


@router.post(
    "/email-report",
    response_model=None,
    dependencies=[Depends(require_workspace_writer), Depends(analytics_rate_limit)],
)
async def email_analytics_report(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    window_days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> dict[str, Any]:
    """Email a usage analytics report to all workspace admins."""
    from runledger_api.services import kafka_export  # noqa: PLC0415
    from runledger_api.services.email import send_analytics_report_email  # noqa: PLC0415
    from runledger_api.services.email_utils import get_workspace_admin_users  # noqa: PLC0415

    t_to = _default_to()
    t_from = t_to - timedelta(days=window_days)

    stmt = (
        select(UsageDaily)
        .where(
            UsageDaily.workspace_id == workspace.id,
            UsageDaily.day >= t_from.date(),
            UsageDaily.day <= t_to.date(),
        )
        .order_by(UsageDaily.day.desc())
    )
    result = await db.execute(stmt)
    rows_orm = result.scalars().all()

    items = [
        {
            "date": str(row.day),
            "provider": row.provider,
            "model": row.model,
            "cost_usd": str(row.cost_usd),
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "call_count": row.call_count,
        }
        for row in rows_orm
    ]

    total_cost = str(round(sum((float(str(r["cost_usd"])) for r in items), 0.0), 6))
    period_label = f"Last {window_days} days"
    ws_name = getattr(workspace, "name", str(workspace.id))

    admins = await get_workspace_admin_users(db, workspace.id)
    for u in admins:
        await send_analytics_report_email(
            to_email=u.email,
            full_name=u.full_name,
            period_label=period_label,
            rows=items,
            total_cost=total_cost,
            workspace_name=ws_name,
        )
        await kafka_export.publish_event(
            db,
            workspace_id=workspace.id,
            event_type="email.report.sent",
            payload={
                "run_id": str(workspace.id),
                "workspace_name": ws_name,
                "recipient": u.email,
                "cadence": "manual",
                "period_label": period_label,
                "total_cost_usd": total_cost,
                "idempotency_key": f"email-report-manual:{workspace.id}:{u.email}:{window_days}:{t_to.date()}",
                "source": "runledger.email",
                "event_summary": "Manual analytics report sent",
            },
        )

    return {"queued": True, "recipients": len(admins)}
