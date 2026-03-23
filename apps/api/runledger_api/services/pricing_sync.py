"""
Pricing YAML sync service.

Loads ``config/pricing.yml`` (path from ``settings.pricing_file``) and
upserts global provider_pricing rows in the database.

Sync rules
----------
* New model   → INSERT with effective_from = now()
* Price changed → close old row (effective_to = now()), INSERT new row
  (historical cost data is preserved via effective-dating)
* Price unchanged → no-op (fully idempotent)

Workspace-specific override rows (workspace_id IS NOT NULL) are never
touched — they always take precedence over global rows.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import yaml
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.metering import ProviderPricing

log = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class PricingEntry:
    provider: str
    model: str
    input_per_1m: Decimal
    output_per_1m: Decimal
    cached_input_per_1m: Decimal | None = field(default=None)


# ── File loader ───────────────────────────────────────────────────────────────


def load_pricing_yaml(path: str) -> list[PricingEntry]:
    """Parse ``path`` and return a list of :class:`PricingEntry` objects.

    Returns an empty list (and logs a warning) if the file does not exist —
    this is non-fatal so the API starts even without the file mounted.
    """
    if not os.path.exists(path):
        log.warning("pricing_file_not_found path=%s — skipping sync", path)
        return []

    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    entries: list[PricingEntry] = []
    for row in raw.get("models", []):
        try:
            provider = str(row["provider"]).strip().lower()
            model = str(row["model"]).strip()
            input_per_1m = Decimal(str(row["input_per_1m"]))
            output_per_1m = Decimal(str(row["output_per_1m"]))
            cached_raw = row.get("cached_input_per_1m")
            cached = Decimal(str(cached_raw)) if cached_raw is not None else None
            entries.append(
                PricingEntry(
                    provider=provider,
                    model=model,
                    input_per_1m=input_per_1m,
                    output_per_1m=output_per_1m,
                    cached_input_per_1m=cached,
                )
            )
        except (KeyError, ValueError) as exc:
            log.warning("pricing_entry_skipped row=%r error=%s", row, exc)

    log.info("pricing_file_loaded path=%s entries=%d", path, len(entries))
    return entries


# ── Database sync ─────────────────────────────────────────────────────────────


async def sync_pricing(
    session: AsyncSession,
    entries: list[PricingEntry],
) -> dict[str, int]:
    """Upsert global pricing rows from *entries*.

    Returns ``{"inserted": N, "updated": N, "unchanged": N}``.
    """
    now = datetime.now(UTC)
    inserted = updated = unchanged = 0

    for entry in entries:
        # Find the current active global row for this provider+model
        stmt = (
            select(ProviderPricing)
            .where(
                and_(
                    ProviderPricing.provider == entry.provider,
                    ProviderPricing.model == entry.model,
                    ProviderPricing.workspace_id.is_(None),
                    ProviderPricing.effective_from <= now,
                    or_(
                        ProviderPricing.effective_to.is_(None),
                        ProviderPricing.effective_to > now,
                    ),
                )
            )
            .order_by(ProviderPricing.effective_from.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            # No active row → insert
            session.add(
                ProviderPricing(
                    provider=entry.provider,
                    model=entry.model,
                    input_cost_per_1m=entry.input_per_1m,
                    output_cost_per_1m=entry.output_per_1m,
                    cached_input_cost_per_1m=entry.cached_input_per_1m,
                    effective_from=now,
                    workspace_id=None,
                )
            )
            inserted += 1
            log.debug("pricing_inserted provider=%s model=%s", entry.provider, entry.model)

        elif (
            existing.input_cost_per_1m != entry.input_per_1m
            or existing.output_cost_per_1m != entry.output_per_1m
            or existing.cached_input_cost_per_1m != entry.cached_input_per_1m
        ):
            # Price changed → close old row, insert new one
            await session.execute(
                update(ProviderPricing)
                .where(ProviderPricing.id == existing.id)
                .values(effective_to=now)
            )
            session.add(
                ProviderPricing(
                    provider=entry.provider,
                    model=entry.model,
                    input_cost_per_1m=entry.input_per_1m,
                    output_cost_per_1m=entry.output_per_1m,
                    cached_input_cost_per_1m=entry.cached_input_per_1m,
                    effective_from=now,
                    workspace_id=None,
                )
            )
            updated += 1
            log.info(
                "pricing_updated provider=%s model=%s old_input=%s new_input=%s",
                entry.provider,
                entry.model,
                existing.input_cost_per_1m,
                entry.input_per_1m,
            )

        else:
            unchanged += 1

    await session.commit()
    log.info(
        "pricing_sync_done inserted=%d updated=%d unchanged=%d",
        inserted,
        updated,
        unchanged,
    )
    return {"inserted": inserted, "updated": updated, "unchanged": unchanged}
