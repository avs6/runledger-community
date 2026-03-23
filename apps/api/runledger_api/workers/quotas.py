"""Quota reset Celery worker.

Runs on the first day of each month to reset events_used → 0 for all tenants.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from runledger_api.core.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="quota_monthly_reset")  # type: ignore[untyped-decorator]
def quota_monthly_reset() -> dict[str, object]:
    """Reset events_used to 0 for all usage_quotas rows."""
    import asyncio  # noqa: PLC0415

    return asyncio.run(_reset())


async def _reset() -> dict[str, object]:
    from sqlalchemy import text, update  # noqa: PLC0415

    from runledger_api.core.db import AsyncSessionLocal  # noqa: PLC0415
    from runledger_api.models.saas import UsageQuota  # noqa: PLC0415

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(UsageQuota).values(events_used=0, period_start=now).returning(text("id"))
        )
        rows = result.fetchall()
        await session.commit()

    count = len(rows)
    log.info("quota_monthly_reset", reset_count=count)
    return {"reset_count": count, "reset_at": now.isoformat()}
