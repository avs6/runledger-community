"""Quota enforcement service.

check_quota() is called on every ingest request.
increment_quota_usage() is called after successful event acceptance.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.saas import UsageQuota

log = structlog.get_logger()


async def check_quota(tenant_id: uuid.UUID, db: AsyncSession) -> None:
    """
    Raise HTTP 402 if the tenant has exceeded their monthly event quota.
    Fail open — if no quota row exists, allow the request through.
    """
    result = await db.execute(
        select(UsageQuota).where(UsageQuota.tenant_id == tenant_id)
    )
    quota = result.scalar_one_or_none()
    if quota is None:
        return  # no quota row → allow (self-hosted OSS path)

    if quota.events_used >= quota.events_limit:
        log.warning(
            "quota_exceeded",
            tenant_id=str(tenant_id),
            used=quota.events_used,
            limit=quota.events_limit,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "quota_exceeded",
                "events_used": quota.events_used,
                "events_limit": quota.events_limit,
                "message": "Monthly event quota exceeded. Upgrade your plan to continue.",
            },
        )


async def increment_quota_usage(tenant_id: uuid.UUID, count: int, db: AsyncSession) -> None:
    """Increment events_used by count for the tenant. No-op if no quota row."""
    await db.execute(
        update(UsageQuota)
        .where(UsageQuota.tenant_id == tenant_id)
        .values(events_used=UsageQuota.events_used + count)
    )
