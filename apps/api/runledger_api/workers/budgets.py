"""
Celery budget workers for RunLedger.

Workers
-------
runaway_protection
    Detects retry storms (>20 provider_calls in 2 min) or token spikes
    (any call with >100k input tokens) within active runs.
    Cancels the run and fires workspace notifications.
    Runs every 5 minutes via Celery Beat.

budget_spend_sync
    Re-computes budget spend counters from provider_calls and writes them
    back to Redis — recovery from Redis eviction / restart.
    Runs daily at 00:10 UTC.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.budgets import Budget, BudgetNotification
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.services.budgets import (
    _period_key,
    _spend_key,
    send_notification,
)

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _make_redis() -> Redis:
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


# ── runaway_protection ────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="budgets.runaway_protection",
    max_retries=2,
    default_retry_delay=30,
)
def runaway_protection() -> dict[str, int]:
    """Detect retry storms and token spikes in active agent runs."""
    return asyncio.run(_run_runaway_protection())


async def _run_runaway_protection() -> dict[str, int]:
    factory = _make_session_factory()
    redis = _make_redis()
    cancelled = 0

    try:
        async with factory() as session:
            now = datetime.now(UTC)
            two_min_ago = now - timedelta(minutes=2)

            # Find runs that have been 'running' for at least 2 minutes
            stmt = select(AgentRun).where(
                AgentRun.status == "running",
                AgentRun.started_at <= two_min_ago,
            )
            result = await session.execute(stmt)
            active_runs: list[AgentRun] = list(result.scalars())

            for run in active_runs:
                # Check retry storm: >20 provider_calls in last 2 min
                storm_stmt = select(func.count(ProviderCall.id)).where(
                    ProviderCall.run_id == run.id,
                    ProviderCall.created_at >= two_min_ago,
                )
                storm_result = await session.execute(storm_stmt)
                call_count = storm_result.scalar_one()

                # Check token spike: any call with >100k input tokens
                spike_stmt = select(func.count(ProviderCall.id)).where(
                    ProviderCall.run_id == run.id,
                    ProviderCall.input_tokens > 100_000,
                )
                spike_result = await session.execute(spike_stmt)
                spike_count = spike_result.scalar_one()

                if call_count > 20 or spike_count > 0:
                    reason = "retry_storm" if call_count > 20 else "token_spike"
                    log.warning(
                        "runaway_detected",
                        run_id=str(run.id),
                        reason=reason,
                        call_count=call_count,
                        spike_count=spike_count,
                    )

                    await session.execute(
                        update(AgentRun)
                        .where(AgentRun.id == run.id)
                        .values(status="cancelled", ended_at=now)
                    )
                    cancelled += 1

                    # Fire notifications
                    notif_result = await session.execute(
                        select(BudgetNotification).where(
                            BudgetNotification.workspace_id == run.workspace_id,
                            BudgetNotification.is_active.is_(True),
                            BudgetNotification.events.any("runaway.detected"),
                        )
                    )
                    notifications: list[BudgetNotification] = list(notif_result.scalars())
                    payload: dict[str, Any] = {
                        "event": "runaway.detected",
                        "run_id": str(run.id),
                        "workspace_id": str(run.workspace_id),
                        "reason": reason,
                        "call_count_last_2min": call_count,
                        "detected_at": now.isoformat(),
                    }
                    for notification in notifications:
                        try:
                            await send_notification(notification, payload)
                        except Exception as exc:
                            log.warning(
                                "runaway_notification_failed",
                                notification_id=str(notification.id),
                                error=str(exc),
                            )

            if cancelled:
                await session.commit()
    finally:
        await redis.aclose()

    if cancelled:
        log.info("runaway_protection_cancelled", count=cancelled)

    return {"cancelled": cancelled}


# ── budget_spend_sync ─────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="budgets.budget_spend_sync",
    max_retries=2,
    default_retry_delay=60,
)
def budget_spend_sync() -> dict[str, int]:
    """Re-compute all active budget spend counters from provider_calls."""
    return asyncio.run(_run_budget_spend_sync())


async def _run_budget_spend_sync() -> dict[str, int]:
    factory = _make_session_factory()
    redis = _make_redis()
    synced = 0

    try:
        async with factory() as session:
            result = await session.execute(select(Budget).where(Budget.is_active.is_(True)))
            budgets: list[Budget] = list(result.scalars())

            now = datetime.now(UTC)

            for budget in budgets:
                pk = _period_key(budget.period_type, now)

                # Determine time window for this period
                if budget.period_type == "daily":
                    period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    period_end = period_start + timedelta(days=1)
                elif budget.period_type == "monthly":
                    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    # First day of next month
                    if now.month == 12:
                        period_end = period_start.replace(year=now.year + 1, month=1)
                    else:
                        period_end = period_start.replace(month=now.month + 1)
                else:
                    # total: sum everything
                    period_start = datetime.min.replace(tzinfo=UTC)
                    period_end = now + timedelta(days=1)

                # Build scope filter
                scope_filter = [ProviderCall.workspace_id == budget.workspace_id]
                if budget.scope_type == "end_user" and budget.scope_id:
                    scope_filter.append(ProviderCall.end_user_id == budget.scope_id)
                # feature_tag is on agent_runs, not provider_calls — skip for now
                # (workspace and total scope are handled by workspace_id filter)

                spend_stmt = select(
                    func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0))
                ).where(
                    *scope_filter,
                    ProviderCall.created_at >= period_start,
                    ProviderCall.created_at < period_end,
                    ProviderCall.cost_usd.is_not(None),
                )
                spend_result = await session.execute(spend_stmt)
                spend = spend_result.scalar_one() or Decimal(0)

                redis_key = _spend_key(budget.id, pk)
                await redis.set(redis_key, str(float(spend)))

                # Set TTL for daily / monthly keys
                if budget.period_type == "daily":
                    await redis.expire(redis_key, 86400 * 2)
                elif budget.period_type == "monthly":
                    await redis.expire(redis_key, 86400 * 35)

                synced += 1

    finally:
        await redis.aclose()

    log.info("budget_spend_sync_done", synced=synced)
    return {"synced": synced}
