"""
Finance system integration services.

  dispatch_billing_webhook   — HMAC-signed webhook on period close
  export_quickbooks_csv      — double-entry journal CSV for QuickBooks
  export_netsuite_csv        — journal entry CSV for NetSuite
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import hmac
import io
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.billing import BillingPeriod, ChargebackRule
from runledger_api.models.billing_webhooks import BillingWebhookConfig, BillingWebhookDelivery

log = structlog.get_logger()

_WEBHOOK_TIMEOUT = 10
_RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds between attempts


# ── HMAC signing ──────────────────────────────────────────────────────────────


def _sign_payload(body: bytes, secret: str) -> str:
    """Return sha256=<hex> HMAC signature of the raw JSON bytes."""
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ── Webhook dispatch ──────────────────────────────────────────────────────────


async def _build_webhook_payload(
    db: AsyncSession,
    period: BillingPeriod,
) -> dict[str, Any]:
    """Build the billing.period.closed webhook payload."""
    rules_result = await db.execute(
        select(ChargebackRule).where(ChargebackRule.workspace_id == period.workspace_id)
    )
    rules = list(rules_result.scalars().all())
    total = period.total_cost_usd or Decimal("0")

    chargeback_breakdown = [
        {
            "dimension": r.dimension,
            "allocation_type": r.allocation_type,
            "weight": str(r.weight),
            "allocated_usd": str((total * r.weight).quantize(Decimal("0.000001"))),
        }
        for r in rules
    ]

    return {
        "event": "billing.period.closed",
        "period_id": str(period.id),
        "workspace_id": str(period.workspace_id),
        "period_start": str(period.period_start),
        "period_end": str(period.period_end),
        "total_cost_usd": str(total),
        "snapshot_signature": period.snapshot_hash or "",
        "chargeback_breakdown": chargeback_breakdown,
        "closed_at": period.closed_at.isoformat() if period.closed_at else None,
    }


async def _attempt_delivery(
    url: str,
    secret: str,
    body: bytes,
    attempt: int,
) -> tuple[int | None, str | None, bool]:
    """
    POST body to url with HMAC signature header.
    Returns (http_status, response_body_text, success).
    """
    try:
        async with httpx.AsyncClient(timeout=_WEBHOOK_TIMEOUT) as client:
            resp = await client.post(
                url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-RunLedger-Signature": _sign_payload(body, secret),
                    "X-RunLedger-Event": "billing.period.closed",
                    "X-RunLedger-Attempt": str(attempt),
                },
            )
        success = 200 <= resp.status_code < 300
        return resp.status_code, resp.text[:1024], success
    except Exception as exc:
        log.warning("webhook_delivery_error", url=url, attempt=attempt, error=str(exc))
        return None, str(exc)[:256], False


async def dispatch_billing_webhook(
    db: AsyncSession,
    period: BillingPeriod,
) -> None:
    """
    Fire HMAC-signed billing.period.closed webhook to all enabled configs.
    Retries up to 3 times with exponential backoff.
    Logs each attempt in billing_webhook_deliveries.
    """
    configs_result = await db.execute(
        select(BillingWebhookConfig).where(
            BillingWebhookConfig.workspace_id == period.workspace_id,
            BillingWebhookConfig.enabled.is_(True),
        )
    )
    configs = list(configs_result.scalars().all())
    if not configs:
        return

    payload = await _build_webhook_payload(db, period)
    body = json.dumps(payload, default=str).encode()

    for cfg in configs:
        success = False
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            http_status, response_body, success = await _attempt_delivery(
                cfg.url, cfg.secret, body, attempt
            )
            now = datetime.now(UTC)
            delivery = BillingWebhookDelivery(
                webhook_config_id=cfg.id,
                billing_period_id=period.id,
                attempt=attempt,
                status="success" if success else "failed",
                response_status=http_status,
                response_body=response_body,
                delivered_at=now if success else None,
            )
            db.add(delivery)
            await db.flush()

            if success:
                log.info(
                    "webhook_delivered",
                    config_id=str(cfg.id),
                    period_id=str(period.id),
                    attempt=attempt,
                )
                break

            if attempt < len(_RETRY_DELAYS):
                await asyncio.sleep(delay)

        if not success:
            log.warning(
                "webhook_all_attempts_failed",
                config_id=str(cfg.id),
                period_id=str(period.id),
            )

    await db.commit()


# ── QuickBooks CSV export ─────────────────────────────────────────────────────


async def export_quickbooks_csv(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
) -> str:
    """
    Generate a QuickBooks-compatible double-entry journal CSV.

    For each chargeback rule:
      - DEBIT  cost centre / team account for allocated_usd
      - CREDIT "AI Spend Clearing" for allocated_usd

    If no rules are configured, a single line for the full period cost.
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")

    rules_result = await db.execute(
        select(ChargebackRule).where(ChargebackRule.workspace_id == period.workspace_id)
    )
    rules = list(rules_result.scalars().all())
    total = period.total_cost_usd or Decimal("0")
    date_str = str(period.period_end)
    ref = str(period.id)[:8]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Account", "Description", "Debit", "Credit", "Reference"])

    if rules:
        for rule in rules:
            allocated = (total * rule.weight).quantize(Decimal("0.01"))
            account_name = f"AI Spend - {rule.dimension}"
            description = (
                f"AI spend allocated to {rule.dimension} "
                f"({period.period_start} – {period.period_end})"
            )
            # Debit cost centre
            writer.writerow([date_str, account_name, description, str(allocated), "", ref])
            # Credit clearing
            writer.writerow([date_str, "AI Spend Clearing", description, "", str(allocated), ref])
    else:
        # No rules — single full-period entry
        description = f"AI spend {period.period_start} – {period.period_end}"
        writer.writerow([date_str, "AI Spend", description, str(total.quantize(Decimal("0.01"))), "", ref])
        writer.writerow([date_str, "AI Spend Clearing", description, "", str(total.quantize(Decimal("0.01"))), ref])

    return buf.getvalue()


# ── NetSuite CSV export ───────────────────────────────────────────────────────


async def export_netsuite_csv(
    db: AsyncSession,
    billing_period_id: uuid.UUID,
) -> str:
    """
    Generate a NetSuite-compatible journal entry CSV.

    Columns: ExternalId, Date, Account, Subsidiary, Department, Memo, Debit, Credit

    allocation_type='cost_center' → maps dimension to Department
    allocation_type='team'        → maps dimension to Department
    allocation_type='env'         → maps dimension to Subsidiary
    """
    period_result = await db.execute(
        select(BillingPeriod).where(BillingPeriod.id == billing_period_id)
    )
    period = period_result.scalar_one_or_none()
    if period is None:
        raise ValueError(f"BillingPeriod {billing_period_id} not found")

    rules_result = await db.execute(
        select(ChargebackRule).where(ChargebackRule.workspace_id == period.workspace_id)
    )
    rules = list(rules_result.scalars().all())
    total = period.total_cost_usd or Decimal("0")
    date_str = str(period.period_end)
    external_id_base = str(period.id)[:8]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ExternalId", "Date", "Account", "Subsidiary", "Department", "Memo", "Debit", "Credit"])

    memo = f"AI spend {period.period_start} – {period.period_end}"

    if rules:
        for i, rule in enumerate(rules):
            allocated = (total * rule.weight).quantize(Decimal("0.01"))
            subsidiary = rule.dimension if rule.allocation_type == "env" else ""
            department = rule.dimension if rule.allocation_type in ("cost_center", "team") else ""
            ext_id = f"{external_id_base}-{i + 1}"
            # Debit
            writer.writerow([ext_id, date_str, "AI Spend", subsidiary, department, memo, str(allocated), ""])
            # Credit
            writer.writerow([ext_id, date_str, "AI Spend Clearing", subsidiary, department, memo, "", str(allocated)])
    else:
        total_str = str(total.quantize(Decimal("0.01")))
        writer.writerow([external_id_base, date_str, "AI Spend", "", "", memo, total_str, ""])
        writer.writerow([external_id_base, date_str, "AI Spend Clearing", "", "", memo, "", total_str])

    return buf.getvalue()
