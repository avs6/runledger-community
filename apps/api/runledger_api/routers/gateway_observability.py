from __future__ import annotations

from fastapi import APIRouter

from runledger_api.core.config import settings
from runledger_api.models.budget_tiers import BudgetTier
from runledger_api.models.model_budgets import ModelBudget

from .gateway_shared import *

router = APIRouter()


@router.get("/deployments/health", response_model=GatewayDeploymentHealthList)
async def list_gateway_deployment_health(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayDeploymentHealthList:
    workspace = auth[0]
    rows = (
        (
            await db.execute(
                select(GatewayRoute)
                .where(GatewayRoute.workspace_id == workspace.id)
                .order_by(GatewayRoute.alias.asc(), GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    return GatewayDeploymentHealthList(
        items=[
            GatewayDeploymentHealthItem(
                route_id=row.id,
                alias=row.alias,
                provider=row.provider,
                target_model=row.target_model,
                deployment_status=row.deployment_status,
                health_summary=row.health_summary,
                last_health_check_at=row.last_health_check_at,
                consecutive_health_failures=row.consecutive_health_failures,
            )
            for row in rows
        ]
    )


# ── Request log (routing log) ─────────────────────────────────────────────────


@router.get("/requests", response_model=GatewayRequestList)
async def list_gateway_requests(
    auth: OrgAdminDep,
    db: DbDep,
    alias: str | None = Query(None, description="Filter by model alias"),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> GatewayRequestList:
    """
    Return recent gateway requests with routing decision reasons.
    Useful for auditing which policy selected which route and why.
    """
    workspace = auth[0]
    stmt = select(GatewayRequest).where(GatewayRequest.workspace_id == workspace.id)

    if alias:
        stmt = stmt.where(GatewayRequest.model_requested == alias)
    if status_filter:
        stmt = stmt.where(GatewayRequest.status == status_filter)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(GatewayRequest.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return GatewayRequestList(
        items=[GatewayRequestResponse.model_validate(r) for r in items],
        total=total,
    )


# ── Stats ──────────────────────────────────────────────────────────────────────


@router.get("/stats", response_model=GatewayStats)
async def gateway_stats(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayStats:
    """Aggregate gateway request stats per route for the workspace."""
    workspace = auth[0]
    stmt = (
        select(
            GatewayRequest.route_id,
            func.count(GatewayRequest.id).label("total"),
            func.count(GatewayRequest.id)
            .filter(GatewayRequest.cache_hit.is_(True))
            .label("cache_hits"),
            func.avg(GatewayRequest.latency_ms).label("avg_latency"),
            func.count(GatewayRequest.id).filter(GatewayRequest.status == "error").label("errors"),
        )
        .where(GatewayRequest.workspace_id == workspace.id)
        .group_by(GatewayRequest.route_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Load route aliases for joining
    route_ids = [r.route_id for r in rows if r.route_id]
    alias_map: dict[uuid.UUID, str] = {}
    if route_ids:
        route_stmt = select(GatewayRoute.id, GatewayRoute.alias).where(
            GatewayRoute.id.in_(route_ids)
        )
        route_result = await db.execute(route_stmt)
        alias_map = {row.id: row.alias for row in route_result.all()}

    route_stats: list[GatewayRouteStats] = []
    total_requests = 0
    total_cache_hits = 0
    latency_weighted_sum = Decimal("0")
    latency_weight = 0

    for row in rows:
        total = int(row.total)
        cache_hits = int(row.cache_hits)
        errors = int(row.errors)
        avg_lat = (
            Decimal(str(row.avg_latency)).quantize(Decimal("0.01")) if row.avg_latency else None
        )
        alias = alias_map.get(row.route_id, "unknown") if row.route_id else "cache_only"
        hit_rate = Decimal(str(round(cache_hits / total, 4))) if total else Decimal("0")

        route_stats.append(
            GatewayRouteStats(
                route_id=row.route_id,
                alias=alias,
                total_requests=total,
                cache_hits=cache_hits,
                cache_hit_rate=hit_rate,
                avg_latency_ms=avg_lat,
                error_count=errors,
            )
        )
        total_requests += total
        total_cache_hits += cache_hits
        if avg_lat is not None:
            latency_weighted_sum += avg_lat * Decimal(total)
            latency_weight += total

    overall_hit_rate = (
        Decimal(str(round(total_cache_hits / total_requests, 4)))
        if total_requests
        else Decimal("0")
    )
    overall_latency = (
        (latency_weighted_sum / Decimal(latency_weight)).quantize(Decimal("0.01"))
        if latency_weight
        else None
    )

    return GatewayStats(
        total_requests=total_requests,
        cache_hits=total_cache_hits,
        cache_hit_rate=overall_hit_rate,
        avg_latency_ms=overall_latency,
        routes=route_stats,
    )


@router.get("/rate-limits/overview", response_model=GatewayRateLimitOverview)
async def gateway_rate_limit_overview(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRateLimitOverview:
    workspace = auth[0]

    route_rows = (
        (
            await db.execute(
                select(GatewayRoute.alias)
                .where(
                    GatewayRoute.workspace_id == workspace.id,
                    GatewayRoute.per_user_rpm_limit.is_not(None),
                )
                .order_by(GatewayRoute.alias.asc())
            )
        )
        .scalars()
        .all()
    )

    passthrough_rows = (
        (
            await db.execute(
                select(GatewayPassThroughEndpoint.slug)
                .where(
                    GatewayPassThroughEndpoint.workspace_id == workspace.id,
                    GatewayPassThroughEndpoint.rate_limit_rpm.is_not(None),
                )
                .order_by(GatewayPassThroughEndpoint.slug.asc())
            )
        )
        .scalars()
        .all()
    )

    budget_tier_count = (
        await db.execute(
            select(func.count(BudgetTier.id)).where(
                BudgetTier.workspace_id == workspace.id,
                BudgetTier.is_active.is_(True),
                sa.or_(BudgetTier.rpm_limit.is_not(None), BudgetTier.tpm_limit.is_not(None)),
            )
        )
    ).scalar_one()

    model_budget_count = (
        await db.execute(
            select(func.count(ModelBudget.id))
            .select_from(ModelBudget)
            .join(ApiKey, ApiKey.id == ModelBudget.api_key_id)
            .where(
                ApiKey.workspace_id == workspace.id,
                ModelBudget.is_active.is_(True),
                sa.or_(ModelBudget.rpm_limit.is_not(None), ModelBudget.tpm_limit.is_not(None)),
            )
        )
    ).scalar_one()

    return GatewayRateLimitOverview(
        tiers=[
            GatewayRateLimitTier(
                key="ingest",
                name="Ingest",
                description="Gateway runtime, OTLP ingest, and write-heavy request paths.",
                rpm=settings.ingest_rate_limit_per_minute,
                endpoints=["/gateway/*", "/v1/chat/completions", "/otlp/*"],
            ),
            GatewayRateLimitTier(
                key="analytics",
                name="Analytics",
                description="Read-oriented dashboards, reports, and observability queries.",
                rpm=settings.analytics_rate_limit_per_minute,
                endpoints=["/analytics/*", "/runs/*", "/outcomes/*"],
            ),
            GatewayRateLimitTier(
                key="management",
                name="Management",
                description="Admin CRUD for settings, budgets, keys, and governance surfaces.",
                rpm=settings.management_rate_limit_per_minute,
                endpoints=["/gateway/config/*", "/budgets/*", "/settings/*"],
            ),
            GatewayRateLimitTier(
                key="system",
                name="System",
                description="Privileged platform and auth surfaces with tighter safety limits.",
                rpm=settings.system_rate_limit_per_minute,
                endpoints=["/auth/*", "/health/*", "/system/*"],
            ),
        ],
        route_rate_limited_count=len(route_rows),
        route_rate_limited_aliases=list(route_rows),
        passthrough_rate_limited_count=len(passthrough_rows),
        passthrough_rate_limited_slugs=list(passthrough_rows),
        budget_tier_rate_limited_count=int(budget_tier_count or 0),
        model_budget_rate_limited_count=int(model_budget_count or 0),
    )


@router.get("/benchmarks/compare", response_model=GatewayBenchmarkComparisonList)
async def gateway_benchmark_comparison(
    auth: OrgAdminDep,
    db: DbDep,
    days: int = Query(7, ge=1, le=30),
    alias: str | None = Query(default=None),
) -> GatewayBenchmarkComparisonList:
    workspace = auth[0]
    since = datetime.now(UTC) - timedelta(days=days)
    stmt = select(GatewayRequest).where(
        GatewayRequest.workspace_id == workspace.id,
        GatewayRequest.created_at >= since,
        GatewayRequest.status != "cache_hit",
    )
    if alias:
        stmt = stmt.where(GatewayRequest.model_requested == alias)
    items = list((await db.execute(stmt)).scalars().all())
    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        alias_key = item.model_requested
        bucket = buckets.setdefault(
            alias_key,
            {
                "request_count": 0,
                "provider_latencies": [],
                "end_to_end": [],
                "overheads": [],
                "timestamps": [],
            },
        )
        cfg = item.config_fingerprint or {}
        provider_latency = cfg.get("provider_latency_ms")
        total_wall = cfg.get("total_wall_ms")
        gateway_overhead = cfg.get("gateway_overhead_ms")
        if provider_latency is not None:
            bucket["provider_latencies"].append(float(provider_latency))
        if total_wall is not None:
            bucket["end_to_end"].append(float(total_wall))
        if gateway_overhead is not None:
            bucket["overheads"].append(float(gateway_overhead))
        bucket["request_count"] += 1
        bucket["timestamps"].append(item.created_at)

    def _percentile(values: list[float], q: float) -> Decimal | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
        return Decimal(str(round(ordered[index], 2)))

    rows: list[GatewayBenchmarkComparisonItem] = []
    for alias_key, bucket in sorted(buckets.items()):
        timestamps = sorted(bucket["timestamps"])
        minutes = max(
            ((timestamps[-1] - timestamps[0]).total_seconds() / 60.0)
            if len(timestamps) > 1
            else 1.0,
            1.0,
        )
        provider_avg = (
            Decimal(
                str(round(sum(bucket["provider_latencies"]) / len(bucket["provider_latencies"]), 2))
            )
            if bucket["provider_latencies"]
            else None
        )
        end_to_end_avg = (
            Decimal(str(round(sum(bucket["end_to_end"]) / len(bucket["end_to_end"]), 2)))
            if bucket["end_to_end"]
            else None
        )
        overhead_avg = (
            Decimal(str(round(sum(bucket["overheads"]) / len(bucket["overheads"]), 2)))
            if bucket["overheads"]
            else None
        )
        overhead_pct = None
        if provider_avg is not None and provider_avg > 0 and overhead_avg is not None:
            overhead_pct = Decimal(str(round(float(overhead_avg / provider_avg), 4)))
        rows.append(
            GatewayBenchmarkComparisonItem(
                alias=alias_key,
                request_count=bucket["request_count"],
                throughput_rpm=Decimal(str(round(bucket["request_count"] / minutes, 4))),
                p50_gateway_overhead_ms=_percentile(bucket["overheads"], 0.50),
                p95_gateway_overhead_ms=_percentile(bucket["overheads"], 0.95),
                p99_gateway_overhead_ms=_percentile(bucket["overheads"], 0.99),
                avg_provider_latency_ms=provider_avg,
                avg_end_to_end_latency_ms=end_to_end_avg,
                avg_gateway_overhead_ms=overhead_avg,
                overhead_vs_provider_pct=overhead_pct,
            )
        )
    return GatewayBenchmarkComparisonList(items=rows)
