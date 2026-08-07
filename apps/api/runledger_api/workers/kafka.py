from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.services import kafka_export

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="kafka.retry_pending_deliveries", max_retries=1)  # type: ignore[untyped-decorator]
def retry_pending_deliveries() -> dict[str, int]:
    return asyncio.run(_run_retry_pending_deliveries())


async def _run_retry_pending_deliveries() -> dict[str, int]:
    factory = _make_session_factory()
    async with factory() as session:
        processed = await kafka_export.process_pending_deliveries(session)
    if processed:
        log.info("kafka.retry_pending.processed", deliveries=processed)
    return {"processed": processed}
