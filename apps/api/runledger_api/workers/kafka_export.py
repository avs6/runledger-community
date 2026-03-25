"""
Celery tasks for Kafka event export.

kafka_export.dispatch — publishes a single event to all subscribed Kafka configs
                        for the workspace.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings

log = structlog.get_logger()


@celery_app.task(name="kafka_export.dispatch")  # type: ignore[untyped-decorator]
def dispatch_kafka_event(
    workspace_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Publish a single event to Kafka for all enabled, subscribed configs in the
    workspace.  Called as fire-and-forget (.delay()) from pipeline, alerts, and
    budget workers.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: PLC0415

    from runledger_api.services.kafka_export import dispatch_to_kafka  # noqa: PLC0415

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with AsyncSession(engine) as session:
            await dispatch_to_kafka(session, workspace_id, event_type, payload)
        await engine.dispose()

    try:
        asyncio.run(_run())
        return {"ok": True, "workspace_id": workspace_id, "event_type": event_type}
    except Exception as exc:
        log.warning(
            "kafka_export_task_error",
            workspace_id=workspace_id,
            event_type=event_type,
            error=str(exc),
        )
        return {"ok": False, "error": str(exc)}
