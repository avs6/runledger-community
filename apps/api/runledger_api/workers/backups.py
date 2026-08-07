from __future__ import annotations

from runledger_api.core.celery_app import celery_app
from runledger_api.services import backup_ops


@celery_app.task(name="backups.run_scheduled")
def run_scheduled() -> int:
    import asyncio

    return asyncio.run(backup_ops.run_scheduled_backups())
