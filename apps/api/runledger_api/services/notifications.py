"""
Slack Block Kit message formatters and HTTP dispatch.

Provides helpers for sending structured Slack alerts for budget breaches
and anomaly detections. No HMAC needed for outbound Slack webhook calls.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
import structlog

log = structlog.get_logger()


# ── Block Kit builders ────────────────────────────────────────────────────────


def build_budget_breach_blocks(
    budget_id: str,
    scope_type: str | None,
    scope_id: str | None,
    spend_usd: Decimal | str,
    limit_usd: Decimal | str,
    action: str | None,
) -> list[dict[str, Any]]:
    """Return Slack Block Kit JSON for a budget breach alert."""
    scope_label = f"{scope_type}:{scope_id}" if scope_id else (scope_type or "workspace")
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":rotating_light: RunLedger Budget Breach",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Budget ID*\n`{budget_id}`"},
                {"type": "mrkdwn", "text": f"*Scope*\n{scope_label}"},
                {"type": "mrkdwn", "text": f"*Spend*\n${spend_usd}"},
                {"type": "mrkdwn", "text": f"*Limit*\n${limit_usd}"},
                {"type": "mrkdwn", "text": f"*Action taken*\n{action or '—'}"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Sent by <https://runledger.io|RunLedger>",
                }
            ],
        },
    ]


def build_anomaly_blocks(
    user_id: str,
    daily_spend: Decimal | str,
    mean_spend: Decimal | str,
    zscore: Decimal | str,
    reason: str,
) -> list[dict[str, Any]]:
    """Return Slack Block Kit JSON for an anomaly detection alert."""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":warning: RunLedger Spend Anomaly Detected",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*User*\n`{user_id}`"},
                {"type": "mrkdwn", "text": f"*Daily spend*\n${daily_spend}"},
                {"type": "mrkdwn", "text": f"*30d mean*\n${mean_spend}"},
                {"type": "mrkdwn", "text": f"*Z-score*\n{zscore}σ"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Reason:* {reason}"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Sent by <https://runledger.io|RunLedger>",
                }
            ],
        },
    ]


def build_test_blocks() -> list[dict[str, Any]]:
    """Return Slack Block Kit JSON for a connectivity test message."""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":white_check_mark: RunLedger — Test Alert",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Your Slack integration is connected successfully. "
                "You will receive budget breach and anomaly alerts here.",
            },
        },
    ]


# ── Slack HTTP dispatch ───────────────────────────────────────────────────────


async def send_slack_message(
    webhook_url: str,
    blocks: list[dict[str, Any]],
    fallback_text: str,
) -> None:
    """
    POST a Block Kit message to a Slack incoming webhook URL.

    Raises httpx.HTTPError on non-2xx responses.
    """
    payload = {"text": fallback_text, "blocks": blocks}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
    log.info("slack.message.sent", fallback_text=fallback_text)
