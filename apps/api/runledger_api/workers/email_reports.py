"""
Celery beat worker: scheduled analytics email reports.

For each workspace with spend in the configured reporting window, emails all
configured recipients a usage summary table.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.email_prefs import EmailPreference
from runledger_api.models.metering import UsageDaily
from runledger_api.models.tenant import Workspace
from runledger_api.services import kafka_export
from runledger_api.services.email import send_analytics_report_email
from runledger_api.services.email_utils import get_email_preference, get_workspace_admin_users

log = structlog.get_logger()


@dataclass(frozen=True)
class ReportRecipient:
    email: str
    full_name: str | None = None


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _timezone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _window_for_frequency(frequency: str) -> tuple[int, str]:
    if frequency == "daily":
        return 1, "Daily"
    if frequency == "monthly":
        return 30, "Monthly"
    return 7, "Weekly"


def _already_sent(prefs: EmailPreference | None, local_now: datetime, frequency: str) -> bool:
    sent_at = getattr(prefs, "report_last_sent_at", None)
    if sent_at is None:
        return False
    local_sent = sent_at.astimezone(local_now.tzinfo)
    if frequency == "daily":
        return bool(local_sent.date() == local_now.date())
    if frequency == "monthly":
        return bool(local_sent.year == local_now.year and local_sent.month == local_now.month)
    sent_year, sent_week, _ = local_sent.isocalendar()
    now_year, now_week, _ = local_now.isocalendar()
    return bool(sent_year == now_year and sent_week == now_week)


def _should_send_report(prefs: EmailPreference | None, now_utc: datetime) -> bool:
    frequency = getattr(prefs, "report_frequency", "weekly")
    if frequency == "never":
        return False

    local_now = now_utc.astimezone(_timezone(getattr(prefs, "report_timezone", "UTC")))
    report_hour = int(getattr(prefs, "report_hour", 7) or 7)
    if local_now.hour != report_hour:
        return False
    if frequency == "weekly" and local_now.weekday() != 0:
        return False
    if frequency == "monthly" and local_now.day != 1:
        return False
    return not _already_sent(prefs, local_now, frequency)


def _custom_recipients(raw: str | None) -> list[ReportRecipient]:
    if not raw:
        return []
    candidates = raw.replace("\n", ",").split(",")
    return [
        ReportRecipient(email=email.strip(), full_name="RunLedger report recipient")
        for email in candidates
        if "@" in email.strip()
    ]


async def _recipients_for(
    session: AsyncSession,
    workspace_id: object,
    prefs: EmailPreference | None,
) -> list[ReportRecipient]:
    mode = getattr(prefs, "report_recipient_mode", "workspace_admins")
    if mode == "custom":
        return _custom_recipients(getattr(prefs, "report_recipients", None))

    admins = await get_workspace_admin_users(session, workspace_id)  # type: ignore[arg-type]
    return [ReportRecipient(email=u.email, full_name=u.full_name) for u in admins]


@celery_app.task(name="email_reports.send_weekly_analytics", max_retries=1)  # type: ignore[untyped-decorator]
def send_weekly_analytics() -> dict[str, int]:
    """Email scheduled analytics reports to configured recipients."""
    return asyncio.run(_run_weekly_reports())


async def _run_weekly_reports() -> dict[str, int]:
    if not (settings.email_enabled and settings.email_reports_enabled):
        log.info(
            "email_reports.skipped_disabled",
            email_enabled=settings.email_enabled,
            email_reports_enabled=settings.email_reports_enabled,
        )
        return {"workspaces_processed": 0, "emails_sent": 0, "skipped_disabled": 1}

    factory = _make_session_factory()
    workspaces_processed = 0
    emails_sent = 0

    t_to = datetime.now(UTC)

    async with factory() as session:
        ws_result = await session.execute(select(Workspace))
        workspaces = list(ws_result.scalars().all())

        for workspace in workspaces:
            try:
                prefs = await get_email_preference(session, workspace.id)
                if not _should_send_report(prefs, t_to):
                    continue

                frequency = getattr(prefs, "report_frequency", "weekly")
                window_days, cadence_label = _window_for_frequency(frequency)
                t_from = t_to - timedelta(days=window_days)
                period_label = (
                    f"{cadence_label} report: "
                    f"{t_from.strftime('%b %d')} - {t_to.strftime('%b %d, %Y')}"
                )

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
                total_cost = str(round(sum((float(str(r["cost_usd"])) for r in items), 0.0), 6))

                recipients = await _recipients_for(session, workspace.id, prefs)
                if not recipients:
                    continue

                ws_name = getattr(workspace, "name", str(workspace.id))
                workspaces_processed += 1

                for recipient in recipients:
                    await send_analytics_report_email(
                        to_email=recipient.email,
                        full_name=recipient.full_name,
                        period_label=period_label,
                        rows=items,
                        total_cost=total_cost,
                        workspace_name=ws_name,
                        template=getattr(prefs, "report_template", "detailed"),
                    )
                    try:
                        await kafka_export.publish_event(
                            session,
                            workspace_id=workspace.id,
                            event_type="email.report.sent",
                            payload={
                                "run_id": str(workspace.id),
                                "workspace_name": ws_name,
                                "recipient": recipient.email,
                                "cadence": frequency,
                                "period_label": period_label,
                                "total_cost_usd": total_cost,
                                "template": getattr(prefs, "report_template", "detailed"),
                                "idempotency_key": f"email-report:{workspace.id}:{recipient.email}:{t_to.date()}:{frequency}",
                                "source": "runledger.email",
                                "event_summary": "Scheduled analytics report sent",
                            },
                        )
                    except Exception:
                        log.exception(
                            "kafka_export.email_report_failed",
                            workspace_id=str(workspace.id),
                            recipient=recipient.email,
                        )
                    emails_sent += 1

                if prefs is not None:
                    prefs.report_last_sent_at = t_to
                    await session.commit()

            except Exception as exc:
                await session.rollback()
                log.warning(
                    "email_reports.workspace_failed",
                    workspace_id=str(workspace.id),
                    error=str(exc),
                )

    log.info(
        "email_reports.scheduled_done",
        workspaces_processed=workspaces_processed,
        emails_sent=emails_sent,
    )
    return {"workspaces_processed": workspaces_processed, "emails_sent": emails_sent}
