"""
Warehouse export Celery workers — Phase 28.

Tasks
-----
warehouse.run_scheduled_exports   — daily beat: creates jobs for all active destinations
warehouse.run_single_export       — process one ExportJob by ID
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings

log = structlog.get_logger()


# ── Scheduled daily export ────────────────────────────────────────────────────


@celery_app.task(name="warehouse.run_scheduled_exports")  # type: ignore[untyped-decorator]
def run_scheduled_exports() -> None:
    """Create and dispatch export jobs for all active destinations (yesterday's data)."""
    asyncio.run(_run_scheduled())


async def _run_scheduled() -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await _schedule_all(session)
    finally:
        await engine.dispose()


async def _schedule_all(session: AsyncSession) -> None:
    from runledger_api.models.warehouse import ExportJob, WarehouseDestination

    result = await session.execute(
        select(WarehouseDestination).where(WarehouseDestination.is_active.is_(True))
    )
    destinations = list(result.scalars().all())
    export_date = (datetime.now(UTC) - timedelta(days=1)).date()

    dispatched = 0
    for dest in destinations:
        try:
            job = ExportJob(
                workspace_id=dest.workspace_id,
                destination_id=dest.id,
                export_date=export_date,
                status="pending",
                resources=list(dest.resources),
            )
            session.add(job)
            await session.flush()
            await session.commit()
            run_single_export.delay(str(job.id))
            dispatched += 1
        except Exception:
            log.exception("warehouse_schedule_failed", destination_id=str(dest.id))

    log.info("warehouse_scheduled", export_date=str(export_date), dispatched=dispatched)


# ── Single export job ─────────────────────────────────────────────────────────


@celery_app.task(name="warehouse.run_single_export")  # type: ignore[untyped-decorator]
def run_single_export(job_id: str) -> None:
    """Process one ExportJob end-to-end: query → serialize → upload → update status."""
    asyncio.run(_run_job(uuid.UUID(job_id)))


async def _run_job(job_id: uuid.UUID) -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await _execute_job(session, job_id)
    finally:
        await engine.dispose()


async def _execute_job(session: AsyncSession, job_id: uuid.UUID) -> None:
    from runledger_api.models.warehouse import ExportJob, WarehouseDestination
    from runledger_api.services.warehouse import export_workspace_data

    # Load job + destination
    job_result = await session.execute(select(ExportJob).where(ExportJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        log.error("warehouse_job_not_found", job_id=str(job_id))
        return

    dest_result = await session.execute(
        select(WarehouseDestination).where(WarehouseDestination.id == job.destination_id)
    )
    dest = dest_result.scalar_one_or_none()
    if not dest:
        job.status = "failed"
        job.error = "Destination not found"
        await session.commit()
        return

    # Mark running
    job.status = "running"
    job.started_at = datetime.now(UTC)
    await session.commit()

    try:
        results = await export_workspace_data(
            session,
            destination=dest,
            export_date=job.export_date,
            resources=list(job.resources),
        )

        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.file_keys = {resource: uri for resource, (uri, _) in results.items()}
        job.row_counts = {resource: count for resource, (_, count) in results.items()}

        # Update destination's last_export_at
        dest.last_export_at = datetime.now(UTC)

        await session.commit()
        log.info(
            "warehouse_job_completed",
            job_id=str(job_id),
            export_date=str(job.export_date),
            row_counts=job.row_counts,
        )

    except Exception as exc:
        job.status = "failed"
        job.completed_at = datetime.now(UTC)
        job.error = str(exc)
        await session.commit()
        log.exception("warehouse_job_failed", job_id=str(job_id))
