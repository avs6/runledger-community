"""
Celery beat worker: weekly analytics email report (every Monday 07:00 UTC).

For each workspace with spend in the last 7 days, emails all workspace admin
and editor users a usage summary table.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.metering import UsageDaily
from runledger_api.models.tenant import Workspace
from runledger_api.services.email import send_analytics_report_email
from runledger_api.services.email_utils import get_email_preference, get_workspace_admin_users

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="email_reports.send_weekly_analytics", max_retries=1)  # type: ignore[untyped-decorator]
def send_weekly_analytics() -> dict[str, int]:
    """Email weekly analytics reports to all workspace admins."""
    return asyncio.run(_run_weekly_reports())


async def _run_weekly_reports() -> dict[str, int]:
    factory = _make_session_factory()
    workspaces_processed = 0
    emails_sent = 0

    t_to = datetime.now(UTC)
    t_from = t_to - timedelta(days=7)
    period_label = f"{t_from.strftime('%b %d')} – {t_to.strftime('%b %d, %Y')}"

    async with factory() as session:
        # Load all workspaces
        ws_result = await session.execute(select(Workspace))
        workspaces = list(ws_result.scalars().all())

        for workspace in workspaces:
            try:
                # Query last 7 days of usage for this workspace
                stmt = (
                    select(UsageDaily)
                    .where(
                        UsageDaily.workspace_id == workspace.id,
                        UsageDaily.day >= t_from.date(),
                        UsageDaily.day <= t_to.date(),
                    )
                    .order_by(UsageDaily.day.desc())
                )
                result = await session.execute(stmt)
                rows_orm = result.scalars().all()

                if not rows_orm:
                    continue  # skip workspaces with no activity

                # Check email preferences — skip if report_frequency is 'never'
                prefs = await get_email_preference(session, workspace.id)
                if prefs is not None and prefs.report_frequency == "never":
                    continue

                items = [
                    {
                        "date": str(row.day),
                        "provider": row.provider,
                        "model": row.model,
                        "cost_usd": str(row.cost_usd),
                        "input_tokens": row.input_tokens,
                        "output_tokens": row.output_tokens,
                        "call_count": row.call_count,
                    }
                    for row in rows_orm
                ]
                total_cost = str(round(sum(float(r["cost_usd"]) for r in items), 6))

                admins = await get_workspace_admin_users(session, workspace.id)
                if not admins:
                    continue

                ws_name = getattr(workspace, "name", str(workspace.id))
                workspaces_processed += 1

                for u in admins:
                    await send_analytics_report_email(
                        to_email=u.email,
                        full_name=u.full_name,
                        period_label=period_label,
                        rows=items,  # type: ignore[arg-type]
                        total_cost=total_cost,
                        workspace_name=ws_name,
                    )
                    emails_sent += 1

            except Exception as exc:
                log.warning(
                    "email_reports.workspace_failed",
                    workspace_id=str(workspace.id),
                    error=str(exc),
                )

    log.info(
        "email_reports.weekly_done",
        workspaces_processed=workspaces_processed,
        emails_sent=emails_sent,
    )
    return {"workspaces_processed": workspaces_processed, "emails_sent": emails_sent}
