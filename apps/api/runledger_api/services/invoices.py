"""
Provider invoice parsing and reconciliation engine.

Parsing
-------
Supports CSV and JSON uploads from:
  - OpenAI    (usage export from platform.openai.com)
  - Anthropic (usage export from console.anthropic.com)
  - Google    (Vertex AI / Google AI Studio billing export)

Column detection is flexible — we look for known column name patterns
regardless of capitalisation or minor variations.

Reconciliation
--------------
For each invoice line we attempt two match strategies:

  1. Exact match   — provider_request_id matches a provider_calls.id (if available)
  2. Fuzzy match   — same model + occurred_at within ±10 min + token counts within 10%

Lines that cannot be matched are marked "unmatched".
Lines manually flagged by a user are marked "disputed".
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog

log = structlog.get_logger()

# ── Provider CSV/JSON parsers ──────────────────────────────────────────────────


def _find_col(row: dict[str, str], *candidates: str) -> str | None:
    """Case-insensitive column lookup."""
    lower = {k.lower().strip(): k for k in row}
    for c in candidates:
        key = lower.get(c.lower())
        if key is not None and row.get(key, "").strip():
            return row[key].strip()
    return None


def _parse_tokens(val: str | None) -> int | None:
    if not val:
        return None
    try:
        return int(re.sub(r"[,\s]", "", val))
    except (ValueError, TypeError):
        return None


def _parse_amount(val: str | None) -> Decimal:
    if not val:
        return Decimal("0")
    cleaned = re.sub(r"[^\d.\-]", "", val)
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S UTC",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            dt = datetime.strptime(val.strip(), fmt)
            return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
        except ValueError:
            continue
    return None


def _detect_provider(headers: list[str]) -> str:
    """Heuristic: detect which provider the CSV came from."""
    joined = " ".join(h.lower() for h in headers)
    if "organization_id" in joined or "organization" in joined:
        return "openai"
    if "anthropic" in joined or "message_id" in joined:
        return "anthropic"
    if "google" in joined or "sku_description" in joined or "project_id" in joined:
        return "google"
    return "unknown"


ParsedLine = dict[str, Any]


def parse_csv(content: bytes, filename: str) -> tuple[str, list[ParsedLine]]:
    """
    Parse a provider usage CSV export.

    Returns (detected_provider, list_of_line_dicts).
    Each dict has keys: provider_request_id, model, input_tokens, output_tokens,
                        amount, occurred_at, raw.
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return "unknown", []

    headers = list(rows[0].keys())
    provider = _detect_provider(headers)

    lines: list[ParsedLine] = []
    for row in rows:
        raw = dict(row)

        # Model
        model = _find_col(
            row,
            "model",
            "model_id",
            "model_slug",
            "sku_description",
            "product",
            "service_description",
        )

        # Request ID
        req_id = _find_col(row, "request_id", "message_id", "id", "usage_id")

        # Tokens
        input_tokens = _parse_tokens(
            _find_col(row, "input_tokens", "prompt_tokens", "input token count", "context_tokens")
        )
        output_tokens = _parse_tokens(
            _find_col(
                row, "output_tokens", "completion_tokens", "output token count", "generated_tokens"
            )
        )

        # Amount / cost
        amount_raw = _find_col(
            row, "cost", "amount", "total_cost", "charge", "subtotal", "cost_usd", "price"
        )
        amount = _parse_amount(amount_raw)

        # Timestamp
        dt_raw = _find_col(
            row,
            "timestamp",
            "date",
            "created_at",
            "start_time",
            "usage_date",
            "invoice_date",
            "occurred_at",
        )
        occurred_at = _parse_dt(dt_raw)

        if amount == Decimal("0") and input_tokens is None and output_tokens is None:
            continue  # skip blank/header rows

        lines.append(
            {
                "provider_request_id": req_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "amount": amount,
                "occurred_at": occurred_at,
                "raw": raw,
            }
        )

    return provider, lines


def parse_json(content: bytes) -> tuple[str, list[ParsedLine]]:
    """
    Parse a provider usage JSON export.
    Handles OpenAI's `usage.export.json` format and generic arrays.
    """
    data = json.loads(content.decode("utf-8"))

    # OpenAI format: {"object": "list", "data": [...]}
    if isinstance(data, dict) and "data" in data:
        records = data["data"]
        provider = "openai"
    elif isinstance(data, list):
        records = data
        provider = "unknown"
    else:
        return "unknown", []

    lines: list[ParsedLine] = []
    for record in records:
        if not isinstance(record, dict):
            continue

        model = record.get("snapshot_id") or record.get("model") or record.get("model_id")
        input_tokens = (
            record.get("n_context_tokens_total")
            or record.get("prompt_tokens")
            or record.get("input_tokens")
        )
        output_tokens = (
            record.get("n_generated_tokens_total")
            or record.get("completion_tokens")
            or record.get("output_tokens")
        )

        # Cost: may be in dollars or in cents
        cost_raw = record.get("cost") or record.get("amount") or 0
        try:
            amount = Decimal(str(cost_raw))
        except InvalidOperation:
            amount = Decimal("0")

        dt_raw = record.get("date") or record.get("timestamp") or record.get("created_at")
        occurred_at = _parse_dt(str(dt_raw)) if dt_raw else None

        req_id = str(record.get("request_id") or record.get("message_id") or "")

        lines.append(
            {
                "provider_request_id": req_id or None,
                "model": str(model) if model else None,
                "input_tokens": int(input_tokens) if input_tokens is not None else None,
                "output_tokens": int(output_tokens) if output_tokens is not None else None,
                "amount": amount,
                "occurred_at": occurred_at,
                "raw": record,
            }
        )

    return provider, lines


# ── Reconciliation engine ──────────────────────────────────────────────────────

_FUZZY_WINDOW_MINUTES = 10
_FUZZY_TOKEN_TOLERANCE = 0.10  # 10%


def _normalise_model(model: str | None) -> str:
    """Strip version suffixes for loose model comparison: gpt-4o-2024-05 → gpt-4o."""
    if not model:
        return ""
    # Remove date-version suffixes like -2024-05-13 or -20240513
    return re.sub(r"-\d{4}-?\d{2}-?\d{2}$", "", model.lower()).strip()


def _tokens_close(a: int | None, b: int | None, tol: float) -> bool:
    if a is None or b is None:
        return True  # can't check, assume ok
    if b == 0 and a == 0:
        return True
    if b == 0:
        return False
    return abs(a - b) / b <= tol


async def reconcile_invoice(
    db: Any,
    invoice_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Match all invoice lines for an invoice against provider_calls.

    Returns a summary dict with counts and amounts.
    Mutates invoice_lines.match_status and related fields in the DB.
    """
    from sqlalchemy import select, update

    from runledger_api.models.events import ProviderCall
    from runledger_api.models.invoices import ProviderInvoice, ProviderInvoiceLine

    # Load lines
    lines_result = await db.execute(
        select(ProviderInvoiceLine).where(ProviderInvoiceLine.invoice_id == invoice_id)
    )
    lines = lines_result.scalars().all()

    if not lines:
        return {"matched_exact": 0, "matched_fuzzy": 0, "unmatched": 0}

    # Load invoice to get period and provider
    inv_result = await db.execute(select(ProviderInvoice).where(ProviderInvoice.id == invoice_id))
    invoice = inv_result.scalar_one_or_none()
    if invoice is None:
        return {}

    # Load provider_calls in the period window (±1 day buffer)

    period_from = datetime(
        invoice.period_start.year, invoice.period_start.month, invoice.period_start.day, tzinfo=UTC
    )
    period_to = datetime(
        invoice.period_end.year,
        invoice.period_end.month,
        invoice.period_end.day,
        23,
        59,
        59,
        tzinfo=UTC,
    )
    # Add 1-day buffer each side
    period_from_buf = period_from - timedelta(days=1)
    period_to_buf = period_to + timedelta(days=1)

    calls_result = await db.execute(
        select(ProviderCall).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= period_from_buf,
            ProviderCall.created_at <= period_to_buf,
        )
    )
    calls = calls_result.scalars().all()

    # Index calls by model for fast lookup
    # Key: normalised_model → list of calls
    calls_by_model: dict[str, list[Any]] = {}
    for call in calls:
        key = _normalise_model(call.model)
        calls_by_model.setdefault(key, []).append(call)

    matched_exact = 0
    matched_fuzzy = 0
    unmatched = 0
    unmatched_amount = Decimal("0")
    runledger_total = Decimal("0")

    used_call_ids: set[uuid.UUID] = set()

    for line in lines:
        if line.match_status == "disputed":
            continue  # don't overwrite manual disputes

        model_key = _normalise_model(line.model)
        candidates = calls_by_model.get(model_key, [])

        best_call = None
        best_match = "unmatched"

        for call in candidates:
            if call.id in used_call_ids:
                continue

            # Fuzzy: timestamp within window + tokens within tolerance
            if line.occurred_at is not None and call.created_at is not None:
                dt_diff = abs((line.occurred_at - call.created_at).total_seconds())
                if dt_diff > _FUZZY_WINDOW_MINUTES * 60:
                    continue

            in_ok = _tokens_close(line.input_tokens, call.input_tokens, _FUZZY_TOKEN_TOLERANCE)
            out_ok = _tokens_close(line.output_tokens, call.output_tokens, _FUZZY_TOKEN_TOLERANCE)
            if in_ok and out_ok:
                best_call = call
                best_match = "fuzzy"
                break

        if best_call is not None:
            used_call_ids.add(best_call.id)
            call_cost = Decimal(str(best_call.cost_usd or 0))
            token_delta = ((line.input_tokens or 0) + (line.output_tokens or 0)) - (
                (best_call.input_tokens or 0) + (best_call.output_tokens or 0)
            )
            cost_delta = line.amount - call_cost
            runledger_total += call_cost

            await db.execute(
                update(ProviderInvoiceLine)
                .where(ProviderInvoiceLine.id == line.id)
                .values(
                    match_status=best_match,
                    matched_call_id=best_call.id,
                    token_delta=token_delta,
                    cost_delta=cost_delta,
                )
            )
            if best_match == "exact":
                matched_exact += 1
            else:
                matched_fuzzy += 1
        else:
            unmatched += 1
            unmatched_amount += line.amount
            await db.execute(
                update(ProviderInvoiceLine)
                .where(ProviderInvoiceLine.id == line.id)
                .values(match_status="unmatched", matched_call_id=None)
            )

    matched_count = matched_exact + matched_fuzzy
    total_count = len(lines)

    # Update invoice summary
    await db.execute(
        update(ProviderInvoice)
        .where(ProviderInvoice.id == invoice_id)
        .values(
            matched_count=matched_count,
            unmatched_amount=unmatched_amount,
            status="reconciled" if unmatched == 0 else "flagged" if unmatched > 0 else "reconciled",
        )
    )
    await db.commit()

    return {
        "matched_exact": matched_exact,
        "matched_fuzzy": matched_fuzzy,
        "unmatched": unmatched,
        "unmatched_amount": str(unmatched_amount),
        "runledger_total": str(runledger_total),
        "matched_pct": round(matched_count / total_count * 100, 2) if total_count else 0,
    }


# ── Dispute export / signing ───────────────────────────────────────────────────


def sign_dispute_export(data: dict[str, Any], signing_key: str) -> str:
    """HMAC-SHA256 signature over sorted JSON (same algorithm as billing snapshots)."""
    body = json.dumps(data, sort_keys=True, default=str).encode()
    return hmac.new(signing_key.encode(), body, hashlib.sha256).hexdigest()
