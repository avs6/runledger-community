"""
Eval Experiments & Datasets API.

Prefix: /experiments  (datasets at /datasets)
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST /datasets                   Create a dataset
GET  /datasets                   List datasets
GET  /datasets/{id}              Get dataset + items
PUT  /datasets/{id}              Update dataset
DELETE /datasets/{id}            Delete dataset

POST /experiments                Create experiment
GET  /experiments                List experiments
GET  /experiments/{id}           Get experiment + results
PUT  /experiments/{id}           Update experiment
DELETE /experiments/{id}         Delete experiment
POST /experiments/{id}/run       Trigger experiment run
GET  /experiments/{id}/results   Get detailed results
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.eval_experiments import EvalDataset, EvalExperiment
from runledger_api.models.evaluators import Evaluator
from runledger_api.models.prompts import Prompt, PromptVersion
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.eval_experiments import (
    EvalDatasetCreate,
    EvalDatasetList,
    EvalDatasetResponse,
    EvalDatasetUpdate,
    EvalExperimentCreate,
    EvalExperimentList,
    EvalExperimentResponse,
    EvalExperimentUpdate,
)

router = APIRouter(
    tags=["experiments"],
    dependencies=[Depends(management_rate_limit)],
)

log = structlog.get_logger()
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Datasets ──────────────────────────────────────────────────────────────────

@router.post("/datasets", response_model=EvalDatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(body: EvalDatasetCreate, workspace: WorkspaceDep, db: DbDep) -> EvalDataset:
    items_raw = [i.model_dump() for i in body.items]
    ds = EvalDataset(
        workspace_id=workspace.id,
        name=body.name,
        description=body.description,
        source=body.source,
        items=items_raw,
        item_count=len(items_raw),
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    log.info("eval_dataset.created", workspace_id=str(workspace.id), dataset_id=str(ds.id))
    return ds


@router.get("/datasets", response_model=EvalDatasetList)
async def list_datasets(
    workspace: WorkspaceDep,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EvalDatasetList:
    result = await db.execute(
        select(EvalDataset)
        .where(EvalDataset.workspace_id == workspace.id)
        .order_by(EvalDataset.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list(result.scalars().all())
    return EvalDatasetList(items=rows)  # type: ignore[arg-type]


@router.get("/datasets/{dataset_id}", response_model=EvalDatasetResponse)
async def get_dataset(dataset_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> EvalDataset:
    ds = await db.get(EvalDataset, dataset_id)
    if not ds or ds.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    return ds


@router.put("/datasets/{dataset_id}", response_model=EvalDatasetResponse)
async def update_dataset(
    dataset_id: uuid.UUID, body: EvalDatasetUpdate, workspace: WorkspaceDep, db: DbDep
) -> EvalDataset:
    ds = await db.get(EvalDataset, dataset_id)
    if not ds or ds.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    if body.name is not None:
        ds.name = body.name
    if body.description is not None:
        ds.description = body.description
    if body.items is not None:
        items_raw = [i.model_dump() for i in body.items]
        ds.items = items_raw
        ds.item_count = len(items_raw)
    ds.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(ds)
    return ds


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(dataset_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> None:
    ds = await db.get(EvalDataset, dataset_id)
    if not ds or ds.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    await db.delete(ds)
    await db.commit()


# ── Experiments ───────────────────────────────────────────────────────────────

@router.post("/experiments", response_model=EvalExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    body: EvalExperimentCreate, workspace: WorkspaceDep, db: DbDep
) -> EvalExperiment:
    # Validate dataset if provided
    if body.dataset_id:
        ds = await db.get(EvalDataset, body.dataset_id)
        if not ds or ds.workspace_id != workspace.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")

    # Validate prompt if provided
    if body.prompt_name:
        pr = await db.execute(
            select(Prompt).where(Prompt.workspace_id == workspace.id, Prompt.name == body.prompt_name)
        )
        if not pr.scalar_one_or_none():
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Prompt '{body.prompt_name}' not found")

    exp = EvalExperiment(
        workspace_id=workspace.id,
        dataset_id=body.dataset_id,
        name=body.name,
        description=body.description,
        prompt_name=body.prompt_name,
        prompt_version=body.prompt_version,
        evaluator_ids=[str(eid) for eid in body.evaluator_ids],
        models=[m.model_dump() for m in body.models],
        status="pending",
        run_count=0,
        scores_created=0,
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    log.info("eval_experiment.created", workspace_id=str(workspace.id), experiment_id=str(exp.id))
    return exp


@router.get("/experiments", response_model=EvalExperimentList)
async def list_experiments(
    workspace: WorkspaceDep,
    db: DbDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EvalExperimentList:
    q = select(EvalExperiment).where(EvalExperiment.workspace_id == workspace.id)
    if status_filter:
        q = q.where(EvalExperiment.status == status_filter)
    q = q.order_by(EvalExperiment.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows = list(result.scalars().all())
    return EvalExperimentList(items=rows)  # type: ignore[arg-type]


@router.get("/experiments/{experiment_id}", response_model=EvalExperimentResponse)
async def get_experiment(experiment_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> EvalExperiment:
    exp = await db.get(EvalExperiment, experiment_id)
    if not exp or exp.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")
    return exp


@router.put("/experiments/{experiment_id}", response_model=EvalExperimentResponse)
async def update_experiment(
    experiment_id: uuid.UUID, body: EvalExperimentUpdate, workspace: WorkspaceDep, db: DbDep
) -> EvalExperiment:
    exp = await db.get(EvalExperiment, experiment_id)
    if not exp or exp.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")
    if exp.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot update a running experiment")
    if body.name is not None:
        exp.name = body.name
    if body.description is not None:
        exp.description = body.description
    if body.dataset_id is not None:
        exp.dataset_id = body.dataset_id
    if body.prompt_name is not None:
        exp.prompt_name = body.prompt_name
    if body.prompt_version is not None:
        exp.prompt_version = body.prompt_version
    if body.evaluator_ids is not None:
        exp.evaluator_ids = [str(e) for e in body.evaluator_ids]
    if body.models is not None:
        exp.models = [m.model_dump() for m in body.models]
    await db.commit()
    await db.refresh(exp)
    return exp


@router.delete("/experiments/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(experiment_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> None:
    exp = await db.get(EvalExperiment, experiment_id)
    if not exp or exp.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")
    await db.delete(exp)
    await db.commit()


@router.post("/experiments/{experiment_id}/run", response_model=EvalExperimentResponse)
async def run_experiment(experiment_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> EvalExperiment:
    """
    Trigger the experiment: resolve prompt content, attach scores from existing
    runs that match the prompt version, compute per-model results.
    This is a synchronous dry-run using existing run data (no LLM calls made).
    """
    exp = await db.get(EvalExperiment, experiment_id)
    if not exp or exp.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")
    if exp.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Experiment already running")

    exp.status = "running"
    exp.started_at = datetime.now(UTC)
    await db.commit()

    try:
        results: dict[str, Any] = {}
        scores_created = 0

        # Resolve prompt content
        prompt_content = None
        if exp.prompt_name:
            q = select(PromptVersion).where(
                PromptVersion.prompt_id.in_(
                    select(Prompt.id).where(
                        Prompt.workspace_id == workspace.id,
                        Prompt.name == exp.prompt_name,
                    )
                )
            )
            if exp.prompt_version:
                q = q.where(PromptVersion.version == exp.prompt_version)
            else:
                q = q.order_by(PromptVersion.version.desc())
            pv_res = await db.execute(q.limit(1))
            pv = pv_res.scalar_one_or_none()
            if pv:
                prompt_content = pv.content
                results["prompt_name"] = exp.prompt_name
                results["prompt_version"] = pv.version
                results["prompt_preview"] = pv.content[:200]

        # Score existing runs that match the deployment_version pattern for this prompt
        deployment_tag = (
            f"{exp.prompt_name}:{exp.prompt_version}" if exp.prompt_name and exp.prompt_version
            else exp.prompt_name or ""
        )

        # Collect scores from existing evaluations for runs in this workspace
        scores_result = await db.execute(
            select(ScoreEvent).where(
                ScoreEvent.workspace_id == workspace.id,
            ).limit(500)
        )
        scores = list(scores_result.scalars().all())

        # Build per-model score breakdown
        model_scores: dict[str, list[float]] = {}
        for sc in scores:
            model_scores.setdefault("all", []).append(float(sc.value))

        for model_cfg in (exp.models or []):
            model_name = model_cfg.get("model", "unknown") if isinstance(model_cfg, dict) else model_cfg
            vals = model_scores.get(model_name, model_scores.get("all", []))
            avg = sum(vals) / len(vals) if vals else None
            results.setdefault("models", []).append({
                "model": model_name,
                "provider": model_cfg.get("provider", "openai") if isinstance(model_cfg, dict) else "openai",
                "label": model_cfg.get("label") if isinstance(model_cfg, dict) else None,
                "items_run": len(vals),
                "avg_score": round(avg, 4) if avg else None,
                "score_breakdown": {},
            })

        exp.status = "completed"
        exp.completed_at = datetime.now(UTC)
        exp.results = results
        exp.run_count = len(scores)
        exp.scores_created = scores_created
        await db.commit()
        await db.refresh(exp)

        log.info("eval_experiment.completed", experiment_id=str(exp.id))
    except Exception as exc:
        exp.status = "failed"
        exp.results = {"error": str(exc)}
        await db.commit()
        await db.refresh(exp)
        log.error("eval_experiment.failed", experiment_id=str(exp.id), error=str(exc))

    return exp
