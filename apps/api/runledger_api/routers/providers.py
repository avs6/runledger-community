"""
Providers router — workspace-scoped provider pricing CRUD.

Prefix: /providers
Auth: Bearer API key via get_current_workspace

Business rules:
- GET: returns global rows (workspace_id IS NULL) + current workspace rows
- POST: always creates workspace-scoped rows
- PUT/DELETE: only allowed on workspace-owned rows (403 on global or foreign)
- POST /pricing/sync: platform admins re-load the deployment's pricing catalog
  (``settings.pricing_file``) into the global rows; ``dry_run`` only validates it
- Every write is audited (review G-10); roles follow core/role_matrix.py ("pricing")
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_org_admin, require_platform_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.budgets import Budget
from runledger_api.models.events import ProviderCall
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.tenant import TenantUser, User, Workspace
from runledger_api.schemas.providers import (
    PricingImportResult,
    ProviderPricingCreate,
    ProviderPricingList,
    ProviderPricingResponse,
    ProviderPricingUpdate,
    UnpricedModel,
    UnpricedUsage,
)
from runledger_api.services.admin_audit import audit_change, snapshot
from runledger_api.services.pricing_import import import_pricing_yaml, parse_pricing_yaml

log = structlog.get_logger()

router = APIRouter(
    prefix="/providers", tags=["providers"], dependencies=[Depends(management_rate_limit)]
)

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
OrgAdminDep = Annotated[tuple[Workspace, User, TenantUser | None], Depends(require_org_admin)]
# The global pricing catalog prices every tenant's spend: platform admins only.
PlatformAdminDep = Annotated[tuple[Workspace, User], Depends(require_platform_admin)]
_PRICE_FIELDS = (
    "provider",
    "model",
    "input_cost_per_1m",
    "output_cost_per_1m",
    "cached_input_cost_per_1m",
    "tags",
    "display_name",
    "effective_from",
    "effective_to",
)


async def _retry_unpriced_calls(
    db: AsyncSession, workspace_id: uuid.UUID | None, model: str | None
) -> None:
    """Clear the enrichment "could not price" flag so new pricing applies right away.

    ``workspace_id``/``model`` None widens the reset (global catalog import).
    """
    from sqlalchemy import update  # noqa: PLC0415

    from runledger_api.models.events import ProviderCall  # noqa: PLC0415

    stmt = update(ProviderCall).where(
        ProviderCall.cost_usd.is_(None), ProviderCall.cost_checked_at.is_not(None)
    )
    if workspace_id is not None:
        stmt = stmt.where(ProviderCall.workspace_id == workspace_id)
    if model is not None:
        stmt = stmt.where(ProviderCall.model == model)
    await db.execute(stmt.values(cost_checked_at=None))


@router.get("/pricing/unpriced", response_model=UnpricedUsage)
async def list_unpriced_usage(
    auth: OrgAdminDep,
    db: DbDep,
    days: int = Query(30, ge=1, le=365),
) -> UnpricedUsage:
    """Model calls enrichment could not price, grouped by provider and model.

    These calls carry tokens but no cost, so spend, budgets and chargeback undercount
    them. Adding pricing for the model (workspace or global) prices them on the next
    enrichment sweep.
    """
    workspace = auth[0]
    since = datetime.now(UTC) - timedelta(days=days)
    unpriced = (
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.created_at >= since,
        ProviderCall.cost_usd.is_(None),
        ProviderCall.cost_checked_at.is_not(None),
    )
    rows = (
        await db.execute(
            select(
                ProviderCall.provider,
                ProviderCall.model,
                func.count().label("calls"),
                func.coalesce(func.sum(ProviderCall.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(ProviderCall.output_tokens), 0).label("output_tokens"),
                func.min(ProviderCall.created_at).label("first_seen"),
                func.max(ProviderCall.created_at).label("last_seen"),
            )
            .where(*unpriced)
            .group_by(ProviderCall.provider, ProviderCall.model)
            .order_by(func.count().desc())
            .limit(200)
        )
    ).all()
    total_calls = (
        await db.execute(
            select(func.count()).where(
                ProviderCall.workspace_id == workspace.id, ProviderCall.created_at >= since
            )
        )
    ).scalar_one()
    items = [
        UnpricedModel(
            provider=r.provider,
            model=r.model,
            calls=int(r.calls),
            input_tokens=int(r.input_tokens),
            output_tokens=int(r.output_tokens),
            first_seen=r.first_seen,
            last_seen=r.last_seen,
        )
        for r in rows
    ]
    unpriced_calls = sum(i.calls for i in items)
    return UnpricedUsage(
        days=days,
        unpriced_calls=unpriced_calls,
        unpriced_tokens=sum(i.input_tokens + i.output_tokens for i in items),
        total_calls=int(total_calls),
        unpriced_pct=round(unpriced_calls / total_calls * 100, 1) if total_calls else 0.0,
        items=items,
    )


@router.get("/pricing", response_model=ProviderPricingList)
async def list_pricing(auth: OrgAdminDep, db: DbDep) -> ProviderPricingList:
    workspace = auth[0]
    result = await db.execute(
        select(ProviderPricing)
        .where(
            or_(
                ProviderPricing.workspace_id.is_(None),
                ProviderPricing.workspace_id == workspace.id,
            ),
            # Only currently-active pricing — exclude superseded/historical rows so the
            # model dropdown and pricing UI don't show stale duplicates.
            ProviderPricing.effective_to.is_(None),
        )
        .order_by(
            ProviderPricing.provider,
            ProviderPricing.model,
            ProviderPricing.effective_from.desc(),
        )
    )
    rows = list(result.scalars().all())
    budget_counts: dict[str, dict[str, int]] = {}
    pricing_ids = [str(row.id) for row in rows]
    if pricing_ids:
        budget_result = await db.execute(
            select(
                Budget.scope_id,
                func.count(Budget.id),
                func.sum(case((Budget.is_active.is_(True), 1), else_=0)),
            )
            .where(
                Budget.workspace_id == workspace.id,
                Budget.scope_type == "provider_profile",
                Budget.scope_id.in_(pricing_ids),
            )
            .group_by(Budget.scope_id)
        )
        budget_counts = {
            scope_id: {
                "budget_count": int(total_count or 0),
                "active_budget_count": int(active_count or 0),
            }
            for scope_id, total_count, active_count in budget_result.all()
            if scope_id is not None
        }

    items = []
    for row in rows:
        counts = budget_counts.get(str(row.id), {})
        base = ProviderPricingResponse.model_validate(row).model_dump(
            exclude={"budget_count", "active_budget_count"}
        )
        items.append(
            ProviderPricingResponse(
                **base,
                budget_count=counts.get("budget_count", 0),
                active_budget_count=counts.get("active_budget_count", 0),
            )
        )
    return ProviderPricingList(items=items)


@router.post("/pricing/import", response_model=PricingImportResult)
async def import_pricing(
    auth: PlatformAdminDep,
    db: DbDep,
    file: Annotated[UploadFile, File(description="A pricing YAML file")],
) -> PricingImportResult:
    """
    Import a pricing YAML (platform admins only) — idempotently upserts the **global** pricing catalog
    (update-in-place; re-importing the same file is a no-op). This is the DB-backed
    source of truth; the file is only the transport.
    """
    workspace = auth[0]
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "file must be UTF-8 text") from None
    result = await import_pricing_yaml(db, text)
    await _retry_unpriced_calls(db, None, None)
    await audit_change(
        db,
        workspace.id,
        "pricing.imported",
        auth=auth,
        target_type="pricing_catalog",
        target_id="global",
        after=result.model_dump(include={"inserted", "updated", "unchanged", "total"}),
    )
    await db.commit()
    log.info(
        "provider_pricing_imported",
        workspace_id=str(workspace.id),
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
    )
    return result


class PricingSyncRequest(BaseModel):
    dry_run: bool = False


def _catalog_path() -> Path | None:
    from runledger_api.core.config import settings  # noqa: PLC0415

    candidates = [Path(settings.pricing_file), Path("/app/config/pricing.yml")]
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "config" / "pricing.yml")
    return next((c for c in candidates if c.exists()), None)


@router.post("/pricing/sync", response_model=PricingImportResult)
async def sync_pricing(
    auth: PlatformAdminDep, db: DbDep, body: PricingSyncRequest | None = None
) -> PricingImportResult:
    """Re-load the deployment's pricing catalog file into the global rows (review G-08).

    The catalog ships with the deployment (``PRICING_FILE``); updating that file and
    syncing is how operators refresh prices. Nothing is fetched from the internet.
    ``dry_run`` parses and validates the file without writing.
    """
    workspace = auth[0]
    path = _catalog_path()
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "pricing catalog file not found")
    text = path.read_text(encoding="utf-8")
    if body is not None and body.dry_run:
        rows, errors = parse_pricing_yaml(text)
        return PricingImportResult(
            inserted=0,
            updated=0,
            unchanged=0,
            total=len(rows),
            providers=sorted({r.provider for r in rows}),
            tags=sorted({t for r in rows for t in r.tags}),
            errors=errors,
        )
    result = await import_pricing_yaml(db, text)
    await _retry_unpriced_calls(db, None, None)
    await audit_change(
        db,
        workspace.id,
        "pricing.synced",
        auth=auth,
        target_type="pricing_catalog",
        target_id="global",
        after={
            **result.model_dump(include={"inserted", "updated", "unchanged", "total"}),
            "file": path.name,
        },
    )
    await db.commit()
    log.info("provider_pricing_synced", inserted=result.inserted, updated=result.updated)
    return result


@router.get("/pricing/example", response_class=PlainTextResponse)
async def pricing_example(auth: OrgAdminDep) -> str:
    """Return the example pricing YAML so the GUI can offer a downloadable template."""
    from runledger_api.core.config import settings  # noqa: PLC0415

    candidates = [
        Path(settings.pricing_file).parent / "pricing.example.yml",  # alongside the live file
        Path("/app/config/pricing.example.yml"),
    ]
    # Repo-relative (local dev): walk up until a config/ dir is found.
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "config" / "pricing.example.yml")
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise HTTPException(status.HTTP_404_NOT_FOUND, "example pricing file not found")


@router.post(
    "/pricing",
    status_code=status.HTTP_201_CREATED,
    response_model=ProviderPricingResponse,
)
async def create_pricing(
    body: ProviderPricingCreate, auth: OrgAdminDep, db: DbDep
) -> ProviderPricingResponse:
    workspace = auth[0]
    pricing = ProviderPricing(
        provider=body.provider,
        model=body.model,
        input_cost_per_1m=body.input_cost_per_1m,
        output_cost_per_1m=body.output_cost_per_1m,
        cached_input_cost_per_1m=body.cached_input_cost_per_1m,
        cache_write_cost_per_1m=body.cache_write_cost_per_1m,
        tags=body.tags,
        display_name=body.display_name,
        effective_from=body.effective_from or datetime.now(UTC),
        workspace_id=workspace.id,
    )
    db.add(pricing)
    await db.flush()
    await _retry_unpriced_calls(db, workspace.id, body.model)
    await audit_change(
        db,
        workspace.id,
        "pricing.created",
        auth=auth,
        target_type="provider_pricing",
        target_id=pricing.id,
        after=snapshot(pricing, _PRICE_FIELDS),
    )
    await db.commit()
    await db.refresh(pricing)
    log.info("provider_pricing_created", pricing_id=str(pricing.id), workspace_id=str(workspace.id))
    return ProviderPricingResponse.model_validate(pricing)


@router.put("/pricing/{pricing_id}", response_model=ProviderPricingResponse)
async def update_pricing(
    pricing_id: uuid.UUID,
    body: ProviderPricingUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> ProviderPricingResponse:
    workspace = auth[0]
    pricing = await db.get(ProviderPricing, pricing_id)
    if pricing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pricing not found")
    if pricing.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot modify global or foreign pricing")
    if pricing.effective_to is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This price version is retired")
    before = snapshot(pricing, _PRICE_FIELDS)
    original_id = pricing.id
    now = datetime.now(UTC)
    price_changed = any(
        value is not None and value != current
        for value, current in (
            (body.input_cost_per_1m, pricing.input_cost_per_1m),
            (body.output_cost_per_1m, pricing.output_cost_per_1m),
            (body.cached_input_cost_per_1m, pricing.cached_input_cost_per_1m),
            (body.cache_write_cost_per_1m, pricing.cache_write_cost_per_1m),
        )
    )
    if price_changed and pricing.effective_from <= now:
        # Version the price (review G-21): calls made before now keep the rate they were
        # made at, the new rate applies from now, and budgets follow the new version.
        pricing.effective_to = now
        successor = ProviderPricing(
            provider=pricing.provider,
            model=pricing.model,
            input_cost_per_1m=pricing.input_cost_per_1m,
            output_cost_per_1m=pricing.output_cost_per_1m,
            cached_input_cost_per_1m=pricing.cached_input_cost_per_1m,
            cache_write_cost_per_1m=pricing.cache_write_cost_per_1m,
            tags=pricing.tags,
            display_name=pricing.display_name,
            effective_from=now,
            workspace_id=pricing.workspace_id,
            source=pricing.source,
        )
        db.add(successor)
        await db.flush()
        await db.execute(
            update(Budget)
            .where(
                Budget.workspace_id == workspace.id,
                Budget.scope_type == "provider_profile",
                Budget.scope_id == str(pricing.id),
            )
            .values(scope_id=str(successor.id))
        )
        pricing = successor
    if body.input_cost_per_1m is not None:
        pricing.input_cost_per_1m = body.input_cost_per_1m
    if body.output_cost_per_1m is not None:
        pricing.output_cost_per_1m = body.output_cost_per_1m
    if body.cached_input_cost_per_1m is not None:
        pricing.cached_input_cost_per_1m = body.cached_input_cost_per_1m
    if body.cache_write_cost_per_1m is not None:
        pricing.cache_write_cost_per_1m = body.cache_write_cost_per_1m
    if body.tags is not None:
        pricing.tags = body.tags
    if body.display_name is not None:
        pricing.display_name = body.display_name
    await _retry_unpriced_calls(db, workspace.id, pricing.model)
    await audit_change(
        db,
        workspace.id,
        "pricing.updated",
        auth=auth,
        target_type="provider_pricing",
        target_id=original_id,
        before=before,
        after={**snapshot(pricing, _PRICE_FIELDS), "version_id": str(pricing.id)},
    )
    await db.commit()
    await db.refresh(pricing)
    return ProviderPricingResponse.model_validate(pricing)


@router.delete("/pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pricing(pricing_id: uuid.UUID, auth: OrgAdminDep, db: DbDep) -> None:
    workspace = auth[0]
    pricing = await db.get(ProviderPricing, pricing_id)
    if pricing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pricing not found")
    if pricing.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot delete global or foreign pricing")
    in_use = (
        await db.execute(
            select(func.count(Budget.id)).where(
                Budget.workspace_id == workspace.id,
                Budget.scope_type == "provider_profile",
                Budget.scope_id == str(pricing.id),
            )
        )
    ).scalar_one()
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{in_use} budget(s) use this price; move or delete them first",
        )
    # Retire rather than delete (review G-21): calls made while it applied keep their
    # cost on re-pricing, and the price history stays auditable.
    pricing.effective_to = datetime.now(UTC)
    await audit_change(
        db,
        workspace.id,
        "pricing.retired",
        auth=auth,
        target_type="provider_pricing",
        target_id=pricing.id,
        after=snapshot(pricing, _PRICE_FIELDS),
    )
    await db.commit()
    log.info("provider_pricing_retired", pricing_id=str(pricing_id))


class RepriceRequest(BaseModel):
    provider: str
    model: str | None = None


@router.post("/reprice", response_model=dict[str, int])
async def reprice_provider(body: RepriceRequest, auth: OrgAdminDep, db: DbDep) -> dict[str, int]:
    """Reset cost_usd to NULL for provider_calls so the enrichment worker re-prices them.

    Useful after updating pricing rates — provider_calls that already have cost_usd = 0.00
    will not be re-enriched automatically (the worker only picks up cost_usd IS NULL).
    This endpoint nullifies their cost so they get repriced on the next enrichment cycle.
    """
    workspace = auth[0]
    filters = [
        ProviderCall.workspace_id == workspace.id,
        ProviderCall.provider == body.provider,
    ]
    if body.model:
        filters.append(ProviderCall.model == body.model)

    result = await db.execute(
        update(ProviderCall).where(*filters).values(cost_usd=None).returning(ProviderCall.id)
    )
    reset = len(result.fetchall())
    await audit_change(
        db,
        workspace.id,
        "pricing.repriced",
        auth=auth,
        target_type="provider_pricing",
        target_id=f"{body.provider}/{body.model or '*'}",
        after={"reset_calls": reset},
    )
    await db.commit()

    if reset:
        from runledger_api.workers.metering import cost_enrichment_worker  # noqa: PLC0415

        cost_enrichment_worker.delay()
        log.info("reprice_triggered", provider=body.provider, model=body.model, reset=reset)

    return {"reset": reset}
