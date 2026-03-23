"""
Celery tasks for batch evaluation and judge drift detection.

Tasks
-----
batch_evaluate(evaluator_id, run_ids, limit)
    Run an evaluator against a batch of recent agent runs.

detect_judge_drift()
    Compare average LLM-judge scores over the last 7 days vs the prior 7 days.
    Fires Slack alerts if drift exceeds 20%.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings

log = structlog.get_logger()


def _get_sync_session():  # type: ignore[return]
    """Return a sync SQLAlchemy session (NullPool, safe for Celery workers)."""
    from sqlalchemy.pool import NullPool

    engine = create_engine(
        settings.database_url.replace("+asyncpg", ""),
        poolclass=NullPool,
    )
    Session = sessionmaker(bind=engine)  # noqa: N806
    return Session()


async def _run_batch(
    evaluator_id: uuid.UUID,
    run_ids: list[uuid.UUID] | None,
    limit: int,
) -> dict[str, int]:
    """Async implementation of batch evaluation."""
    from sqlalchemy.pool import NullPool

    async_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    AsyncSessionLocal = sessionmaker(  # noqa: N806
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    from runledger_api.models.evaluators import Evaluator
    from runledger_api.models.events import AgentRun
    from runledger_api.models.scores import ScoreEvent
    from runledger_api.services.evaluators import evaluate_run

    evaluated = 0
    scores_created = 0
    errors = 0

    async with AsyncSessionLocal() as db:
        # Load evaluator
        result = await db.execute(select(Evaluator).where(Evaluator.id == evaluator_id))
        evaluator = result.scalar_one_or_none()
        if evaluator is None or evaluator.status != "active":
            log.warning("evaluator_not_found_or_inactive", evaluator_id=str(evaluator_id))
            await async_engine.dispose()
            return {"evaluated": 0, "scores_created": 0, "errors": 0}

        # Resolve runs to evaluate
        stmt = select(AgentRun).where(AgentRun.workspace_id == evaluator.workspace_id)
        if run_ids:
            stmt = stmt.where(AgentRun.id.in_(run_ids))
        else:
            stmt = (
                stmt.where(AgentRun.status == "succeeded")
                .order_by(AgentRun.started_at.desc())
                .limit(limit)
            )
        run_result = await db.execute(stmt)
        runs = run_result.scalars().all()

        for run in runs:
            evaluated += 1
            run_dict: dict[str, Any] = {
                "id": str(run.id),
                "status": run.status,
                "feature_tag": run.feature_tag,
                "deployment_version": run.deployment_version,
                "total_cost_usd": str(run.total_cost_usd) if run.total_cost_usd else None,
                "total_input_tokens": run.total_input_tokens,
                "total_output_tokens": run.total_output_tokens,
                "duration_ms": run.duration_ms,
            }

            try:
                score_value, evidence = await evaluate_run(
                    evaluator.type, evaluator.config, run_dict
                )
                score = ScoreEvent(
                    workspace_id=evaluator.workspace_id,
                    run_id=run.id,
                    name=evaluator.name,
                    value=score_value,
                    source="llm" if evaluator.type == "llm_judge" else "rule",
                    confidence=Decimal("0.9") if evaluator.type == "llm_judge" else Decimal("1.0"),
                    evidence=evidence,
                    evaluator_id=evaluator_id,
                )
                db.add(score)
                scores_created += 1
            except Exception as exc:
                errors += 1
                log.warning(
                    "evaluator_run_error",
                    evaluator_id=str(evaluator_id),
                    run_id=str(run.id),
                    error=str(exc),
                )

        # Update evaluator stats
        await db.execute(
            update(Evaluator)
            .where(Evaluator.id == evaluator_id)
            .values(
                last_run_at=datetime.now(UTC),
                last_run_count=Evaluator.last_run_count + scores_created,
            )
        )
        await db.commit()

    await async_engine.dispose()
    return {"evaluated": evaluated, "scores_created": scores_created, "errors": errors}


@celery_app.task(name="evaluators.batch_evaluate")  # type: ignore[untyped-decorator]
def batch_evaluate(
    evaluator_id: str,
    run_ids: list[str] | None = None,
    limit: int = 100,
) -> dict[str, int]:
    """Celery task: run an evaluator against a batch of agent runs."""
    eid = uuid.UUID(evaluator_id)
    rids = [uuid.UUID(r) for r in run_ids] if run_ids else None
    result = asyncio.run(_run_batch(eid, rids, limit))
    log.info("batch_evaluate_done", evaluator_id=evaluator_id, **result)
    return result


# ── Judge drift detection ─────────────────────────────────────────────────────


async def _detect_drift() -> list[dict[str, Any]]:
    """Compare LLM-judge scores over last 7d vs prior 7d per evaluator."""
    from sqlalchemy.pool import NullPool

    async_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    AsyncSessionLocal = sessionmaker(  # noqa: N806
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    from sqlalchemy import func

    from runledger_api.models.evaluators import Evaluator
    from runledger_api.models.scores import ScoreEvent

    now = datetime.now(UTC)
    current_start = now - timedelta(days=7)
    prior_start = now - timedelta(days=14)
    prior_end = current_start

    drift_items: list[dict[str, Any]] = []

    async with AsyncSessionLocal() as db:
        # Load all active LLM judge evaluators
        ev_result = await db.execute(
            select(Evaluator).where(
                Evaluator.type == "llm_judge",
                Evaluator.status == "active",
            )
        )
        evaluators = ev_result.scalars().all()

        for ev in evaluators:
            # Current window avg
            cur_result = await db.execute(
                select(func.avg(ScoreEvent.value)).where(
                    ScoreEvent.evaluator_id == ev.id,
                    ScoreEvent.created_at >= current_start,
                )
            )
            current_avg = cur_result.scalar()

            # Prior window avg
            prior_result = await db.execute(
                select(func.avg(ScoreEvent.value)).where(
                    ScoreEvent.evaluator_id == ev.id,
                    ScoreEvent.created_at >= prior_start,
                    ScoreEvent.created_at < prior_end,
                )
            )
            prior_avg = prior_result.scalar()

            if current_avg is None or prior_avg is None or float(prior_avg) == 0:
                continue

            change_pct = (float(current_avg) - float(prior_avg)) / float(prior_avg) * 100.0

            if abs(change_pct) >= 20.0:
                drift_items.append(
                    {
                        "evaluator_id": str(ev.id),
                        "evaluator_name": ev.name,
                        "workspace_id": str(ev.workspace_id),
                        "current_avg": float(current_avg),
                        "prior_avg": float(prior_avg),
                        "change_pct": change_pct,
                    }
                )

    await async_engine.dispose()
    return drift_items


@celery_app.task(name="evaluators.detect_judge_drift")  # type: ignore[untyped-decorator]
def detect_judge_drift() -> None:
    """Celery beat task: detect judge score drift and log warnings."""
    drift_items = asyncio.run(_detect_drift())

    for item in drift_items:
        direction = "degraded" if item["change_pct"] < 0 else "improved"
        log.warning(
            "judge_drift_detected",
            evaluator_id=item["evaluator_id"],
            evaluator_name=item["evaluator_name"],
            workspace_id=item["workspace_id"],
            current_avg=item["current_avg"],
            prior_avg=item["prior_avg"],
            change_pct=item["change_pct"],
            direction=direction,
        )

        # Attempt Slack notification if workspace has a configured webhook
        try:
            _notify_drift(item)
        except Exception as exc:
            log.debug("drift_slack_notify_failed", error=str(exc))

    log.info("judge_drift_check_complete", drifted=len(drift_items))


def _notify_drift(item: dict[str, Any]) -> None:
    """Fire-and-forget Slack notification for drift (sync, runs in Celery thread)."""
    import asyncio as _asyncio

    from runledger_api.services.notifications import send_slack_message

    # Look up workspace Slack webhook synchronously
    session = _get_sync_session()
    try:
        from runledger_api.models.tenant import Workspace

        ws = session.get(Workspace, uuid.UUID(item["workspace_id"]))
        if ws is None or not getattr(ws, "slack_webhook_url", None):
            return
        webhook_url: str = ws.slack_webhook_url  # type: ignore[attr-defined]
    finally:
        session.close()

    direction = "degraded" if item["change_pct"] < 0 else "improved"
    pct = abs(item["change_pct"])

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Judge Drift Alert* — evaluator `{item['evaluator_name']}` has "
                    f"*{direction}* by {pct:.1f}% over the last 7 days.\n"
                    f"Current avg: `{item['current_avg']:.4f}` | Prior avg: `{item['prior_avg']:.4f}`"
                ),
            },
        }
    ]

    _asyncio.run(
        send_slack_message(
            webhook_url,
            blocks,
            f"Judge drift detected: {item['evaluator_name']} {direction} {pct:.1f}%",
        )
    )
