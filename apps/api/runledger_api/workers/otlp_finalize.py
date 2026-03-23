"""
OTLP trace finalization worker.

Closes stale OTLP-ingested agent runs and their open spans after the
inactivity timeout. Handles:
  - Traces whose root span never emitted a run_end (crashed app, timeout, etc.)
  - Spans that were started but never ended within an otherwise-closed run
  - Out-of-order batches that left runs open beyond the inactivity window

Default inactivity timeout: 5 minutes (OTLP_INACTIVITY_TIMEOUT_MINUTES).
Beat schedule: every 3 minutes — tighter than the timeout so close-out
happens promptly without a long tail of open runs in the analytics views.

Stale runs are marked cancelled (not failed) to distinguish deliberate
application failure from ingest-level abandonment.
Open spans within a stale run are marked failed with a synthetic ended_at
set to NOW() so latency calculations remain bounded.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import AgentRun, RunStatusEnum, Span, SpanStatusEnum

log = structlog.get_logger()

# Runs still open after this many minutes are considered stale.
# Configurable via settings in the future; 5 minutes matches the plan spec.
_INACTIVITY_MINUTES = 5


@celery_app.task(name="otlp.finalize_stale_traces")  # type: ignore[untyped-decorator]
def finalize_stale_traces() -> None:
    """Close OTLP runs that have been open longer than the inactivity timeout."""
    asyncio.run(_finalize())


async def _finalize() -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            closed = await _close_stale_runs(session)
            await session.commit()
            if closed:
                log.info("otlp_finalize_complete", runs_closed=closed)
    finally:
        await engine.dispose()


async def _close_stale_runs(session: AsyncSession) -> int:
    """
    Find and close stale OTLP runs.

    Returns the number of runs closed.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=_INACTIVITY_MINUTES)

    # SELECT id FROM agent_runs WHERE source_type='otlp'
    #   AND status='running' AND started_at < cutoff
    result = await session.execute(
        select(AgentRun.id).where(
            AgentRun.source_type == "otlp",
            AgentRun.status == RunStatusEnum.running,
            AgentRun.started_at < cutoff,
        )
    )
    run_ids = [row[0] for row in result.all()]

    if not run_ids:
        return 0

    now = datetime.now(UTC)

    # Close all open spans belonging to stale runs
    await session.execute(
        update(Span)
        .where(
            Span.run_id.in_(run_ids),
            Span.status == SpanStatusEnum.running,
        )
        .values(
            status=SpanStatusEnum.failed,
            ended_at=now,
        )
    )

    # Close the stale runs as cancelled (not failed — this is a timeout, not
    # an application-level error)
    await session.execute(
        update(AgentRun)
        .where(AgentRun.id.in_(run_ids))
        .values(
            status=RunStatusEnum.cancelled,
            ended_at=now,
        )
    )

    log.warning(
        "otlp_stale_runs_closed",
        count=len(run_ids),
        inactivity_minutes=_INACTIVITY_MINUTES,
        cutoff=cutoff.isoformat(),
    )
    return len(run_ids)
