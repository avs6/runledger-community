"""
Pricing sync service — YAML-based sync plus embedded catalog sync.

Loads ``config/pricing.yml`` (path from ``settings.pricing_file``) and
upserts global provider_pricing rows in the database.

Sync rules (YAML)
-----------------
* New model   → INSERT with effective_from = now()
* Price changed → close old row (effective_to = now()), INSERT new row
  (historical cost data is preserved via effective-dating)
* Price unchanged → no-op (fully idempotent)

Sync rules (catalog)
--------------------
* Only inserts global rows (workspace_id=NULL) with source='catalog'.
* Never modifies existing rows — preserves manual overrides.

Workspace-specific override rows (workspace_id IS NOT NULL) are never
touched — they always take precedence over global rows.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
import yaml
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.metering import (
    _SYNC_CONFIG_SINGLETON_ID,
    PricingSyncConfig,
    ProviderPricing,
)

log = logging.getLogger(__name__)
catalog_log = structlog.get_logger()

# ── Embedded pricing catalog ───────────────────────────────────────────────────
# Format: (provider, model, input_per_1m, output_per_1m, cached_input_per_1m | None)
# Rates are in USD per 1M tokens. Keep sorted by provider then model.
# Last reviewed: 2026-01-01. Update when providers publish new pricing.
PRICING_CATALOG: list[tuple[str, str, str, str, str | None]] = [
    # ── Anthropic ────────────────────────────────────────────────────────────
    ("anthropic", "claude-3-5-haiku-20241022", "0.80", "4.00", "0.08"),
    ("anthropic", "claude-3-5-haiku-latest", "0.80", "4.00", "0.08"),
    ("anthropic", "claude-3-5-sonnet-20241022", "3.00", "15.00", "0.30"),
    ("anthropic", "claude-3-5-sonnet-latest", "3.00", "15.00", "0.30"),
    ("anthropic", "claude-3-haiku-20240307", "0.25", "1.25", "0.03"),
    ("anthropic", "claude-3-opus-20240229", "15.00", "75.00", "1.50"),
    ("anthropic", "claude-3-opus-latest", "15.00", "75.00", "1.50"),
    ("anthropic", "claude-3-sonnet-20240229", "3.00", "15.00", "0.30"),
    ("anthropic", "claude-opus-4", "15.00", "75.00", "1.50"),
    ("anthropic", "claude-sonnet-4", "3.00", "15.00", "0.30"),
    ("anthropic", "claude-haiku-4", "0.80", "4.00", "0.08"),
    # ── Google ────────────────────────────────────────────────────────────────
    ("google", "gemini-1.5-flash", "0.075", "0.30", "0.01875"),
    ("google", "gemini-1.5-flash-8b", "0.0375", "0.15", "0.01"),
    ("google", "gemini-1.5-pro", "1.25", "5.00", "0.3125"),
    ("google", "gemini-2.0-flash", "0.10", "0.40", "0.025"),
    ("google", "gemini-2.0-flash-lite", "0.075", "0.30", "0.01875"),
    ("google", "gemini-2.5-pro", "1.25", "10.00", None),
    # ── Mistral ───────────────────────────────────────────────────────────────
    ("mistral", "codestral-2501", "0.30", "0.90", None),
    ("mistral", "ministral-3b-2410", "0.04", "0.04", None),
    ("mistral", "ministral-8b-2410", "0.10", "0.10", None),
    ("mistral", "mistral-large-2411", "2.00", "6.00", None),
    ("mistral", "mistral-medium-2312", "2.75", "8.10", None),
    ("mistral", "mistral-small-2409", "0.20", "0.60", None),
    ("mistral", "pixtral-12b-2409", "0.15", "0.15", None),
    ("mistral", "pixtral-large-2411", "2.00", "6.00", None),
    # ── OpenAI ────────────────────────────────────────────────────────────────
    ("openai", "gpt-3.5-turbo", "0.50", "1.50", None),
    ("openai", "gpt-4", "30.00", "60.00", None),
    ("openai", "gpt-4-turbo", "10.00", "30.00", None),
    ("openai", "gpt-4o", "2.50", "10.00", "1.25"),
    ("openai", "gpt-4o-audio-preview", "2.50", "10.00", None),
    ("openai", "gpt-4o-mini", "0.15", "0.60", "0.075"),
    ("openai", "gpt-4o-mini-audio-preview", "0.15", "0.60", None),
    ("openai", "o1", "15.00", "60.00", "7.50"),
    ("openai", "o1-mini", "3.00", "12.00", "1.50"),
    ("openai", "o1-preview", "15.00", "60.00", None),
    ("openai", "o3", "10.00", "40.00", "2.50"),
    ("openai", "o3-mini", "1.10", "4.40", "0.55"),
    ("openai", "o4-mini", "1.10", "4.40", "0.275"),
]

# Pinned effective_from for catalog rows — bump this date when you update rates above
CATALOG_EFFECTIVE_FROM = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


async def get_sync_config(db: AsyncSession) -> PricingSyncConfig | None:
    """Load the singleton sync config row. Returns None if table not yet migrated."""
    try:
        return await db.get(PricingSyncConfig, _SYNC_CONFIG_SINGLETON_ID)
    except Exception:
        return None


async def sync_catalog_to_db(
    db: AsyncSession,
    *,
    dry_run: bool = False,
    force: bool = False,
    providers: list[str] | None = None,
    models: list[str] | None = None,
) -> dict[str, int | bool | list[str]]:
    """
    Sync the embedded PRICING_CATALOG to provider_pricing.

    Options (all keyword-only):
      dry_run  — compute what would happen, but write nothing (default False)
      force    — update existing catalog rows with current rates (default False)
      providers — if set, only sync these provider names (e.g. ["openai"])
      models    — if set, only sync these exact model strings

    Config overrides (from pricing_sync_config table):
      excluded_providers — always skipped regardless of `providers` arg
      excluded_models    — always skipped regardless of `models` arg
      force_update       — treated as default for `force` when not explicitly True

    Returns dict with keys:
      inserted, updated, skipped, excluded, dry_run, providers_synced
    """
    config = await get_sync_config(db)
    excluded_providers: set[str] = set(config.excluded_providers or []) if config else set()
    excluded_models: set[str] = set(config.excluded_models or []) if config else set()
    # Config force_update is the persistent default; call-time `force` overrides it
    effective_force = force or (config.force_update if config else False)

    # Provider/model filter (call-time)
    provider_filter: set[str] | None = {p.lower() for p in providers} if providers else None
    model_filter: set[str] | None = set(models) if models else None

    # Load existing global catalog rows to detect what already exists
    existing_result = await db.execute(
        select(ProviderPricing).where(
            ProviderPricing.workspace_id.is_(None),
            ProviderPricing.source == "catalog",
        )
    )
    existing: dict[tuple[str, str], ProviderPricing] = {
        (r.provider, r.model): r for r in existing_result.scalars()
    }

    inserted = updated = skipped = excluded = 0
    providers_touched: list[str] = []

    for provider, model, inp, out, cached in PRICING_CATALOG:
        # Apply exclusions
        if provider in excluded_providers or model in excluded_models:
            excluded += 1
            continue
        # Apply call-time filters
        if provider_filter and provider not in provider_filter:
            skipped += 1
            continue
        if model_filter and model not in model_filter:
            skipped += 1
            continue

        key = (provider, model)
        new_input = Decimal(inp)
        new_output = Decimal(out)
        new_cached = Decimal(cached) if cached else None
        existing_row = existing.get(key)

        if existing_row is None:
            if not dry_run:
                db.add(
                    ProviderPricing(
                        id=uuid.uuid4(),
                        provider=provider,
                        model=model,
                        input_cost_per_1m=new_input,
                        output_cost_per_1m=new_output,
                        cached_input_cost_per_1m=new_cached,
                        effective_from=CATALOG_EFFECTIVE_FROM,
                        workspace_id=None,
                        source="catalog",
                    )
                )
            inserted += 1
            if provider not in providers_touched:
                providers_touched.append(provider)
        elif effective_force and (
            existing_row.input_cost_per_1m != new_input
            or existing_row.output_cost_per_1m != new_output
            or existing_row.cached_input_cost_per_1m != new_cached
        ):
            if not dry_run:
                existing_row.input_cost_per_1m = new_input
                existing_row.output_cost_per_1m = new_output
                existing_row.cached_input_cost_per_1m = new_cached
                existing_row.effective_from = CATALOG_EFFECTIVE_FROM
            updated += 1
            if provider not in providers_touched:
                providers_touched.append(provider)
        else:
            skipped += 1

    result: dict[str, int | bool | list[str]] = {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "excluded": excluded,
        "dry_run": dry_run,
        "providers_synced": sorted(providers_touched),
    }

    if not dry_run and (inserted or updated):
        await db.commit()
        # Update last_sync_at on config row
        if config:
            config.last_sync_at = datetime.now(UTC)
            config.last_sync_result = {
                k: v for k, v in result.items() if isinstance(v, (int, bool))
            }
            await db.commit()

    catalog_log.info(
        "pricing_catalog_synced", **{k: v for k, v in result.items() if not isinstance(v, list)}
    )
    return result


async def get_pricing_timeline(
    db: AsyncSession,
    provider: str,
    model: str,
    workspace_id: uuid.UUID | None = None,
) -> list[ProviderPricing]:
    """
    Return all historical pricing rows for a (provider, model) pair,
    ordered newest-first.

    Includes global rows + workspace-specific overrides if workspace_id given.
    """
    filters = [
        ProviderPricing.provider == provider,
        ProviderPricing.model == model,
        or_(
            ProviderPricing.workspace_id.is_(None),
            ProviderPricing.workspace_id == workspace_id
            if workspace_id
            else ProviderPricing.workspace_id.is_(None),
        ),
    ]
    result = await db.execute(
        select(ProviderPricing).where(*filters).order_by(ProviderPricing.effective_from.desc())
    )
    return list(result.scalars().all())


async def add_price_correction(
    db: AsyncSession,
    pricing_id: uuid.UUID,
    new_input_per_1m: Decimal,
    new_output_per_1m: Decimal,
    cached_input_per_1m: Decimal | None,
    effective_from: datetime,
    workspace_id: uuid.UUID,
    notes: str | None = None,
) -> ProviderPricing:
    """
    Close the given pricing row (set effective_to=effective_from) and
    insert a corrected row with the new rates.

    Used for retroactive price corrections with full audit trail.
    """
    existing = await db.get(ProviderPricing, pricing_id)
    if existing is None:
        raise ValueError(f"ProviderPricing {pricing_id} not found")

    # Close the existing row
    existing.effective_to = effective_from

    correction = ProviderPricing(
        id=uuid.uuid4(),
        provider=existing.provider,
        model=existing.model,
        input_cost_per_1m=new_input_per_1m,
        output_cost_per_1m=new_output_per_1m,
        cached_input_cost_per_1m=cached_input_per_1m,
        effective_from=effective_from,
        workspace_id=workspace_id,
        source="manual",
    )
    db.add(correction)
    await db.commit()
    await db.refresh(correction)
    catalog_log.info(
        "price_correction_added",
        original_id=str(pricing_id),
        new_id=str(correction.id),
        provider=correction.provider,
        model=correction.model,
    )
    return correction


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
