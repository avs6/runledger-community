"""
Provider-pricing YAML import.

Parses a pricing YAML (the `models:` list format, same as `config/pricing.yml`) and
**idempotently upserts global provider_pricing rows** (workspace_id IS NULL). This is the
single source of truth for both the GUI "Import YAML" action and the initial seed.

Update semantics (per product decision): a changed price **updates the existing row in
place**; an unchanged row is a no-op; a new (provider, model) is inserted. Re-importing the
same file therefore changes nothing.

YAML shape
----------
    models:
      - provider: openai
        model: o3-mini
        input_per_1m: 1.10
        output_per_1m: 4.40
        cached_input_per_1m: 0.55     # optional
        tags: [reasoning, coding]     # optional
        display_name: "OpenAI o3-mini"  # optional
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.metering import ProviderPricing
from runledger_api.schemas.providers import PricingImportResult


@dataclass
class ParsedRow:
    provider: str
    model: str
    input_cost_per_1m: Decimal
    output_cost_per_1m: Decimal
    cached_input_cost_per_1m: Decimal | None
    tags: list[str] = field(default_factory=list)
    display_name: str | None = None


def _dec(v: Any) -> Decimal:
    return Decimal(str(v))


def parse_pricing_yaml(text: str) -> tuple[list[ParsedRow], list[str]]:
    """Parse a pricing YAML string → (rows, errors). Never raises on bad rows."""
    errors: list[str] = []
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return [], [f"invalid YAML: {exc}"]
    items = doc.get("models") if isinstance(doc, dict) else doc
    if not isinstance(items, list):
        return [], ["expected a top-level `models:` list"]

    rows: list[ParsedRow] = []
    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            errors.append(f"row {i}: not a mapping")
            continue
        provider = str(raw.get("provider", "")).strip()
        model = str(raw.get("model", "")).strip()
        if not provider or not model:
            errors.append(f"row {i}: missing provider or model")
            continue
        try:
            in_rate = _dec(raw["input_per_1m"])
            out_rate = _dec(raw["output_per_1m"])
        except (KeyError, InvalidOperation, TypeError):
            errors.append(f"{provider}/{model}: missing or invalid input_per_1m / output_per_1m")
            continue
        cached = None
        if raw.get("cached_input_per_1m") is not None:
            try:
                cached = _dec(raw["cached_input_per_1m"])
            except (InvalidOperation, TypeError):
                errors.append(f"{provider}/{model}: invalid cached_input_per_1m (ignored)")
        tags_raw = raw.get("tags") or []
        tags = (
            [str(t).strip() for t in tags_raw if str(t).strip()]
            if isinstance(tags_raw, list)
            else []
        )
        display_name = raw.get("display_name")
        rows.append(
            ParsedRow(
                provider,
                model,
                in_rate,
                out_rate,
                cached,
                tags,
                str(display_name) if display_name else None,
            )
        )
    return rows, errors


async def import_pricing(
    db: AsyncSession, rows: list[ParsedRow], *, parse_errors: list[str] | None = None
) -> PricingImportResult:
    """Upsert parsed rows as global pricing (update in place). Idempotent."""
    inserted = updated = unchanged = 0
    now = datetime.now(UTC)
    for r in rows:
        # Most-recent active global row for this model. Uses .first() (not
        # scalar_one_or_none) because legacy data may contain duplicate active rows
        # for the same provider/model — we update the newest and leave the rest.
        existing = (
            (
                await db.execute(
                    select(ProviderPricing)
                    .where(
                        ProviderPricing.provider == r.provider,
                        ProviderPricing.model == r.model,
                        ProviderPricing.workspace_id.is_(None),
                        ProviderPricing.effective_to.is_(None),
                    )
                    .order_by(ProviderPricing.effective_from.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )

        if existing is None:
            db.add(
                ProviderPricing(
                    provider=r.provider,
                    model=r.model,
                    input_cost_per_1m=r.input_cost_per_1m,
                    output_cost_per_1m=r.output_cost_per_1m,
                    cached_input_cost_per_1m=r.cached_input_cost_per_1m,
                    tags=r.tags,
                    display_name=r.display_name,
                    effective_from=now,
                    workspace_id=None,
                    source="yaml_import",
                )
            )
            inserted += 1
            continue

        changed = (
            existing.input_cost_per_1m != r.input_cost_per_1m
            or existing.output_cost_per_1m != r.output_cost_per_1m
            or existing.cached_input_cost_per_1m != r.cached_input_cost_per_1m
            or list(existing.tags or []) != r.tags
            or existing.display_name != r.display_name
        )
        if changed:
            existing.input_cost_per_1m = r.input_cost_per_1m
            existing.output_cost_per_1m = r.output_cost_per_1m
            existing.cached_input_cost_per_1m = r.cached_input_cost_per_1m
            existing.tags = r.tags
            existing.display_name = r.display_name
            existing.source = "yaml_import"
            updated += 1
        else:
            unchanged += 1

    await db.commit()
    return PricingImportResult(
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        total=len(rows),
        providers=sorted({r.provider for r in rows}),
        tags=sorted({t for r in rows for t in r.tags}),
        errors=list(parse_errors or []),
    )


async def import_pricing_yaml(db: AsyncSession, text: str) -> PricingImportResult:
    """Convenience: parse then import."""
    rows, errors = parse_pricing_yaml(text)
    return await import_pricing(db, rows, parse_errors=errors)
