"""
Celery billing workers for RunLedger.

Workers
-------
nightly_reconciliation
    Checks all recently-closed billing periods for reconciliation issues.
    Logs structured results. Runs daily at 00:15 UTC.

auto_create_billing_periods
    For each workspace, checks if a billing period exists for the previous
    calendar month. If not, creates one. Runs daily at 00:01 UTC.
"""

from __future__ import annotations

import asyncio
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.billing import BillingPeriod
from runledger_api.models.tenant import Workspace
from runledger_api.services.billing import run_reconciliation

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── nightly_reconciliation ────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="billing.nightly_reconciliation",
    max_retries=2,
    default_retry_delay=60,
)
def nightly_reconciliation() -> dict[str, int]:
    """Reconcile recently-closed billing periods."""
    return asyncio.run(_run_nightly_reconciliation())


async def _run_nightly_reconciliation() -> dict[str, int]:
    factory = _make_session_factory()
    checked = 0
    failed = 0

    async with factory() as session:
        cutoff = datetime.now(UTC) - timedelta(days=7)

        result = await session.execute(
            select(BillingPeriod).where(
                BillingPeriod.status == "closed",
                BillingPeriod.created_at > cutoff,
            )
        )
        periods: list[BillingPeriod] = list(result.scalars())

        for period in periods:
            try:
                recon = await run_reconciliation(session, period.id)
                checked += 1
                if recon.status == "fail":
                    failed += 1
                    log.warning(
                        "nightly_reconciliation_fail",
                        period_id=str(period.id),
                        issues=recon.issues,
                        delta_pct=str(recon.delta_pct),
                        orphaned=recon.orphaned_calls,
                        duplicates=recon.duplicate_calls,
                    )
                else:
                    log.info(
                        "nightly_reconciliation_pass",
                        period_id=str(period.id),
                    )
            except Exception as exc:
                log.error(
                    "nightly_reconciliation_error",
                    period_id=str(period.id),
                    error=str(exc),
                )
                failed += 1

    log.info("nightly_reconciliation_done", checked=checked, failed=failed)
    return {"checked": checked, "failed": failed}


# ── auto_create_billing_periods ───────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="billing.auto_create_billing_periods",
    max_retries=2,
    default_retry_delay=60,
)
def auto_create_billing_periods() -> dict[str, int]:
    """Create billing periods for last month if missing."""
    return asyncio.run(_run_auto_create_billing_periods())


async def _run_auto_create_billing_periods() -> dict[str, int]:
    factory = _make_session_factory()
    created = 0
    skipped = 0

    # Previous calendar month
    today = date.today()
    if today.month == 1:
        last_month = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month = today.replace(month=today.month - 1, day=1)

    last_day = monthrange(last_month.year, last_month.month)[1]
    period_start = last_month
    period_end = last_month.replace(day=last_day)

    async with factory() as session:
        ws_result = await session.execute(select(Workspace))
        workspaces: list[Workspace] = list(ws_result.scalars())

        for workspace in workspaces:
            # Check if period already exists for this month
            existing = await session.execute(
                select(BillingPeriod).where(
                    BillingPeriod.workspace_id == workspace.id,
                    BillingPeriod.period_start == period_start,
                    BillingPeriod.period_end == period_end,
                )
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue

            period = BillingPeriod(
                workspace_id=workspace.id,
                period_start=period_start,
                period_end=period_end,
                status="open",
            )
            session.add(period)
            created += 1
            log.info(
                "auto_created_billing_period",
                workspace_id=str(workspace.id),
                period_start=str(period_start),
                period_end=str(period_end),
            )

        if created:
            await session.commit()

    log.info("auto_create_billing_periods_done", created=created, skipped=skipped)
    return {"created": created, "skipped": skipped}
