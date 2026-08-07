"""
Celery beat worker: alert rule evaluation (every 5 minutes).

For each active alert rule, computes the configured metric over the rule's
time window and fires a notification when the threshold is crossed.

Deduplication: a rule will not re-fire if it already fired within the current
window_minutes period.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.alerts import AlertFiring, AlertRule
from runledger_api.models.budgets import BudgetNotification
from runledger_api.models.events import AgentRun
from runledger_api.models.gateway import GatewayRequest, GatewayRoute
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.services.email import send_alert_fired_email
from runledger_api.services.email_utils import get_email_preference, get_workspace_admin_users
from runledger_api.services import kafka_export
from runledger_api.services.notifications import send_slack_message

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="alerts.evaluate_rules", max_retries=1)  # type: ignore[untyped-decorator]
def evaluate_alert_rules() -> dict[str, int]:
    """Evaluate all active alert rules; fire notifications when thresholds are crossed."""
    return asyncio.run(_run_evaluation())


async def _run_evaluation() -> dict[str, int]:
    factory = _make_session_factory()
    rules_checked = 0
    firings_created = 0

    async with factory() as session:
        # Load all active rules
        rules_result = await session.execute(select(AlertRule).where(AlertRule.is_active.is_(True)))
        rules: list[AlertRule] = list(rules_result.scalars().all())

        now = datetime.now(UTC)
        # Cache email preferences per workspace to avoid repeated DB lookups
        from runledger_api.models.email_prefs import (
            EmailPreference as _EmailPreference,  # noqa: F401
        )

        prefs_cache: dict[Any, Any] = {}

        for rule in rules:
            rules_checked += 1
            window_start = now - timedelta(minutes=rule.window_minutes)

            try:
                metric_value = await _compute_metric(
                    session, rule.workspace_id, rule.metric, window_start, now
                )
            except Exception as exc:
                log.warning(
                    "alerts.metric_compute_failed",
                    rule_id=str(rule.id),
                    metric=rule.metric,
                    error=str(exc),
                )
                continue

            if metric_value is None:
                continue

            # Check threshold
            threshold_crossed = (rule.operator == "gt" and metric_value > rule.threshold) or (
                rule.operator == "lt" and metric_value < rule.threshold
            )
            if not threshold_crossed:
                continue

            # Deduplication: skip if already fired in the current window
            dedup_stmt = select(AlertFiring).where(
                AlertFiring.rule_id == rule.id,
                AlertFiring.fired_at >= window_start,
            )
            dedup_result = await session.execute(dedup_stmt)
            if dedup_result.scalar_one_or_none() is not None:
                continue

            # Create firing record
            firing = AlertFiring(
                rule_id=rule.id,
                workspace_id=rule.workspace_id,
                metric_value=metric_value,
            )
            session.add(firing)
            await session.flush()
            firings_created += 1
            log.info(
                "alerts.rule_fired",
                rule_id=str(rule.id),
                rule_name=rule.name,
                metric=rule.metric,
                metric_value=str(metric_value),
                threshold=str(rule.threshold),
            )
            try:
                await kafka_export.publish_event(
                    session,
                    workspace_id=rule.workspace_id,
                    event_type="alert.fired",
                    payload={
                        "run_id": str(firing.id),
                        "alert_rule_id": str(rule.id),
                        "alert_firing_id": str(firing.id),
                        "metric": rule.metric,
                        "metric_value": str(metric_value),
                        "threshold": str(rule.threshold),
                        "operator": rule.operator,
                        "window_minutes": rule.window_minutes,
                        "fired_at": firing.fired_at.isoformat() if firing.fired_at else now.isoformat(),
                        "idempotency_key": f"alert-fired:{rule.id}:{firing.id}",
                        "source": "runledger.alerts",
                        "event_summary": f"Alert fired for {rule.metric}",
                    },
                )
            except Exception:
                log.exception("kafka_export.alert_fired_failed", rule_id=str(rule.id))

            # Send Slack notification if channel configured
            if rule.channel_id is not None:
                await _send_alert_notification(session, rule, metric_value, now)

            # Send email notifications if enabled
            if rule.email_enabled:
                # Check workspace email preferences
                ws_id = rule.workspace_id
                if ws_id not in prefs_cache:
                    prefs_cache[ws_id] = await get_email_preference(session, ws_id)
                prefs = prefs_cache[ws_id]
                if prefs is None or prefs.alerts_enabled:
                    await _send_alert_emails(session, rule, metric_value)

        await session.commit()

    log.info(
        "alerts.evaluation.done",
        rules_checked=rules_checked,
        firings_created=firings_created,
    )
    return {"rules_checked": rules_checked, "firings_created": firings_created}


async def _compute_metric(
    session: AsyncSession,
    workspace_id: Any,
    metric: str,
    window_start: datetime,
    window_end: datetime,
) -> Decimal | None:
    """Compute the named metric for the workspace over the given window."""

    if metric == "error_rate":
        total_stmt = select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= window_start,
            AgentRun.started_at < window_end,
        )
        total = (await session.execute(total_stmt)).scalar_one()
        if total == 0:
            return None
        failed_stmt = select(func.count(AgentRun.id)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= window_start,
            AgentRun.started_at < window_end,
            AgentRun.status == "failed",
        )
        failed = (await session.execute(failed_stmt)).scalar_one()
        return Decimal(str(failed / total))

    if metric == "p95_latency":
        # Compute p95 of (ended_at - started_at) in milliseconds
        latency_stmt = select(
            func.percentile_cont(0.95).within_group(
                func.extract("epoch", AgentRun.ended_at - AgentRun.started_at) * 1000
            )
        ).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= window_start,
            AgentRun.started_at < window_end,
            AgentRun.ended_at.isnot(None),
        )
        result = (await session.execute(latency_stmt)).scalar()
        if result is None:
            return None
        return Decimal(str(result))

    if metric == "avg_score":
        score_stmt = select(func.avg(ScoreEvent.value)).where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.created_at >= window_start,
            ScoreEvent.created_at < window_end,
        )
        result = (await session.execute(score_stmt)).scalar()
        if result is None:
            return None
        return Decimal(str(result))

    if metric == "spend_velocity":
        spend_stmt = select(func.coalesce(func.sum(AgentRun.total_cost_usd), 0)).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= window_start,
            AgentRun.started_at < window_end,
        )
        result = (await session.execute(spend_stmt)).scalar()
        return Decimal(str(result)) if result is not None else Decimal("0")

    if metric == "model_availability":
        routes_stmt = select(GatewayRoute).where(GatewayRoute.workspace_id == workspace_id)
        routes = list((await session.execute(routes_stmt)).scalars().all())
        considered = [route for route in routes if route.last_health_check_at is not None or route.is_active]
        if not considered:
            return None
        healthy = sum(1 for route in considered if route.deployment_status == "healthy")
        return Decimal(str(healthy / len(considered)))

    if metric == "gateway_overhead_p95":
        rows_stmt = select(GatewayRequest.config_fingerprint).where(
            GatewayRequest.workspace_id == workspace_id,
            GatewayRequest.route_id.is_not(None),
            GatewayRequest.created_at >= window_start,
            GatewayRequest.created_at < window_end,
            GatewayRequest.status == "success",
        )
        rows = (await session.execute(rows_stmt)).scalars().all()
        overheads: list[float] = []
        for cfg in rows:
            if not isinstance(cfg, dict):
                continue
            value = cfg.get("gateway_overhead_ms")
            try:
                if value is not None:
                    overheads.append(float(value))
            except (TypeError, ValueError):
                continue
        if not overheads:
            return None
        overheads.sort()
        index = min(len(overheads) - 1, max(0, int(len(overheads) * 0.95) - 1))
        return Decimal(str(round(overheads[index], 4)))

    return None


async def _send_alert_notification(
    session: AsyncSession,
    rule: AlertRule,
    metric_value: Decimal,
    fired_at: datetime,
) -> None:
    """Send a Slack notification for a fired alert rule."""
    notif = await session.get(BudgetNotification, rule.channel_id)
    if notif is None or not notif.is_active or notif.channel != "slack":
        return

    metric_label = {
        "error_rate": f"{float(metric_value) * 100:.1f}%",
        "p95_latency": f"{float(metric_value):.0f}ms",
        "avg_score": f"{float(metric_value):.3f}",
        "spend_velocity": f"${float(metric_value):.4f}",
        "model_availability": f"{float(metric_value) * 100:.1f}%",
        "gateway_overhead_p95": f"{float(metric_value):.0f}ms",
    }.get(rule.metric, str(metric_value))

    threshold_label = {
        "error_rate": f"{float(rule.threshold) * 100:.1f}%",
        "p95_latency": f"{float(rule.threshold):.0f}ms",
        "avg_score": f"{float(rule.threshold):.3f}",
        "spend_velocity": f"${float(rule.threshold):.4f}",
        "model_availability": f"{float(rule.threshold) * 100:.1f}%",
        "gateway_overhead_p95": f"{float(rule.threshold):.0f}ms",
    }.get(rule.metric, str(rule.threshold))

    operator_label = ">" if rule.operator == "gt" else "<"
    window_label = (
        f"{rule.window_minutes}m" if rule.window_minutes < 60 else f"{rule.window_minutes // 60}h"
    )

    fallback = (
        f"RunLedger Alert: {rule.name} — "
        f"{rule.metric} = {metric_label} {operator_label} {threshold_label} "
        f"(last {window_label})"
    )
    blocks: list[dict[str, object]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":rotating_light: RunLedger Alert Fired",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Rule:* {rule.name}"},
                {"type": "mrkdwn", "text": f"*Metric:* `{rule.metric}`"},
                {
                    "type": "mrkdwn",
                    "text": f"*Value:* {metric_label} {operator_label} {threshold_label}",
                },
                {"type": "mrkdwn", "text": f"*Window:* last {window_label}"},
                {
                    "type": "mrkdwn",
                    "text": f"*Fired at:* {fired_at.strftime('%Y-%m-%d %H:%M UTC')}",
                },
            ],
        },
    ]

    try:
        await send_slack_message(notif.destination_url, blocks, fallback)
    except Exception as exc:
        log.warning(
            "alerts.notification_failed",
            rule_id=str(rule.id),
            error=str(exc),
        )


async def _send_alert_emails(
    session: AsyncSession,
    rule: AlertRule,
    metric_value: Decimal,
) -> None:
    """Email workspace admins when an alert rule fires."""
    metric_label = {
        "error_rate": f"{float(metric_value) * 100:.1f}%",
        "p95_latency": f"{float(metric_value):.0f}ms",
        "avg_score": f"{float(metric_value):.3f}",
        "spend_velocity": f"${float(metric_value):.4f}",
        "model_availability": f"{float(metric_value) * 100:.1f}%",
        "gateway_overhead_p95": f"{float(metric_value):.0f}ms",
    }.get(rule.metric, str(metric_value))

    threshold_label = {
        "error_rate": f"{float(rule.threshold) * 100:.1f}%",
        "p95_latency": f"{float(rule.threshold):.0f}ms",
        "avg_score": f"{float(rule.threshold):.3f}",
        "spend_velocity": f"${float(rule.threshold):.4f}",
        "model_availability": f"{float(rule.threshold) * 100:.1f}%",
        "gateway_overhead_p95": f"{float(rule.threshold):.0f}ms",
    }.get(rule.metric, str(rule.threshold))

    try:
        # Look up workspace name
        ws_result = await session.execute(
            select(Workspace).where(Workspace.id == rule.workspace_id)
        )
        workspace = ws_result.scalar_one_or_none()
        ws_name = workspace.name if workspace else str(rule.workspace_id)

        admins = await get_workspace_admin_users(session, rule.workspace_id)
        await asyncio.gather(
            *[
                send_alert_fired_email(
                    to_email=u.email,
                    full_name=u.full_name,
                    rule_name=rule.name,
                    metric=rule.metric,
                    operator=rule.operator,
                    threshold=threshold_label,
                    value=metric_label,
                    workspace_name=ws_name,
                )
                for u in admins
            ],
            return_exceptions=True,
        )
    except Exception as exc:
        log.warning("alerts.email_failed", rule_id=str(rule.id), error=str(exc))
