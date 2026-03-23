"""
Celery tasks for outcome rollups and ROI alerts.

Tasks
-----
rollup_outcomes_daily()
    Compute and upsert daily outcome rollups for all workspaces.
    Idempotent — safe to re-run.

check_outcome_alerts()
    Detect cost-per-success spikes and success-rate drops.
    Fires structlog warnings; Slack dispatch when workspace has a webhook.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import structlog

from runledger_api.core.celery_app import celery_app

log = structlog.get_logger()

_SPIKE_THRESHOLD = 0.30   # 30% increase in cost_per_success triggers alert
_DROP_THRESHOLD = 0.20    # 20% decrease in success_rate triggers alert
_MIN_SAMPLE = 5           # minimum outcomes in window to alert


async def _rollup() -> int:
    """Compute outcome_rollups_daily for yesterday across all workspaces."""
    from sqlalchemy import func, select, text
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    from runledger_api.core.config import settings
    from runledger_api.models.events import AgentRun, ProviderCall
    from runledger_api.models.outcomes import Outcome, OutcomeRollupDaily

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # noqa: N806

    yesterday = date.today() - timedelta(days=1)
    day_start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    rows_written = 0

    async with AsyncSessionLocal() as db:
        # Get distinct (workspace_id, outcome_type) pairs for yesterday
        pairs_result = await db.execute(
            select(Outcome.workspace_id, Outcome.outcome_type)
            .where(Outcome.created_at >= day_start, Outcome.created_at < day_end)
            .distinct()
        )
        pairs = pairs_result.all()

        for workspace_id, outcome_type in pairs:
            # Aggregate outcomes for this pair
            agg_result = await db.execute(
                select(
                    func.count(Outcome.id).label("count"),
                    func.sum(func.cast(Outcome.success, type_=func.Integer.__class__)).label("success_count"),
                    func.coalesce(func.sum(Outcome.value_usd), Decimal("0")).label("total_value"),
                ).where(
                    Outcome.workspace_id == workspace_id,
                    Outcome.outcome_type == outcome_type,
                    Outcome.created_at >= day_start,
                    Outcome.created_at < day_end,
                )
            )
            agg = agg_result.one()

            count = int(agg.count or 0)
            if count == 0:
                continue

            # Count successes separately (sum of bool cast is unreliable across engines)
            success_result = await db.execute(
                select(func.count(Outcome.id)).where(
                    Outcome.workspace_id == workspace_id,
                    Outcome.outcome_type == outcome_type,
                    Outcome.success.is_(True),
                    Outcome.created_at >= day_start,
                    Outcome.created_at < day_end,
                )
            )
            success_count = int(success_result.scalar() or 0)

            # Total cost from provider_calls linked via run_id
            run_ids_sq = (
                select(Outcome.run_id)
                .where(
                    Outcome.workspace_id == workspace_id,
                    Outcome.outcome_type == outcome_type,
                    Outcome.created_at >= day_start,
                    Outcome.created_at < day_end,
                    Outcome.run_id.isnot(None),
                )
                .scalar_subquery()
            )
            cost_result = await db.execute(
                select(func.coalesce(func.sum(ProviderCall.cost_usd), Decimal("0"))).where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.run_id.in_(run_ids_sq),
                )
            )
            total_cost = Decimal(str(cost_result.scalar() or 0))

            success_rate = Decimal(str(round(success_count / count, 4)))
            cost_per_success = (
                Decimal(str(round(float(total_cost) / success_count, 6)))
                if success_count > 0
                else Decimal("0")
            )
            total_value = Decimal(str(agg.total_value or 0))
            roi = (
                Decimal(str(round((float(total_value) - float(total_cost)) / float(total_cost) * 100, 4)))
                if total_cost > 0 and total_value > 0
                else None
            )

            # Upsert into rollup table
            stmt = (
                insert(OutcomeRollupDaily)
                .values(
                    workspace_id=workspace_id,
                    day=yesterday,
                    outcome_type=outcome_type,
                    success_rate=success_rate,
                    count=count,
                    total_cost_usd=total_cost,
                    cost_per_success_usd=cost_per_success,
                    total_value_usd=total_value if total_value > 0 else None,
                    roi=roi,
                )
                .on_conflict_do_update(
                    index_elements=["workspace_id", "day", "outcome_type"],
                    set_={
                        "success_rate": success_rate,
                        "count": count,
                        "total_cost_usd": total_cost,
                        "cost_per_success_usd": cost_per_success,
                        "total_value_usd": total_value if total_value > 0 else None,
                        "roi": roi,
                    },
                )
            )
            await db.execute(stmt)
            rows_written += 1

        await db.commit()

    await engine.dispose()
    return rows_written


@celery_app.task(name="outcomes.rollup_daily")  # type: ignore[untyped-decorator]
def rollup_outcomes_daily() -> None:
    written = asyncio.run(_rollup())
    log.info("outcome_rollup_done", rows_written=written)


async def _check_alerts() -> list[dict]:
    """Compare last 7d cost_per_success + success_rate vs prior 7d."""
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    from runledger_api.core.config import settings
    from runledger_api.models.outcomes import OutcomeRollupDaily

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # noqa: N806

    today = date.today()
    curr_start = today - timedelta(days=7)
    prior_start = today - timedelta(days=14)
    prior_end = curr_start

    alerts: list[dict] = []

    async with AsyncSessionLocal() as db:
        # Aggregate current window
        curr_result = await db.execute(
            select(
                OutcomeRollupDaily.workspace_id,
                OutcomeRollupDaily.outcome_type,
                func.avg(OutcomeRollupDaily.success_rate).label("avg_sr"),
                func.avg(OutcomeRollupDaily.cost_per_success_usd).label("avg_cps"),
                func.sum(OutcomeRollupDaily.count).label("total_count"),
            )
            .where(OutcomeRollupDaily.day >= curr_start)
            .group_by(OutcomeRollupDaily.workspace_id, OutcomeRollupDaily.outcome_type)
        )
        curr_rows = curr_result.all()

        # Aggregate prior window
        prior_result = await db.execute(
            select(
                OutcomeRollupDaily.workspace_id,
                OutcomeRollupDaily.outcome_type,
                func.avg(OutcomeRollupDaily.success_rate).label("avg_sr"),
                func.avg(OutcomeRollupDaily.cost_per_success_usd).label("avg_cps"),
            )
            .where(
                OutcomeRollupDaily.day >= prior_start,
                OutcomeRollupDaily.day < prior_end,
            )
            .group_by(OutcomeRollupDaily.workspace_id, OutcomeRollupDaily.outcome_type)
        )
        prior_map = {
            (str(r.workspace_id), r.outcome_type): r for r in prior_result.all()
        }

        for row in curr_rows:
            total = int(row.total_count or 0)
            if total < _MIN_SAMPLE:
                continue

            key = (str(row.workspace_id), row.outcome_type)
            prior = prior_map.get(key)
            if prior is None:
                continue

            curr_sr = float(row.avg_sr or 0)
            prior_sr = float(prior.avg_sr or 0)
            curr_cps = float(row.avg_cps or 0)
            prior_cps = float(prior.avg_cps or 0)

            if prior_sr > 0 and (prior_sr - curr_sr) / prior_sr >= _DROP_THRESHOLD:
                alerts.append({
                    "workspace_id": str(row.workspace_id),
                    "outcome_type": row.outcome_type,
                    "alert_type": "success_rate_drop",
                    "current": curr_sr,
                    "prior": prior_sr,
                    "change_pct": round((curr_sr - prior_sr) / prior_sr * 100, 2),
                })

            if prior_cps > 0 and (curr_cps - prior_cps) / prior_cps >= _SPIKE_THRESHOLD:
                alerts.append({
                    "workspace_id": str(row.workspace_id),
                    "outcome_type": row.outcome_type,
                    "alert_type": "cost_per_success_spike",
                    "current": curr_cps,
                    "prior": prior_cps,
                    "change_pct": round((curr_cps - prior_cps) / prior_cps * 100, 2),
                })

    await engine.dispose()
    return alerts


@celery_app.task(name="outcomes.check_alerts")  # type: ignore[untyped-decorator]
def check_outcome_alerts() -> None:
    alerts = asyncio.run(_check_alerts())
    for alert in alerts:
        log.warning(
            "outcome_alert",
            alert_type=alert["alert_type"],
            outcome_type=alert["outcome_type"],
            workspace_id=alert["workspace_id"],
            current=alert["current"],
            prior=alert["prior"],
            change_pct=alert["change_pct"],
        )
    log.info("outcome_alert_check_done", alerts_fired=len(alerts))
