"""
Providers router — workspace-scoped provider pricing CRUD.

Prefix: /providers
Auth: Bearer API key via get_current_workspace

Business rules:
- GET: returns global rows (workspace_id IS NULL) + current workspace rows
- POST: always creates workspace-scoped rows
- PUT/DELETE: only allowed on workspace-owned rows (403 on global or foreign)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_org_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.events import ProviderCall
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.tenant import TenantUser, User, Workspace
from runledger_api.schemas.providers import (
    PricingImportResult,
    ProviderPricingCreate,
    ProviderPricingList,
    ProviderPricingResponse,
    ProviderPricingUpdate,
)
from runledger_api.services.pricing_import import import_pricing_yaml

log = structlog.get_logger()

router = APIRouter(
    prefix="/providers", tags=["providers"], dependencies=[Depends(management_rate_limit)]
)

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
OrgAdminDep = Annotated[tuple[Workspace, User, TenantUser | None], Depends(require_org_admin)]


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
    return ProviderPricingList(items=[ProviderPricingResponse.model_validate(r) for r in rows])


@router.post("/pricing/import", response_model=PricingImportResult)
async def import_pricing(
    auth: OrgAdminDep,
    db: DbDep,
    file: Annotated[UploadFile, File(description="A pricing YAML file")],
) -> PricingImportResult:
    """
    Import a pricing YAML — idempotently upserts the **global** pricing catalog
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
    log.info(
        "provider_pricing_imported",
        workspace_id=str(workspace.id),
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
    )
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
        tags=body.tags,
        display_name=body.display_name,
        effective_from=body.effective_from or datetime.now(UTC),
        workspace_id=workspace.id,
    )
    db.add(pricing)
    await db.flush()
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
    if body.input_cost_per_1m is not None:
        pricing.input_cost_per_1m = body.input_cost_per_1m
    if body.output_cost_per_1m is not None:
        pricing.output_cost_per_1m = body.output_cost_per_1m
    if body.cached_input_cost_per_1m is not None:
        pricing.cached_input_cost_per_1m = body.cached_input_cost_per_1m
    if body.tags is not None:
        pricing.tags = body.tags
    if body.display_name is not None:
        pricing.display_name = body.display_name
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
    await db.delete(pricing)
    await db.commit()
    log.info("provider_pricing_deleted", pricing_id=str(pricing_id))


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
    await db.commit()

    if reset:
        from runledger_api.workers.metering import cost_enrichment_worker  # noqa: PLC0415

        cost_enrichment_worker.delay()
        log.info("reprice_triggered", provider=body.provider, model=body.model, reset=reset)

    return {"reset": reset}
