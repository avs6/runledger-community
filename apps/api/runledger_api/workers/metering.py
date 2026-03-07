"""
Celery metering workers for RunLedger.

Workers
-------
sync_pricing_from_file_worker
    Reads config/pricing.yml and upserts global provider_pricing rows.
    Runs every 6 hours via Celery Beat (and also on API startup).

cost_enrichment_worker
    Picks up provider_calls with NULL cost_usd (and known token counts), computes
    cost using the pricing engine, and rolls the result up to the parent span and
    agent_run.  Runs every 60 seconds via Celery Beat.

rollup_hourly_worker
    Full recompute of usage_hourly for a 2-hour look-back window.  Idempotent:
    deletes existing rows for the window then inserts fresh aggregates.
    Runs every 30 minutes.

rollup_daily_worker
    Aggregates usage_hourly → usage_daily for the previous calendar day (UTC).
    Runs daily at 00:05 UTC.

data_quality_worker
    Flags provider_calls missing tokens or cost.  Runs every hour.

replay_backfill
    One-shot task: re-runs cost enrichment and rollups for an arbitrary time
    range.  Called manually after a pricing correction.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import ProviderCall
from runledger_api.models.metering import DataQualityIssue, UsageDaily, UsageHourly
from runledger_api.services.budgets import (
    _matching_budgets,
    fire_breach,
    get_budget_spend,
    get_workspace_budgets_cached,
    incr_budget_spend,
)
from runledger_api.services.pricing import calculate_cost

log = structlog.get_logger()

# ── Shared session factory (NullPool — safe for Celery --pool=solo) ───────────


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── cost_enrichment_worker ────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="metering.cost_enrichment",
    max_retries=3,
    default_retry_delay=10,
)
def cost_enrichment_worker() -> dict[str, int]:
    """Compute cost for all uncost provider_calls and roll up to spans + runs."""
    return asyncio.run(_run_cost_enrichment())


async def _run_cost_enrichment() -> dict[str, int]:
    from redis.asyncio import Redis  # noqa: PLC0415

    factory = _make_session_factory()
    enriched = 0

    redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        async with factory() as session:
            # Fetch up to 500 provider_calls that have tokens but no cost
            stmt = (
                select(ProviderCall)
                .where(
                    ProviderCall.cost_usd.is_(None),
                    ProviderCall.input_tokens.is_not(None),
                )
                .order_by(ProviderCall.created_at)
                .limit(500)
            )
            result = await session.execute(stmt)
            calls: list[ProviderCall] = list(result.scalars())

            for pc in calls:
                cost = await calculate_cost(
                    session,
                    provider=pc.provider,
                    model=pc.model,
                    input_tokens=pc.input_tokens,
                    output_tokens=pc.output_tokens,
                    cached_input_tokens=pc.cached_input_tokens,
                    at_time=pc.created_at,
                    workspace_id=pc.workspace_id,
                )
                if cost is None:
                    cost = Decimal("0")  # Free/local provider (e.g. Ollama) — mark as $0

                await session.execute(
                    update(ProviderCall).where(ProviderCall.id == pc.id).values(cost_usd=cost)
                )
                enriched += 1

                # Increment Redis budget spend counters for matching budgets
                try:
                    budgets = await get_workspace_budgets_cached(redis, session, pc.workspace_id)
                    matched = _matching_budgets(
                        budgets,
                        end_user_id=pc.end_user_id,
                        feature_tag=None,  # feature_tag is on agent_run, not pc
                    )
                    import uuid  # noqa: PLC0415

                    for b in matched:
                        budget_id = uuid.UUID(b["id"])
                        await incr_budget_spend(redis, budget_id, b["period_type"], cost)
                        spend = await get_budget_spend(redis, budget_id, b["period_type"])
                        if spend >= Decimal(b["limit_usd"]) and b["action"] != "notify":
                            await fire_breach(session, redis, b, spend, b["action"])
                except Exception as exc:
                    log.warning("budget_incr_failed", error=str(exc))

            await session.commit()
    finally:
        await redis.aclose()

    if enriched:
        log.info("cost_enrichment_done", enriched=enriched)
        # Roll up costs to spans and runs after enriching
        asyncio.run(_rollup_span_and_run_costs())

    return {"enriched": enriched}


async def _rollup_span_and_run_costs() -> None:
    """
    Update span.cost_usd and agent_run.total_cost_usd / total_tokens by
    summing their child provider_calls.  Only touches rows where child costs
    are now fully populated (all provider_calls for that span/run have cost_usd).
    """
    factory = _make_session_factory()
    async with factory() as session:
        # Update spans
        await session.execute(
            text("""
                UPDATE spans s
                SET cost_usd = agg.total
                FROM (
                    SELECT span_id, SUM(cost_usd) AS total
                    FROM provider_calls
                    WHERE span_id IS NOT NULL AND cost_usd IS NOT NULL
                    GROUP BY span_id
                ) agg
                WHERE s.id = agg.span_id
            """)
        )

        # Update agent_runs
        await session.execute(
            text("""
                UPDATE agent_runs ar
                SET
                    total_cost_usd        = agg.total_cost,
                    total_input_tokens    = agg.total_input,
                    total_output_tokens   = agg.total_output
                FROM (
                    SELECT
                        run_id,
                        SUM(cost_usd)       AS total_cost,
                        SUM(input_tokens)   AS total_input,
                        SUM(output_tokens)  AS total_output
                    FROM provider_calls
                    WHERE cost_usd IS NOT NULL
                    GROUP BY run_id
                ) agg
                WHERE ar.id = agg.run_id
            """)
        )

        await session.commit()


# ── rollup_hourly_worker ──────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="metering.rollup_hourly",
    max_retries=2,
    default_retry_delay=30,
)
def rollup_hourly_worker(lookback_hours: int = 2) -> dict[str, Any]:
    """Full recompute of usage_hourly for the last N hours."""
    return asyncio.run(_run_rollup_hourly(lookback_hours))


async def _run_rollup_hourly(lookback_hours: int) -> dict[str, Any]:
    now = datetime.now(UTC)
    # Truncate to the current hour
    window_end = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    window_start = window_end - timedelta(hours=lookback_hours + 1)

    factory = _make_session_factory()
    async with factory() as session:
        # Delete existing rows for the window (idempotent)
        await session.execute(
            delete(UsageHourly).where(
                UsageHourly.hour >= window_start,
                UsageHourly.hour < window_end,
            )
        )

        # Recompute aggregates from provider_calls joined to agent_runs
        await session.execute(
            text("""
                INSERT INTO usage_hourly
                    (id, workspace_id, model, provider, feature_tag, end_user_id,
                     hour, input_tokens, output_tokens, cost_usd, run_count, call_count)
                SELECT
                    gen_random_uuid(),
                    pc.workspace_id,
                    pc.model,
                    pc.provider,
                    ar.feature_tag,
                    pc.end_user_id,
                    date_trunc('hour', pc.created_at) AS hour,
                    COALESCE(SUM(pc.input_tokens), 0),
                    COALESCE(SUM(pc.output_tokens), 0),
                    COALESCE(SUM(pc.cost_usd), 0),
                    COUNT(DISTINCT pc.run_id),
                    COUNT(pc.id)
                FROM provider_calls pc
                LEFT JOIN agent_runs ar ON ar.id = pc.run_id
                WHERE pc.created_at >= :window_start
                  AND pc.created_at < :window_end
                  AND pc.status = 'success'
                GROUP BY
                    pc.workspace_id, pc.model, pc.provider,
                    ar.feature_tag, pc.end_user_id,
                    date_trunc('hour', pc.created_at)
            """),
            {"window_start": window_start, "window_end": window_end},
        )

        await session.commit()

    log.info("rollup_hourly_done", window_start=str(window_start), window_end=str(window_end))
    return {"window_start": str(window_start), "window_end": str(window_end)}


# ── rollup_daily_worker ───────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="metering.rollup_daily",
    max_retries=2,
    default_retry_delay=60,
)
def rollup_daily_worker(target_day: str | None = None) -> dict[str, Any]:
    """
    Aggregate usage_hourly → usage_daily for a given day.

    Parameters
    ----------
    target_day:
        ISO date string (``YYYY-MM-DD``).  Defaults to yesterday (UTC).
    """
    return asyncio.run(_run_rollup_daily(target_day))


async def _run_rollup_daily(target_day: str | None) -> dict[str, Any]:
    if target_day:
        from datetime import date

        day = date.fromisoformat(target_day)
    else:
        day = (datetime.now(UTC) - timedelta(days=1)).date()

    factory = _make_session_factory()
    async with factory() as session:
        # Delete existing rows for the day
        await session.execute(delete(UsageDaily).where(UsageDaily.day == day))

        # Aggregate from usage_hourly
        await session.execute(
            text("""
                INSERT INTO usage_daily
                    (id, workspace_id, model, provider, feature_tag, end_user_id,
                     day, input_tokens, output_tokens, cost_usd, run_count, call_count)
                SELECT
                    gen_random_uuid(),
                    workspace_id,
                    model,
                    provider,
                    feature_tag,
                    end_user_id,
                    :day,
                    SUM(input_tokens),
                    SUM(output_tokens),
                    SUM(cost_usd),
                    SUM(run_count),
                    SUM(call_count)
                FROM usage_hourly
                WHERE hour >= :day_start
                  AND hour < :day_end
                GROUP BY workspace_id, model, provider, feature_tag, end_user_id
            """),
            {
                "day": day,
                "day_start": datetime(day.year, day.month, day.day, tzinfo=UTC),
                "day_end": datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(days=1),
            },
        )

        await session.commit()

    log.info("rollup_daily_done", day=str(day))
    return {"day": str(day)}


# ── data_quality_worker ───────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="metering.data_quality",
    max_retries=2,
    default_retry_delay=30,
)
def data_quality_worker() -> dict[str, int]:
    """Flag provider_calls with missing tokens or cost."""
    return asyncio.run(_run_data_quality())


async def _run_data_quality() -> dict[str, int]:
    lookback = datetime.now(UTC) - timedelta(hours=1)
    factory = _make_session_factory()
    flagged = 0

    async with factory() as session:
        # Find calls missing token counts
        stmt = (
            select(ProviderCall)
            .where(
                ProviderCall.created_at >= lookback,
                ProviderCall.input_tokens.is_(None),
                ProviderCall.status == "success",
            )
            .limit(1000)
        )
        result = await session.execute(stmt)
        calls: list[ProviderCall] = list(result.scalars())

        for pc in calls:
            # Check if already flagged
            existing = await session.execute(
                select(DataQualityIssue).where(
                    DataQualityIssue.provider_call_id == pc.id,
                    DataQualityIssue.issue_type == "missing_tokens",
                    DataQualityIssue.resolved.is_(False),
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            session.add(
                DataQualityIssue(
                    workspace_id=pc.workspace_id,
                    provider_call_id=pc.id,
                    run_id=pc.run_id,
                    issue_type="missing_tokens",
                    details={
                        "model": pc.model,
                        "provider": pc.provider,
                        "created_at": pc.created_at.isoformat(),
                    },
                )
            )
            flagged += 1

        # Find calls with token data but no cost after 5 minutes (pricing gap)
        five_min_ago = datetime.now(UTC) - timedelta(minutes=5)
        stmt2 = (
            select(ProviderCall)
            .where(
                ProviderCall.created_at >= lookback,
                ProviderCall.created_at <= five_min_ago,
                ProviderCall.input_tokens.is_not(None),
                ProviderCall.cost_usd.is_(None),
                ProviderCall.status == "success",
            )
            .limit(1000)
        )
        result2 = await session.execute(stmt2)
        uncost: list[ProviderCall] = list(result2.scalars())

        for pc in uncost:
            existing2 = await session.execute(
                select(DataQualityIssue).where(
                    DataQualityIssue.provider_call_id == pc.id,
                    DataQualityIssue.issue_type == "missing_cost",
                    DataQualityIssue.resolved.is_(False),
                )
            )
            if existing2.scalar_one_or_none() is not None:
                continue

            session.add(
                DataQualityIssue(
                    workspace_id=pc.workspace_id,
                    provider_call_id=pc.id,
                    run_id=pc.run_id,
                    issue_type="missing_cost",
                    details={
                        "model": pc.model,
                        "provider": pc.provider,
                        "input_tokens": pc.input_tokens,
                        "created_at": pc.created_at.isoformat(),
                    },
                )
            )
            flagged += 1

        if flagged:
            await session.commit()

    if flagged:
        log.info("data_quality_issues_flagged", count=flagged)

    return {"flagged": flagged}


# ── replay_backfill ───────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="metering.replay_backfill",
    max_retries=1,
    default_retry_delay=60,
)
def replay_backfill(from_iso: str, to_iso: str) -> dict[str, Any]:
    """
    Re-run cost enrichment and hourly/daily rollups for a time range.

    Used after a pricing correction to retroactively update cost figures.

    Parameters
    ----------
    from_iso:
        Start of the range as an ISO-8601 datetime string (UTC).
    to_iso:
        End of the range as an ISO-8601 datetime string (UTC).
    """
    return asyncio.run(_run_replay_backfill(from_iso, to_iso))


async def _run_replay_backfill(from_iso: str, to_iso: str) -> dict[str, Any]:
    from_dt = datetime.fromisoformat(from_iso)
    to_dt = datetime.fromisoformat(to_iso)

    log.info("replay_backfill_start", from_dt=str(from_dt), to_dt=str(to_dt))

    factory = _make_session_factory()

    # 1. Clear existing cost data in the window so enrichment re-prices them
    async with factory() as session:
        await session.execute(
            update(ProviderCall)
            .where(
                ProviderCall.created_at >= from_dt,
                ProviderCall.created_at < to_dt,
            )
            .values(cost_usd=None)
        )
        await session.commit()

    # 2. Re-run cost enrichment (will pick up cleared rows)
    enrichment_result = await _run_cost_enrichment()

    # 3. Re-run hourly rollups for the affected window
    lookback_hours = int((to_dt - from_dt).total_seconds() / 3600) + 2
    hourly_result = await _run_rollup_hourly(lookback_hours)

    # 4. Re-run daily rollups for affected days

    current_day = from_dt.date()
    end_day = to_dt.date()
    days_rerolled: list[str] = []
    while current_day <= end_day:
        await _run_rollup_daily(str(current_day))
        days_rerolled.append(str(current_day))
        current_day += timedelta(days=1)

    log.info("replay_backfill_done", days=days_rerolled)
    return {
        "enriched": enrichment_result["enriched"],
        "hourly_window": hourly_result,
        "days_rerolled": days_rerolled,
    }


# ── sync_pricing_from_file_worker ─────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="metering.sync_pricing_from_file",
    max_retries=1,
    default_retry_delay=30,
)
def sync_pricing_from_file_worker() -> dict[str, int]:
    """Read config/pricing.yml and upsert global provider_pricing rows.

    Runs every 6 hours via Celery Beat.  Also called on API startup.
    Safe to run multiple times — fully idempotent.
    """
    return asyncio.run(_run_sync_pricing_from_file())


async def _run_sync_pricing_from_file() -> dict[str, int]:
    from runledger_api.services.pricing_sync import load_pricing_yaml, sync_pricing  # noqa: PLC0415

    factory = _make_session_factory()
    entries = load_pricing_yaml(settings.pricing_file)
    if not entries:
        return {"inserted": 0, "updated": 0, "unchanged": 0}

    async with factory() as session:
        result = await sync_pricing(session, entries)

    log.info("sync_pricing_from_file_done", **result)
    return result
