"""
Pricing sync Celery worker — syncs the embedded catalog to provider_pricing.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="pricing.sync_catalog")  # type: ignore[untyped-decorator]
def sync_pricing_catalog() -> dict[str, Any]:
    """
    Sync the embedded pricing catalog to provider_pricing (Celery beat, 6h).

    Reads pricing_sync_config before running:
      - sync_enabled=False  → exits immediately with {"skipped_reason": "disabled"}
      - excluded_providers  → respected by sync_catalog_to_db
      - excluded_models     → respected by sync_catalog_to_db
      - force_update        → passed through as the `force` default
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: PLC0415

    from runledger_api.core.config import settings  # noqa: PLC0415
    from runledger_api.services.pricing_sync import (  # noqa: PLC0415
        get_sync_config,
        sync_catalog_to_db,
    )

    async def _run() -> dict[str, Any]:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with AsyncSession(engine) as db:
            config = await get_sync_config(db)
            if config is not None and not config.sync_enabled:
                log.info("pricing_catalog_sync_skipped", reason="disabled")
                return {"skipped_reason": "disabled", "inserted": 0, "updated": 0, "skipped": 0}
            result = await sync_catalog_to_db(db)
        await engine.dispose()
        return result

    return asyncio.run(_run())
