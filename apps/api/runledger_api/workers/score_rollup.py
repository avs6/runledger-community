"""
Celery score rollup worker.

score_rollup_worker
    Aggregates score_events → score_rollups_daily for a target calendar day (UTC).
    Idempotent: deletes existing rollup rows for the day then inserts fresh aggregates.
    LEFT JOINs agent_runs to enrich with feature_tag and deployment_version.
    Runs nightly via Celery Beat (or on-demand with an explicit day_str).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.scores import ScoreRollupDaily
from runledger_api.models.tenant import Workspace

log = structlog.get_logger()


@celery_app.task(name="score_rollup.run")  # type: ignore[untyped-decorator]
def score_rollup_worker(day_str: str | None = None) -> None:
    """Roll up score_events into score_rollups_daily for the target day."""
    asyncio.run(_run(day_str))


async def _run(day_str: str | None) -> None:
    if day_str is not None:
        target_day = date.fromisoformat(day_str)
    else:
        target_day = (datetime.now(UTC) - timedelta(days=1)).date()

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            await _rollup_day(session, target_day)
    except Exception:
        log.exception("score_rollup_failed", target_day=str(target_day))

    # Run regression detection (separate try/except so rollup failure doesn't skip it)
    try:
        async with session_factory() as session:
            await _check_score_regressions(session, target_day)
    except Exception:
        log.exception("score_regression_check_failed", target_day=str(target_day))
    finally:
        await engine.dispose()


async def _rollup_day(session: AsyncSession, target_day: date) -> None:
    log.info("score_rollup_start", day=str(target_day))

    # Delete existing rollup rows for this day (idempotent)
    await session.execute(delete(ScoreRollupDaily).where(ScoreRollupDaily.day == target_day))

    # Aggregate score_events LEFT JOIN agent_runs for dimension enrichment
    # Groups by workspace_id + name + feature_tag + model + deployment_version
    insert_sql = text(
        """
        INSERT INTO score_rollups_daily
            (workspace_id, day, score_name, feature_tag, model, deployment_version,
             avg_value, p50, p90, sample_count)
        SELECT
            se.workspace_id,
            :target_day::date                                   AS day,
            se.name                                             AS score_name,
            COALESCE(ar.feature_tag, '')                        AS feature_tag,
            COALESCE(pc.model, '')                              AS model,
            COALESCE(ar.deployment_version, '')                 AS deployment_version,
            AVG(se.value)                                       AS avg_value,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY se.value) AS p50,
            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY se.value) AS p90,
            COUNT(*)                                            AS sample_count
        FROM score_events se
        LEFT JOIN agent_runs ar ON se.run_id = ar.id
        LEFT JOIN (
            SELECT DISTINCT ON (run_id) run_id, model
            FROM provider_calls
            ORDER BY run_id, created_at
        ) pc ON se.run_id = pc.run_id
        WHERE se.created_at >= :day_start
          AND se.created_at <  :day_end
        GROUP BY
            se.workspace_id,
            se.name,
            COALESCE(ar.feature_tag, ''),
            COALESCE(pc.model, ''),
            COALESCE(ar.deployment_version, '')
        """
    )

    day_start = datetime(target_day.year, target_day.month, target_day.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    await session.execute(
        insert_sql,
        {"target_day": str(target_day), "day_start": day_start, "day_end": day_end},
    )
    await session.commit()
    log.info("score_rollup_done", day=str(target_day))


async def _check_score_regressions(session: AsyncSession, target_day: date) -> None:
    """Detect score regressions (>20% drop) vs prior 7-day window and email admins."""
    from runledger_api.services.email import send_score_regression_email
    from runledger_api.services.email_utils import get_email_preference, get_workspace_admin_users

    prior_end = target_day - timedelta(days=1)
    prior_start = target_day - timedelta(days=8)

    regression_sql = text(
        """
        SELECT
            today.workspace_id,
            today.score_name     AS metric_name,
            today.avg_value      AS current_avg,
            prior.avg_score      AS prior_avg,
            (prior.avg_score - today.avg_value) / prior.avg_score * 100 AS drop_pct
        FROM score_rollups_daily today
        JOIN (
            SELECT workspace_id, score_name, AVG(avg_value) AS avg_score
            FROM score_rollups_daily
            WHERE day BETWEEN :prior_start AND :prior_end
            GROUP BY workspace_id, score_name
        ) prior ON prior.workspace_id = today.workspace_id
                AND prior.score_name = today.score_name
        WHERE today.day = :target_day
          AND prior.avg_score > 0
          AND (prior.avg_score - today.avg_value) / prior.avg_score > 0.20
        """
    )

    result = await session.execute(
        regression_sql,
        {
            "target_day": str(target_day),
            "prior_start": str(prior_start),
            "prior_end": str(prior_end),
        },
    )
    regressions = result.all()

    if not regressions:
        return

    for row in regressions:
        try:
            prefs = await get_email_preference(session, row.workspace_id)
            if prefs is not None and not prefs.score_regression_enabled:
                continue

            ws_result = await session.execute(
                select(Workspace).where(Workspace.id == row.workspace_id)
            )
            workspace = ws_result.scalar_one_or_none()
            ws_name = workspace.name if workspace else str(row.workspace_id)

            admins = await get_workspace_admin_users(session, row.workspace_id)
            await asyncio.gather(
                *[
                    send_score_regression_email(
                        to_email=u.email,
                        full_name=u.full_name,
                        metric_name=row.metric_name,
                        current_avg=float(row.current_avg),
                        prior_avg=float(row.prior_avg),
                        change_pct=float(row.drop_pct),
                        workspace_name=ws_name,
                    )
                    for u in admins
                ],
                return_exceptions=True,
            )
            log.info(
                "score_regression_email_sent",
                workspace_id=str(row.workspace_id),
                metric=row.metric_name,
                drop_pct=float(row.drop_pct),
            )
        except Exception as exc:
            log.warning(
                "score_regression_email_failed",
                workspace_id=str(row.workspace_id),
                error=str(exc),
            )
