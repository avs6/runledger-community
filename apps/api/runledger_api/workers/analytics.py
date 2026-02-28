"""
Celery worker: nightly anomaly detection.

For each workspace with activity in the past 30 days, computes per-user daily spend
and flags users whose yesterday's spend is >3σ above their 30-day mean.
Results are stored in user_anomalies (idempotent — skips existing anomalies for
the same workspace/user/date).
"""

from __future__ import annotations

import asyncio
import statistics
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import ProviderCall
from runledger_api.models.replay import UserAnomaly

log = structlog.get_logger()

_ZSCORE_THRESHOLD = 3.0
_LOOKBACK_DAYS = 30


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="analytics.anomaly_detection",
    max_retries=1,
)
def anomaly_detection_worker() -> dict[str, int]:
    """Detect end-user spend anomalies; populate user_anomalies table."""
    return asyncio.run(_run_anomaly_detection())


async def _run_anomaly_detection() -> dict[str, int]:
    factory = _make_session_factory()
    now = datetime.now(UTC)
    lookback_start = now - timedelta(days=_LOOKBACK_DAYS)
    yesterday: date = (now - timedelta(days=1)).date()

    workspaces_checked = 0
    anomalies_flagged = 0

    async with factory() as session:
        # 1. Get all workspace IDs active in the last 30d
        ws_stmt = (
            select(ProviderCall.workspace_id.distinct())
            .where(ProviderCall.created_at >= lookback_start)
        )
        ws_result = await session.execute(ws_stmt)
        workspace_ids = [row[0] for row in ws_result.all()]

        for workspace_id in workspace_ids:
            workspaces_checked += 1

            # 2. Get distinct end_user_ids active in last 30d for this workspace
            user_stmt = (
                select(ProviderCall.end_user_id.distinct())
                .where(
                    ProviderCall.workspace_id == workspace_id,
                    ProviderCall.created_at >= lookback_start,
                    ProviderCall.end_user_id.is_not(None),
                )
            )
            user_result = await session.execute(user_stmt)
            end_user_ids = [row[0] for row in user_result.all()]

            for end_user_id in end_user_ids:
                # 3. Get daily spend for this user over the lookback window
                daily_stmt = (
                    select(
                        func.date(ProviderCall.created_at).label("spend_date"),
                        func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)).label(
                            "daily_cost"
                        ),
                    )
                    .where(
                        ProviderCall.workspace_id == workspace_id,
                        ProviderCall.end_user_id == end_user_id,
                        ProviderCall.created_at >= lookback_start,
                        ProviderCall.created_at < now,
                    )
                    .group_by(func.date(ProviderCall.created_at))
                    .order_by(func.date(ProviderCall.created_at))
                )
                daily_result = await session.execute(daily_stmt)
                daily_rows = daily_result.all()

                if len(daily_rows) < 2:
                    # Not enough data to compute meaningful stats
                    continue

                daily_spends = [float(row.daily_cost) for row in daily_rows]
                mean_spend = statistics.mean(daily_spends)

                try:
                    stddev = statistics.stdev(daily_spends)
                except statistics.StatisticsError:
                    continue

                if stddev == 0:
                    continue

                # 4. Find yesterday's spend (if present)
                yesterday_spend = 0.0
                for row in daily_rows:
                    if row.spend_date == yesterday:
                        yesterday_spend = float(row.daily_cost)
                        break

                if yesterday_spend <= 0:
                    continue

                zscore = (yesterday_spend - mean_spend) / stddev

                if zscore <= _ZSCORE_THRESHOLD:
                    continue

                # 5. Check for existing anomaly for same workspace/user/date
                existing_stmt = select(UserAnomaly).where(
                    UserAnomaly.workspace_id == workspace_id,
                    UserAnomaly.end_user_id == end_user_id,
                    UserAnomaly.detected_at == yesterday,
                )
                existing_result = await session.execute(existing_stmt)
                if existing_result.scalar_one_or_none() is not None:
                    continue

                # 6. Insert anomaly
                reason = (
                    f"Daily spend ${yesterday_spend:.4f} is {zscore:.1f}\u03c3 "
                    f"above 30d mean ${mean_spend:.4f}"
                )
                anomaly = UserAnomaly(
                    workspace_id=workspace_id,
                    end_user_id=end_user_id,
                    detected_at=yesterday,
                    daily_spend=Decimal(str(yesterday_spend)),
                    mean_spend=Decimal(str(mean_spend)),
                    zscore=Decimal(str(round(zscore, 4))),
                    reason=reason,
                )
                session.add(anomaly)
                anomalies_flagged += 1
                log.info(
                    "analytics.anomaly.flagged",
                    workspace_id=str(workspace_id),
                    end_user_id=end_user_id,
                    zscore=round(zscore, 2),
                )

        await session.commit()

    log.info(
        "analytics.anomaly_detection.done",
        workspaces_checked=workspaces_checked,
        anomalies_flagged=anomalies_flagged,
    )
    return {"workspaces_checked": workspaces_checked, "anomalies_flagged": anomalies_flagged}
