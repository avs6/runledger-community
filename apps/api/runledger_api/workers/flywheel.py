"""
Optimization flywheel worker (Phase 7).

Nightly job: for each recently-active workspace, run the flywheel analysis (aggregate the
recorded (config, cost, quality) tuples → analyzer → persist recommendations, auto-applying
the safe ones when the workspace is in `auto` mode), then check applied recommendations for
SLA breach and roll back any that no longer hold.

Fail-open and best-effort: any error for a workspace is logged and skipped; the task never
crashes the worker. Scheduled via Celery beat (daily).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.gateway import GatewayRequest
from runledger_api.services import flywheel

log = logging.getLogger(__name__)


async def _active_workspaces(db) -> list[str]:
    since = datetime.now(UTC) - timedelta(days=1)
    rows = await db.execute(
        select(GatewayRequest.workspace_id).where(GatewayRequest.created_at >= since).distinct()
    )
    return [str(r[0]) for r in rows.all()]


async def _run() -> dict[str, int]:
    if not flywheel.enabled():
        return {"workspaces": 0, "recommendations": 0, "auto_applied": 0, "rolled_back": 0}
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    workspaces = recs = applied = rolled = 0
    async with factory() as db:
        for ws in await _active_workspaces(db):
            try:
                result = await flywheel.run_analysis(db, ws)
                if result.get("status") == "ok":
                    workspaces += 1
                    recs += result.get("recommendations", 0)
                    applied += result.get("auto_applied", 0)
                rolled += await flywheel.check_guardrails(db, ws)
            except Exception as exc:  # noqa: BLE001 — fail-open per workspace
                log.warning("flywheel_worker_skipped ws=%s error=%s", ws, str(exc))
                await db.rollback()
    await engine.dispose()
    return {
        "workspaces": workspaces,
        "recommendations": recs,
        "auto_applied": applied,
        "rolled_back": rolled,
    }


@celery_app.task(name="flywheel.analyze")  # type: ignore[untyped-decorator]
def analyze() -> dict[str, int]:
    """Run the cost x quality flywheel for each active workspace."""
    result = asyncio.run(_run())
    log.info(
        "flywheel workspaces=%s recommendations=%s auto_applied=%s rolled_back=%s",
        result["workspaces"],
        result["recommendations"],
        result["auto_applied"],
        result["rolled_back"],
    )
    return result
