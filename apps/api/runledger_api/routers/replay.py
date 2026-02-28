"""
Replay harness API — datasets + cost-projection experiments.

All endpoints are workspace-scoped via Bearer API key.
Prefix: /replay

Endpoints
---------
POST  /replay/datasets              Create a named dataset of run IDs
GET   /replay/datasets              List datasets for workspace
GET   /replay/datasets/{id}         Single dataset
POST  /replay/experiments           Create an experiment
GET   /replay/experiments           List experiments
GET   /replay/experiments/{id}      Single experiment
POST  /replay/experiments/{id}/run  Enqueue cost-projection worker
GET   /replay/experiments/{id}/results  Results (or pending stub)
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.replay import ReplayDataset, ReplayExperiment
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.replay import (
    ConfigDelta,
    ConfigResult,
    DatasetCreate,
    DatasetList,
    DatasetResponse,
    ExperimentCreate,
    ExperimentList,
    ExperimentResponse,
    ExperimentResults,
)

router = APIRouter(prefix="/replay", tags=["replay"], dependencies=[Depends(management_rate_limit)])
log = structlog.get_logger()


def _dataset_response(dataset: ReplayDataset) -> DatasetResponse:
    return DatasetResponse(
        id=str(dataset.id),
        name=dataset.name,
        source=dataset.source,
        run_ids=list(dataset.run_ids),
        run_count=len(dataset.run_ids),
        created_at=dataset.created_at,
    )


def _experiment_response(exp: ReplayExperiment) -> ExperimentResponse:
    return ExperimentResponse(
        id=str(exp.id),
        dataset_id=str(exp.dataset_id),
        name=exp.name,
        configs=exp.configs,
        status=exp.status,
        estimated_cost_usd=exp.estimated_cost_usd,
        created_at=exp.created_at,
    )


# ── POST /replay/datasets ─────────────────────────────────────────────────────


@router.post("/datasets", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    body: DatasetCreate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetResponse:
    """Create a named dataset of run IDs for replay experiments."""
    dataset = ReplayDataset(
        workspace_id=workspace.id,
        name=body.name,
        source=body.source,
        run_ids=body.run_ids,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return _dataset_response(dataset)


# ── GET /replay/datasets ──────────────────────────────────────────────────────


@router.get("/datasets", response_model=DatasetList)
async def list_datasets(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetList:
    """List all datasets for the workspace."""
    stmt = (
        select(ReplayDataset)
        .where(ReplayDataset.workspace_id == workspace.id)
        .order_by(ReplayDataset.created_at.desc())
    )
    result = await db.execute(stmt)
    datasets = result.scalars().all()
    return DatasetList(items=[_dataset_response(d) for d in datasets])


# ── GET /replay/datasets/{id} ─────────────────────────────────────────────────


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DatasetResponse:
    """Fetch a single dataset by ID."""
    try:
        did = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Dataset not found")

    stmt = select(ReplayDataset).where(
        ReplayDataset.id == did,
        ReplayDataset.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _dataset_response(dataset)


# ── POST /replay/experiments ──────────────────────────────────────────────────


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    body: ExperimentCreate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentResponse:
    """Create a cost-projection experiment referencing a dataset."""
    try:
        did = uuid.UUID(body.dataset_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Verify dataset belongs to workspace
    ds_stmt = select(ReplayDataset).where(
        ReplayDataset.id == did,
        ReplayDataset.workspace_id == workspace.id,
    )
    ds_result = await db.execute(ds_stmt)
    dataset = ds_result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    experiment = ReplayExperiment(
        workspace_id=workspace.id,
        dataset_id=did,
        name=body.name,
        configs=[c.model_dump() for c in body.configs],
        status="pending",
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return _experiment_response(experiment)


# ── GET /replay/experiments ───────────────────────────────────────────────────


@router.get("/experiments", response_model=ExperimentList)
async def list_experiments(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentList:
    """List all experiments for the workspace."""
    stmt = (
        select(ReplayExperiment)
        .where(ReplayExperiment.workspace_id == workspace.id)
        .order_by(ReplayExperiment.created_at.desc())
    )
    result = await db.execute(stmt)
    experiments = result.scalars().all()
    return ExperimentList(items=[_experiment_response(e) for e in experiments])


# ── GET /replay/experiments/{id} ──────────────────────────────────────────────


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentResponse:
    """Fetch a single experiment by ID."""
    try:
        eid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Experiment not found")

    stmt = select(ReplayExperiment).where(
        ReplayExperiment.id == eid,
        ReplayExperiment.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    exp = result.scalar_one_or_none()
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _experiment_response(exp)


# ── POST /replay/experiments/{id}/run ────────────────────────────────────────


@router.post("/experiments/{experiment_id}/run", response_model=ExperimentResponse)
async def run_experiment(
    experiment_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentResponse:
    """Enqueue the cost-projection worker for this experiment."""
    from runledger_api.workers.replay import run_experiment_worker  # noqa: PLC0415

    try:
        eid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Experiment not found")

    stmt = select(ReplayExperiment).where(
        ReplayExperiment.id == eid,
        ReplayExperiment.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    exp = result.scalar_one_or_none()
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    exp.status = "running"
    await db.commit()
    await db.refresh(exp)

    run_experiment_worker.delay(str(exp.id))
    log.info("replay.experiment.queued", experiment_id=str(exp.id))

    return _experiment_response(exp)


# ── GET /replay/experiments/{id}/results ─────────────────────────────────────


@router.get("/experiments/{experiment_id}/results", response_model=ExperimentResults)
async def get_experiment_results(
    experiment_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentResults:
    """Fetch experiment results; returns empty stub if not yet completed."""
    try:
        eid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Experiment not found")

    stmt = select(ReplayExperiment).where(
        ReplayExperiment.id == eid,
        ReplayExperiment.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    exp = result.scalar_one_or_none()
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if exp.status != "completed" or not exp.results:
        return ExperimentResults(
            experiment_id=str(exp.id),
            experiment_name=exp.name,
            status=exp.status,
            dataset_run_count=0,
            configs=[],
            deltas=[],
            completed_at=None,
        )

    raw = exp.results
    configs = [ConfigResult(**c) for c in raw.get("configs", [])]
    deltas = [ConfigDelta(**d) for d in raw.get("deltas", [])]
    completed_at_str = raw.get("completed_at")
    completed_at = datetime.fromisoformat(completed_at_str) if completed_at_str else None

    return ExperimentResults(
        experiment_id=str(exp.id),
        experiment_name=exp.name,
        status=exp.status,
        dataset_run_count=raw.get("dataset_run_count", 0),
        configs=configs,
        deltas=deltas,
        completed_at=completed_at,
    )
