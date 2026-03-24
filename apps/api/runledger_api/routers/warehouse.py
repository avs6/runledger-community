"""
Warehouse Export API — Phase 28.

Prefix: /warehouse
Auth: Bearer API key (workspace-admin only)

Endpoints
---------
POST   /warehouse/destinations              Create a destination
GET    /warehouse/destinations              List destinations
GET    /warehouse/destinations/{id}         Get a destination
PUT    /warehouse/destinations/{id}         Update a destination
DELETE /warehouse/destinations/{id}         Delete a destination
POST   /warehouse/destinations/{id}/test    Test S3 connection
GET    /warehouse/jobs                      List export jobs
POST   /warehouse/jobs                      Trigger a manual export job
GET    /warehouse/jobs/{id}                 Get a job
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_workspace_admin
from runledger_api.core.feature_gate import require_enterprise
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.tenant import Workspace
from runledger_api.models.warehouse import ExportJob, WarehouseDestination
from runledger_api.schemas.warehouse import (
    ConnectionTestResult,
    ExportJobList,
    ExportJobResponse,
    ExportJobTrigger,
    WarehouseDestinationCreate,
    WarehouseDestinationList,
    WarehouseDestinationResponse,
    WarehouseDestinationUpdate,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.crypto import encrypt_secret

router = APIRouter(
    prefix="/warehouse",
    tags=["warehouse"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[tuple[Any, ...], Depends(require_workspace_admin)]


# ── Destinations ──────────────────────────────────────────────────────────────


@router.post(
    "/destinations",
    response_model=WarehouseDestinationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_destination(
    body: WarehouseDestinationCreate,
    auth: AdminDep,
    db: DbDep,
) -> WarehouseDestinationResponse:
    require_enterprise("Warehouse export destinations")
    workspace: Workspace = auth[0]
    dest = WarehouseDestination(
        workspace_id=workspace.id,
        name=body.name,
        provider=body.provider,
        bucket=body.bucket,
        prefix=body.prefix,
        region=body.region,
        endpoint_url=body.endpoint_url,
        access_key_id=encrypt_secret(body.access_key_id),
        secret_access_key=encrypt_secret(body.secret_access_key),
        format=body.format,
        resources=body.resources,
        is_active=body.is_active,
    )
    db.add(dest)
    await db.flush()
    await db.commit()
    await db.refresh(dest)
    await emit_audit_event(
        db,
        workspace_id=workspace.id,
        action="warehouse_destination.created",
        target_id=str(dest.id),
        after={"name": dest.name, "provider": dest.provider, "bucket": dest.bucket},
    )
    return WarehouseDestinationResponse.model_validate(dest)


@router.get("/destinations", response_model=WarehouseDestinationList)
async def list_destinations(
    auth: AdminDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> WarehouseDestinationList:
    workspace: Workspace = auth[0]
    q = select(WarehouseDestination).where(WarehouseDestination.workspace_id == workspace.id)
    if not include_inactive:
        q = q.where(WarehouseDestination.is_active.is_(True))
    q = q.order_by(WarehouseDestination.created_at.desc())
    result = await db.execute(q)
    items = list(result.scalars().all())
    return WarehouseDestinationList(
        items=[WarehouseDestinationResponse.model_validate(d) for d in items],
        total=len(items),
    )


@router.get("/destinations/{destination_id}", response_model=WarehouseDestinationResponse)
async def get_destination(
    destination_id: uuid.UUID,
    auth: AdminDep,
    db: DbDep,
) -> WarehouseDestinationResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(WarehouseDestination).where(
            WarehouseDestination.id == destination_id,
            WarehouseDestination.workspace_id == workspace.id,
        )
    )
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    return WarehouseDestinationResponse.model_validate(dest)


@router.put("/destinations/{destination_id}", response_model=WarehouseDestinationResponse)
async def update_destination(
    destination_id: uuid.UUID,
    body: WarehouseDestinationUpdate,
    auth: AdminDep,
    db: DbDep,
) -> WarehouseDestinationResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(WarehouseDestination).where(
            WarehouseDestination.id == destination_id,
            WarehouseDestination.workspace_id == workspace.id,
        )
    )
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    _secret_fields = {"access_key_id", "secret_access_key"}
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(dest, field, encrypt_secret(value) if field in _secret_fields else value)

    await db.commit()
    await db.refresh(dest)
    await emit_audit_event(
        db,
        workspace_id=workspace.id,
        action="warehouse_destination.updated",
        target_id=str(dest.id),
        after=body.model_dump(exclude_none=True, exclude={"secret_access_key"}),
    )
    return WarehouseDestinationResponse.model_validate(dest)


@router.delete("/destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination(
    destination_id: uuid.UUID,
    auth: AdminDep,
    db: DbDep,
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(WarehouseDestination).where(
            WarehouseDestination.id == destination_id,
            WarehouseDestination.workspace_id == workspace.id,
        )
    )
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    await db.delete(dest)
    await db.commit()
    await emit_audit_event(
        db,
        workspace_id=workspace.id,
        action="warehouse_destination.deleted",
        target_id=str(destination_id),
        after={"name": dest.name},
    )


@router.post("/destinations/{destination_id}/test", response_model=ConnectionTestResult)
async def test_destination(
    destination_id: uuid.UUID,
    auth: AdminDep,
    db: DbDep,
) -> ConnectionTestResult:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(WarehouseDestination).where(
            WarehouseDestination.id == destination_id,
            WarehouseDestination.workspace_id == workspace.id,
        )
    )
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    from runledger_api.services.warehouse import test_destination_connection

    try:
        await test_destination_connection(dest)
        return ConnectionTestResult(ok=True)
    except Exception as exc:
        return ConnectionTestResult(ok=False, error=str(exc))


# ── Export Jobs ───────────────────────────────────────────────────────────────


@router.post("/jobs", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def trigger_export_job(
    body: ExportJobTrigger,
    auth: AdminDep,
    db: DbDep,
) -> ExportJobResponse:
    workspace: Workspace = auth[0]

    result = await db.execute(
        select(WarehouseDestination).where(
            WarehouseDestination.id == body.destination_id,
            WarehouseDestination.workspace_id == workspace.id,
        )
    )
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    export_date = body.export_date or (datetime.now(UTC).date() - timedelta(days=1))
    resources = body.resources or list(dest.resources)

    job = ExportJob(
        workspace_id=workspace.id,
        destination_id=dest.id,
        export_date=export_date,
        status="pending",
        resources=resources,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await db.refresh(job)

    # Dispatch Celery task
    from runledger_api.workers.warehouse import run_single_export

    run_single_export.delay(str(job.id))

    log.info("warehouse_job_triggered", job_id=str(job.id), export_date=str(export_date))
    return ExportJobResponse.model_validate(job)


@router.get("/jobs", response_model=ExportJobList)
async def list_export_jobs(
    auth: AdminDep,
    db: DbDep,
    destination_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
) -> ExportJobList:
    workspace: Workspace = auth[0]
    q = select(ExportJob).where(ExportJob.workspace_id == workspace.id)
    if destination_id:
        q = q.where(ExportJob.destination_id == destination_id)
    if status_filter:
        q = q.where(ExportJob.status == status_filter)
    q = q.order_by(ExportJob.created_at.desc()).limit(limit)
    result = await db.execute(q)
    items = list(result.scalars().all())

    count_q = select(ExportJob).where(ExportJob.workspace_id == workspace.id)
    if destination_id:
        count_q = count_q.where(ExportJob.destination_id == destination_id)
    if status_filter:
        count_q = count_q.where(ExportJob.status == status_filter)
    total_result = await db.execute(count_q)
    total = len(list(total_result.scalars().all()))

    return ExportJobList(
        items=[ExportJobResponse.model_validate(j) for j in items],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job(
    job_id: uuid.UUID,
    auth: AdminDep,
    db: DbDep,
) -> ExportJobResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(ExportJob).where(
            ExportJob.id == job_id,
            ExportJob.workspace_id == workspace.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return ExportJobResponse.model_validate(job)
