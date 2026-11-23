"""
Experiments & Datasets API — the one experiment system (review B-07).

Prefix: /experiments  (datasets at /datasets)
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /datasets                    Create a dataset
POST   /datasets/from-runs          Curate a replay dataset from recorded runs
GET    /datasets                    List datasets (paged; X-Total-Count)
GET    /datasets/{id}               Get dataset + items
PUT    /datasets/{id}               Update dataset
DELETE /datasets/{id}               Delete dataset

POST   /experiments                 Create experiment (mode = eval | replay)
GET    /experiments                 List experiments (paged; ?mode=&status=)
GET    /experiments/{id}            Get experiment + results
PUT    /experiments/{id}            Update experiment
DELETE /experiments/{id}            Delete experiment
POST   /experiments/{id}/run        Run the dataset through the gateway
POST   /experiments/{id}/recommend-route  Turn the result into a Flywheel recommendation

Runs really execute (review B-08): every item × model goes through gateway-rs with
the caller's key, is recorded as a run, and is scored by the experiment's
evaluators. The old replay harness (``/replay``, cost projection only) is merged in
as ``mode="replay"``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import AsyncSessionLocal, get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_writer
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.eval_experiments import EvalDataset, EvalExperiment
from runledger_api.models.evaluators import Evaluator
from runledger_api.models.events import AgentRun
from runledger_api.models.flywheel import FlywheelRecommendation
from runledger_api.models.gateway import GatewayRoute
from runledger_api.models.prompts import Prompt
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.eval_experiments import (
    DatasetFromRuns,
    EvalDatasetCreate,
    EvalDatasetList,
    EvalDatasetResponse,
    EvalDatasetUpdate,
    EvalExperimentCreate,
    EvalExperimentList,
    EvalExperimentResponse,
    EvalExperimentUpdate,
    RouteRecommendationRequest,
    RouteRecommendationResponse,
)
from runledger_api.services import gateway_client
from runledger_api.services.evaluators import load_run_payloads
from runledger_api.services.experiments import execute_experiment, pick_recommendation

router = APIRouter(
    tags=["experiments"],
    dependencies=[Depends(management_rate_limit)],
)

log = structlog.get_logger()
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _dataset_or_404(db: AsyncSession, dataset_id: uuid.UUID, ws: Workspace) -> EvalDataset:
    ds = await db.get(EvalDataset, dataset_id)
    if not ds or ds.workspace_id != ws.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    return ds


async def _experiment_or_404(
    db: AsyncSession, experiment_id: uuid.UUID, ws: Workspace
) -> EvalExperiment:
    exp = await db.get(EvalExperiment, experiment_id)
    if not exp or exp.workspace_id != ws.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found")
    return exp


async def _validate_refs(
    db: AsyncSession,
    ws: Workspace,
    *,
    dataset_id: uuid.UUID | None,
    prompt_name: str | None,
    evaluator_ids: list[uuid.UUID] | None,
) -> None:
    if dataset_id:
        await _dataset_or_404(db, dataset_id, ws)
    if prompt_name:
        found = (
            await db.execute(
                select(Prompt.id).where(Prompt.workspace_id == ws.id, Prompt.name == prompt_name)
            )
        ).scalar_one_or_none()
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Prompt '{prompt_name}' not found")
    for eid in evaluator_ids or []:
        ev = await db.get(Evaluator, eid)
        if ev is None or ev.workspace_id != ws.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Evaluator {eid} not found")


# ── Datasets ──────────────────────────────────────────────────────────────────


@router.post(
    "/datasets",
    response_model=EvalDatasetResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def create_dataset(
    body: EvalDatasetCreate, workspace: WorkspaceDep, db: DbDep
) -> EvalDataset:
    items_raw = [i.model_dump(exclude_none=True) for i in body.items]
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


@router.post(
    "/datasets/from-runs",
    response_model=EvalDatasetResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def create_dataset_from_runs(
    body: DatasetFromRuns, workspace: WorkspaceDep, db: DbDep
) -> EvalDataset:
    """Curate a replay dataset from recorded runs (their captured conversations).

    Runs without a captured input are reported back in ``description`` and left out:
    replaying needs the original messages.
    """
    run_ids = list(dict.fromkeys(body.run_ids))
    owned = set(
        (
            await db.execute(
                select(AgentRun.id).where(
                    AgentRun.workspace_id == workspace.id, AgentRun.id.in_(run_ids)
                )
            )
        )
        .scalars()
        .all()
    )
    missing = [str(r) for r in run_ids if r not in owned]
    if missing:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Runs not found in this workspace: {', '.join(missing[:5])}"
        )
    payloads = await load_run_payloads(db, run_ids)
    items: list[dict[str, Any]] = []
    uncaptured = 0
    for rid in run_ids:
        captured = payloads.get(rid) or {}
        messages = captured.get("input_payload")
        if not isinstance(messages, list) or not messages:
            uncaptured += 1
            continue
        item: dict[str, Any] = {"run_id": str(rid), "messages": messages, "metadata": {}}
        output = captured.get("output_payload")
        if body.use_output_as_expected and output is not None:
            from runledger_api.services.evaluators import payload_text  # noqa: PLC0415

            item["expected_output"] = payload_text(output)[:4000]
        items.append(item)
    if not items:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "None of these runs has a captured conversation; enable payload capture to replay",
        )
    description = body.description or ""
    if uncaptured:
        description = (description + f" ({uncaptured} run(s) skipped: no captured input)").strip()
    ds = EvalDataset(
        workspace_id=workspace.id,
        name=body.name,
        description=description or None,
        source="runs",
        items=items,
        item_count=len(items),
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return ds


@router.get("/datasets", response_model=EvalDatasetList)
async def list_datasets(
    workspace: WorkspaceDep,
    db: DbDep,
    page: PageDep,
    response: Response,
    source: Annotated[str | None, Query()] = None,
) -> EvalDatasetList:
    stmt = select(EvalDataset).where(EvalDataset.workspace_id == workspace.id)
    if source:
        stmt = stmt.where(EvalDataset.source == source)
    rows = await paginate(
        db, stmt.order_by(EvalDataset.created_at.desc(), EvalDataset.id), page, response
    )
    return EvalDatasetList(items=rows)  # type: ignore[arg-type]


@router.get("/datasets/{dataset_id}", response_model=EvalDatasetResponse)
async def get_dataset(dataset_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> EvalDataset:
    return await _dataset_or_404(db, dataset_id, workspace)


@router.put(
    "/datasets/{dataset_id}",
    response_model=EvalDatasetResponse,
    dependencies=[Depends(require_workspace_writer)],
)
async def update_dataset(
    dataset_id: uuid.UUID, body: EvalDatasetUpdate, workspace: WorkspaceDep, db: DbDep
) -> EvalDataset:
    ds = await _dataset_or_404(db, dataset_id, workspace)
    if body.name is not None:
        ds.name = body.name
    if body.description is not None:
        ds.description = body.description
    if body.items is not None:
        items_raw = [i.model_dump(exclude_none=True) for i in body.items]
        ds.items = items_raw
        ds.item_count = len(items_raw)
    ds.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(ds)
    return ds


@router.delete(
    "/datasets/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_writer)],
)
async def delete_dataset(dataset_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> None:
    ds = await _dataset_or_404(db, dataset_id, workspace)
    await db.delete(ds)
    await db.commit()


# ── Experiments ───────────────────────────────────────────────────────────────


@router.post(
    "/experiments",
    response_model=EvalExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def create_experiment(
    body: EvalExperimentCreate, workspace: WorkspaceDep, db: DbDep
) -> EvalExperiment:
    await _validate_refs(
        db,
        workspace,
        dataset_id=body.dataset_id,
        prompt_name=body.prompt_name,
        evaluator_ids=body.evaluator_ids,
    )
    exp = EvalExperiment(
        workspace_id=workspace.id,
        dataset_id=body.dataset_id,
        name=body.name,
        description=body.description,
        mode=body.mode,
        prompt_name=body.prompt_name,
        prompt_version=body.prompt_version,
        evaluator_ids=[str(eid) for eid in body.evaluator_ids],
        models=[m.model_dump(exclude_none=True) for m in body.models],
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
    page: PageDep,
    response: Response,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    mode: Annotated[str | None, Query(pattern="^(eval|replay)$")] = None,
    prompt_name: Annotated[str | None, Query()] = None,
) -> EvalExperimentList:
    q = select(EvalExperiment).where(EvalExperiment.workspace_id == workspace.id)
    if status_filter:
        q = q.where(EvalExperiment.status == status_filter)
    if mode:
        q = q.where(EvalExperiment.mode == mode)
    if prompt_name:
        q = q.where(EvalExperiment.prompt_name == prompt_name)
    rows = await paginate(
        db, q.order_by(EvalExperiment.created_at.desc(), EvalExperiment.id), page, response
    )
    return EvalExperimentList(items=rows)  # type: ignore[arg-type]


@router.get("/experiments/{experiment_id}", response_model=EvalExperimentResponse)
async def get_experiment(
    experiment_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep
) -> EvalExperiment:
    return await _experiment_or_404(db, experiment_id, workspace)


@router.put(
    "/experiments/{experiment_id}",
    response_model=EvalExperimentResponse,
    dependencies=[Depends(require_workspace_writer)],
)
async def update_experiment(
    experiment_id: uuid.UUID, body: EvalExperimentUpdate, workspace: WorkspaceDep, db: DbDep
) -> EvalExperiment:
    exp = await _experiment_or_404(db, experiment_id, workspace)
    if exp.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot update a running experiment")
    await _validate_refs(
        db,
        workspace,
        dataset_id=body.dataset_id,
        prompt_name=body.prompt_name,
        evaluator_ids=body.evaluator_ids,
    )
    if body.name is not None:
        exp.name = body.name
    if body.description is not None:
        exp.description = body.description
    if body.mode is not None:
        exp.mode = body.mode
    if body.dataset_id is not None:
        exp.dataset_id = body.dataset_id
    if body.prompt_name is not None:
        exp.prompt_name = body.prompt_name or None
    if body.prompt_version is not None:
        exp.prompt_version = body.prompt_version or None
    if body.evaluator_ids is not None:
        exp.evaluator_ids = [str(e) for e in body.evaluator_ids]
    if body.models is not None:
        exp.models = [m.model_dump(exclude_none=True) for m in body.models]
    await db.commit()
    await db.refresh(exp)
    return exp


@router.delete(
    "/experiments/{experiment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_writer)],
)
async def delete_experiment(experiment_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> None:
    exp = await _experiment_or_404(db, experiment_id, workspace)
    if exp.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot delete a running experiment")
    await db.delete(exp)
    await db.commit()


async def _run_in_background(experiment_id: uuid.UUID, authorization: str) -> None:
    async with AsyncSessionLocal() as db:
        exp = await db.get(EvalExperiment, experiment_id)
        if exp is not None:
            await execute_experiment(db, exp, authorization)


@router.post(
    "/experiments/{experiment_id}/run",
    response_model=EvalExperimentResponse,
    dependencies=[Depends(require_workspace_writer)],
)
async def run_experiment(
    experiment_id: uuid.UUID,
    request: Request,
    background: BackgroundTasks,
    workspace: WorkspaceDep,
    db: DbDep,
    wait: Annotated[bool, Query()] = False,
) -> EvalExperiment:
    """Run the dataset through the gateway once per model and score the outputs.

    Calls use the caller's API key, so budgets, guardrails and routing apply and
    each call is a recorded run. By default the run continues in the background
    (poll ``GET /experiments/{id}``); ``?wait=true`` returns the finished result.
    """
    exp = await _experiment_or_404(db, experiment_id, workspace)
    if exp.status == "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Experiment already running")
    if exp.dataset_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Experiment has no dataset")
    if not exp.models:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Experiment has no models")
    authorization = gateway_client.bearer_from_headers(request.headers)
    if authorization is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Experiments run through the gateway with your API key; send it as a Bearer token",
        )
    if wait:
        return await execute_experiment(db, exp, authorization)
    exp.status = "running"
    exp.started_at = datetime.now(UTC)
    exp.results = None
    await db.commit()
    await db.refresh(exp)
    background.add_task(_run_in_background, exp.id, authorization)
    return exp


@router.post(
    "/experiments/{experiment_id}/recommend-route",
    response_model=RouteRecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer)],
)
async def recommend_route(
    experiment_id: uuid.UUID,
    body: RouteRecommendationRequest,
    workspace: WorkspaceDep,
    db: DbDep,
) -> RouteRecommendationResponse:
    """Turn a completed experiment into a pending Flywheel recommendation (review B-05).

    The baseline is the experiment's first model (a route alias); the candidate is
    the cheapest model that holds the baseline score within ``max_score_drop``, or
    the best scorer. The recommendation proposes switching the baseline alias's
    primary route to the candidate's target model, and is applied (with audit and
    rollback) through ``POST /gateway/flywheel/recommendations/{id}/apply``.
    """
    exp = await _experiment_or_404(db, experiment_id, workspace)
    if exp.status != "completed" or not isinstance(exp.results, dict):
        raise HTTPException(status.HTTP_409_CONFLICT, "Run the experiment to completion first")
    picked = pick_recommendation(exp.results, body.max_score_drop)
    if picked is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No candidate beats the baseline on cost at equal quality, or on quality",
        )
    baseline, candidate = picked

    async def primary_target(alias: str) -> str | None:
        route = (
            await db.execute(
                select(GatewayRoute)
                .where(
                    GatewayRoute.workspace_id == workspace.id,
                    GatewayRoute.alias == alias,
                    GatewayRoute.is_active.is_(True),
                )
                .order_by(GatewayRoute.priority)
                .limit(1)
            )
        ).scalar_one_or_none()
        return route.target_model if route else None

    base_target = await primary_target(baseline["model"])
    if base_target is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Baseline '{baseline['model']}' is not an active gateway route alias",
        )
    cand_target = await primary_target(candidate["model"]) or candidate["model"]
    cost_pct = None
    try:
        b, c = float(baseline["avg_cost_usd"]), float(candidate["avg_cost_usd"])
        cost_pct = Decimal(str(round((c - b) / b * 100, 4))) if b else None
    except (TypeError, ValueError, KeyError):
        cost_pct = None
    rec = FlywheelRecommendation(
        workspace_id=workspace.id,
        segment_by="alias",
        segment_key=baseline["model"],
        kind="switch",
        current_config={"model": base_target, "source": "experiment"},
        proposed_config={"model": cand_target},
        est_cost_delta_pct=cost_pct,
        current_quality=_dec(baseline.get("avg_score")),
        proposed_quality=_dec(candidate.get("avg_score")),
        min_quality=_dec(baseline.get("avg_score")) or Decimal("0"),
        sample_size=int(candidate.get("scored_items") or candidate.get("items_run") or 0),
        confidence="medium" if (candidate.get("scored_items") or 0) >= 20 else "low",
        rationale=(
            f"Experiment '{exp.name}': {candidate['label']} scored "
            f"{candidate.get('avg_score')} vs {baseline.get('avg_score')} for "
            f"{baseline['label']}, avg cost {candidate.get('avg_cost_usd')} vs "
            f"{baseline.get('avg_cost_usd')} (experiment {exp.id})."
        ),
        status="pending",
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return RouteRecommendationResponse(
        recommendation_id=rec.id,
        alias=baseline["model"],
        current_model=base_target,
        proposed_model=cand_target,
        current_quality=baseline.get("avg_score"),
        proposed_quality=candidate.get("avg_score"),
        est_cost_delta_pct=float(cost_pct) if cost_pct is not None else None,
        rationale=rec.rationale or "",
    )


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(float(value), 4)))
