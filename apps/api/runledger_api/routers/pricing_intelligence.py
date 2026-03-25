"""
Pricing Intelligence API.

Prefix: /pricing
Auth: Bearer API key

Endpoints
---------
# Pricing timeline + corrections
GET    /pricing/timeline                         Price history for provider+model
POST   /pricing/sync                             Trigger catalog sync
POST   /pricing/{pricing_id}/correct             Add retroactive price correction

# Contracts (per-workspace negotiated rates)
POST   /pricing/contracts                        Create contract
GET    /pricing/contracts                        List contracts
GET    /pricing/contracts/{id}                   Get contract
PUT    /pricing/contracts/{id}                   Update contract
DELETE /pricing/contracts/{id}                   Deactivate contract

# Credits and commitments
POST   /pricing/credits                          Add credit/prepaid bundle
GET    /pricing/credits                          List credits
POST   /pricing/credits/apply                    Apply credits to a cost amount
GET    /pricing/credits/{id}                     Get credit
PUT    /pricing/credits/{id}                     Update credit
DELETE /pricing/credits/{id}                     Deactivate credit
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_workspace,
    require_org_admin,
    require_workspace_admin,
)
from runledger_api.core.feature_gate import require_feature
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.metering import (
    PricingContract,
    PricingCredit,
)
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.pricing_intelligence import (
    CreditApplicationResult,
    PricingContractCreate,
    PricingContractList,
    PricingContractResponse,
    PricingContractUpdate,
    PricingCreditCreate,
    PricingCreditList,
    PricingCreditResponse,
    PricingCreditUpdate,
    PricingSyncConfigResponse,
    PricingSyncConfigUpdate,
    SyncTriggerRequest,
)
from runledger_api.schemas.providers import ProviderPricingList, ProviderPricingResponse
from runledger_api.services.pricing_sync import (
    add_price_correction,
    get_pricing_timeline,
    get_sync_config,
    sync_catalog_to_db,
)

router = APIRouter(prefix="/pricing", tags=["pricing-intelligence"])
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Pricing timeline ───────────────────────────────────────────────────────────


@router.get(
    "/timeline",
    response_model=ProviderPricingList,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_price_timeline(
    workspace: WorkspaceDep,
    db: DbDep,
    provider: Annotated[str, Query()],
    model: Annotated[str, Query()],
) -> ProviderPricingList:
    """Return full price history for a provider+model, newest-first."""
    rows = await get_pricing_timeline(db, provider, model, workspace_id=workspace.id)
    return ProviderPricingList(items=[ProviderPricingResponse.model_validate(r) for r in rows])


# ── Sync config ────────────────────────────────────────────────────────────────


@router.get(
    "/sync/config",
    response_model=PricingSyncConfigResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_pricing_sync_config(
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> PricingSyncConfigResponse:
    """
    Return the current pricing sync configuration.

    Controls the catalog sync beat task:
      sync_enabled      — master on/off switch for the scheduled sync
      excluded_providers — providers the sync will always skip (e.g. ["mistral"])
      excluded_models    — exact model names the sync will always skip
      force_update       — when true, sync updates existing catalog rows with new rates
    """
    config = await get_sync_config(db)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sync config not initialised — run migration 041",
        )
    return PricingSyncConfigResponse.model_validate(config)


@router.put(
    "/sync/config",
    response_model=PricingSyncConfigResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_pricing_sync_config(
    body: PricingSyncConfigUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> PricingSyncConfigResponse:
    """
    Update pricing sync settings.

    All fields are optional — only supplied fields are changed.

    Examples:
      {"sync_enabled": false}                        → stop the beat task
      {"excluded_providers": ["mistral", "google"]}  → skip these providers
      {"excluded_models": ["gpt-4"]}                 → pin this model
      {"force_update": true}                         → allow rate updates on next sync
      {"excluded_providers": []}                     → clear all provider exclusions
    """
    workspace: Workspace = auth[0]
    config = await get_sync_config(db)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sync config not initialised — run migration 041",
        )
    if body.sync_enabled is not None:
        config.sync_enabled = body.sync_enabled
    if body.excluded_providers is not None:
        config.excluded_providers = [p.lower().strip() for p in body.excluded_providers]
    if body.excluded_models is not None:
        config.excluded_models = list(body.excluded_models)
    if body.force_update is not None:
        config.force_update = body.force_update

    config.updated_by = str(workspace.id)
    config.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(config)
    log.info(
        "pricing_sync_config_updated",
        sync_enabled=config.sync_enabled,
        excluded_providers=config.excluded_providers,
        force_update=config.force_update,
    )
    return PricingSyncConfigResponse.model_validate(config)


# ── Catalog sync ───────────────────────────────────────────────────────────────


@router.post(
    "/sync",
    response_model=dict,
    dependencies=[Depends(management_rate_limit)],
)
async def trigger_pricing_sync(
    body: SyncTriggerRequest,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> dict[str, Any]:
    """
    Manually trigger a pricing catalog sync with fine-grained control.

    Options:
      dry_run   — preview changes without writing to the DB (default false)
      force     — update existing catalog rows with the latest rates (default false)
      providers — list of provider names to sync; null = all non-excluded providers
      models    — list of exact model names to sync; null = all non-excluded models

    The sync always respects excluded_providers and excluded_models from
    GET /pricing/sync/config regardless of what you pass here.

    Example (preview what would change for OpenAI only):
      {"dry_run": true, "providers": ["openai"]}
    """
    return await sync_catalog_to_db(
        db,
        dry_run=body.dry_run,
        force=body.force,
        providers=body.providers,
        models=body.models,
    )


# ── Price corrections ──────────────────────────────────────────────────────────


class PriceCorrection(BaseModel):
    input_cost_per_1m: Decimal
    output_cost_per_1m: Decimal
    cached_input_cost_per_1m: Decimal | None = None
    effective_from: datetime
    notes: str | None = None


@router.post(
    "/{pricing_id}/correct",
    response_model=ProviderPricingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def correct_pricing(
    pricing_id: uuid.UUID,
    body: PriceCorrection,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> ProviderPricingResponse:
    """
    Add a retroactive price correction.

    Closes the existing row (sets effective_to) and inserts a new corrected row
    with the given effective_from. Creates a full audit trail in the timeline.
    """
    workspace: Workspace = auth[0]
    try:
        row = await add_price_correction(
            db,
            pricing_id=pricing_id,
            new_input_per_1m=body.input_cost_per_1m,
            new_output_per_1m=body.output_cost_per_1m,
            cached_input_per_1m=body.cached_input_cost_per_1m,
            effective_from=body.effective_from,
            workspace_id=workspace.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProviderPricingResponse.model_validate(row)


# ── Pricing contracts ──────────────────────────────────────────────────────────


@router.post(
    "/contracts",
    response_model=PricingContractResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_contract(
    body: PricingContractCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> PricingContractResponse:
    """Create a negotiated rate contract for this workspace."""
    require_feature("pricing_contracts", "Pricing contracts")
    workspace: Workspace = auth[0]
    contract = PricingContract(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider=body.provider,
        model=body.model,
        discount_pct=body.discount_pct,
        fixed_input_per_1m=body.fixed_input_per_1m,
        fixed_output_per_1m=body.fixed_output_per_1m,
        effective_from=body.effective_from,
        effective_until=body.effective_until,
        notes=body.notes,
        is_active=True,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    log.info(
        "pricing_contract_created",
        contract_id=str(contract.id),
        workspace_id=str(workspace.id),
        provider=contract.provider,
    )
    return PricingContractResponse.model_validate(contract)


@router.get(
    "/contracts",
    response_model=PricingContractList,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_contracts(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
    active_only: Annotated[bool, Query()] = False,
) -> PricingContractList:
    workspace: Workspace = auth[0]
    stmt = select(PricingContract).where(PricingContract.workspace_id == workspace.id)
    if active_only:
        stmt = stmt.where(PricingContract.is_active.is_(True))
    stmt = stmt.order_by(PricingContract.provider, PricingContract.effective_from.desc())
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return PricingContractList(
        items=[PricingContractResponse.model_validate(c) for c in items],
        total=len(items),
    )


@router.get(
    "/contracts/{contract_id}",
    response_model=PricingContractResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_contract(
    contract_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> PricingContractResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(PricingContract).where(
            PricingContract.id == contract_id,
            PricingContract.workspace_id == workspace.id,
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return PricingContractResponse.model_validate(contract)


@router.put(
    "/contracts/{contract_id}",
    response_model=PricingContractResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_contract(
    contract_id: uuid.UUID,
    body: PricingContractUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> PricingContractResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(PricingContract).where(
            PricingContract.id == contract_id,
            PricingContract.workspace_id == workspace.id,
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    if body.discount_pct is not None:
        contract.discount_pct = body.discount_pct
    if body.fixed_input_per_1m is not None:
        contract.fixed_input_per_1m = body.fixed_input_per_1m
    if body.fixed_output_per_1m is not None:
        contract.fixed_output_per_1m = body.fixed_output_per_1m
    if body.effective_until is not None:
        contract.effective_until = body.effective_until
    if body.notes is not None:
        contract.notes = body.notes
    if body.is_active is not None:
        contract.is_active = body.is_active
    await db.commit()
    await db.refresh(contract)
    return PricingContractResponse.model_validate(contract)


@router.delete(
    "/contracts/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_contract(
    contract_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(PricingContract).where(
            PricingContract.id == contract_id,
            PricingContract.workspace_id == workspace.id,
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    contract.is_active = False
    await db.commit()


# ── Pricing credits ────────────────────────────────────────────────────────────


@router.post(
    "/credits",
    response_model=PricingCreditResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_credit(
    body: PricingCreditCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> PricingCreditResponse:
    require_feature("pricing_credits", "Pricing credits")
    workspace: Workspace = auth[0]
    credit = PricingCredit(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        name=body.name,
        credit_type=body.credit_type,
        amount_usd=body.amount_usd,
        remaining_usd=body.amount_usd,
        source=body.source,
        effective_from=body.effective_from,
        effective_until=body.effective_until,
        priority=body.priority,
        is_active=True,
    )
    db.add(credit)
    await db.commit()
    await db.refresh(credit)
    log.info(
        "pricing_credit_created",
        credit_id=str(credit.id),
        workspace_id=str(workspace.id),
        credit_type=credit.credit_type,
        amount_usd=str(credit.amount_usd),
    )
    return PricingCreditResponse.model_validate(credit)


@router.get(
    "/credits",
    response_model=PricingCreditList,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_credits(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
    active_only: Annotated[bool, Query()] = False,
) -> PricingCreditList:
    workspace: Workspace = auth[0]
    stmt = select(PricingCredit).where(PricingCredit.workspace_id == workspace.id)
    if active_only:
        stmt = stmt.where(PricingCredit.is_active.is_(True))
    stmt = stmt.order_by(PricingCredit.priority, PricingCredit.effective_from)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return PricingCreditList(
        items=[PricingCreditResponse.model_validate(c) for c in items],
        total=len(items),
    )


# IMPORTANT: /credits/apply must be defined BEFORE /credits/{credit_id} to avoid
# FastAPI treating "apply" as a credit_id path parameter.
@router.post(
    "/credits/apply",
    response_model=CreditApplicationResult,
    dependencies=[Depends(management_rate_limit)],
)
async def apply_credits_endpoint(
    body: dict[str, Any],
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> CreditApplicationResult:
    """Apply available credits to a cost amount. Returns net cost after credits."""
    workspace: Workspace = auth[0]
    cost_str = body.get("cost_usd")
    if cost_str is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cost_usd is required",
        )
    try:
        cost_usd = Decimal(str(cost_str))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cost_usd must be a valid decimal",
        ) from exc

    from runledger_api.services.pricing_credits import apply_credits  # noqa: PLC0415

    result = await apply_credits(db, workspace.id, cost_usd)
    return CreditApplicationResult(**result)


@router.get(
    "/credits/{credit_id}",
    response_model=PricingCreditResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_credit(
    credit_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: DbDep,
) -> PricingCreditResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(PricingCredit).where(
            PricingCredit.id == credit_id,
            PricingCredit.workspace_id == workspace.id,
        )
    )
    credit = result.scalar_one_or_none()
    if credit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit not found")
    return PricingCreditResponse.model_validate(credit)


@router.put(
    "/credits/{credit_id}",
    response_model=PricingCreditResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_credit(
    credit_id: uuid.UUID,
    body: PricingCreditUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> PricingCreditResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(PricingCredit).where(
            PricingCredit.id == credit_id,
            PricingCredit.workspace_id == workspace.id,
        )
    )
    credit = result.scalar_one_or_none()
    if credit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit not found")
    if body.name is not None:
        credit.name = body.name
    if body.remaining_usd is not None:
        credit.remaining_usd = body.remaining_usd
    if body.effective_until is not None:
        credit.effective_until = body.effective_until
    if body.priority is not None:
        credit.priority = body.priority
    if body.is_active is not None:
        credit.is_active = body.is_active
    await db.commit()
    await db.refresh(credit)
    return PricingCreditResponse.model_validate(credit)


@router.delete(
    "/credits/{credit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_credit(
    credit_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_org_admin)],
    db: DbDep,
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(PricingCredit).where(
            PricingCredit.id == credit_id,
            PricingCredit.workspace_id == workspace.id,
        )
    )
    credit = result.scalar_one_or_none()
    if credit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit not found")
    credit.is_active = False
    await db.commit()
