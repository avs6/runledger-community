"""
Tests for Phase 10 Replay harness:
  POST /replay/datasets              Create dataset
  GET  /replay/datasets              List datasets
  GET  /replay/datasets/{id}         404 for unknown
  POST /replay/experiments           Create experiment
  POST /replay/experiments (bad ds)  404 when dataset not in workspace
  GET  /replay/experiments           List experiments
  POST /replay/experiments/{id}/run  Enqueue worker (Celery mocked)
  GET  /replay/experiments/{id}/results  Pending stub
  GET  /replay/experiments/{id}/results  Completed parse
  GET  /replay/datasets (no auth)    401

Uses authed_client / mock_db_session fixtures from conftest. No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Mock result helpers ────────────────────────────────────────────────────────


def _scalar_orm_result(value: object) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    return m


def _scalars_list_result(rows: list[object]) -> MagicMock:
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


# ── Factories ──────────────────────────────────────────────────────────────────


def _make_dataset(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="test-dataset",
        source="live_runs",
        run_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_experiment(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        name="test-experiment",
        configs=[{"model": "gpt-4o", "label": None}, {"model": "gpt-4o-mini", "label": None}],
        status="pending",
        estimated_cost_usd=None,
        results=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── POST /replay/datasets ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_dataset(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /replay/datasets → 201, run_count = len(run_ids)."""
    run_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
    dataset = _make_dataset(name="my-dataset", run_ids=run_ids)

    async def mock_refresh(obj: object) -> None:
        obj.id = dataset.id  # type: ignore[attr-defined]
        obj.created_at = dataset.created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh

    response = await authed_client.post(
        "/replay/datasets",
        json={"name": "my-dataset", "run_ids": run_ids},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my-dataset"
    assert data["run_count"] == 3
    assert len(data["run_ids"]) == 3


# ── GET /replay/datasets ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_datasets(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /replay/datasets → items list."""
    datasets = [_make_dataset(name="ds-1"), _make_dataset(name="ds-2")]
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result(datasets))

    response = await authed_client.get("/replay/datasets")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    names = [d["name"] for d in data["items"]]
    assert "ds-1" in names
    assert "ds-2" in names


# ── GET /replay/datasets/{id} 404 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_dataset_404(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /replay/datasets/{id} with unknown id → 404."""
    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(None))

    response = await authed_client.get(f"/replay/datasets/{uuid.uuid4()}")

    assert response.status_code == 404


# ── POST /replay/experiments ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_experiment(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /replay/experiments → 201, status=pending."""
    dataset = _make_dataset()
    experiment = _make_experiment(dataset_id=dataset.id)

    async def mock_refresh(obj: object) -> None:
        obj.id = experiment.id  # type: ignore[attr-defined]
        obj.created_at = experiment.created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh
    # First execute: dataset lookup; refresh called after commit
    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(dataset))

    response = await authed_client.post(
        "/replay/experiments",
        json={
            "dataset_id": str(dataset.id),
            "name": "test-experiment",
            "configs": [{"model": "gpt-4o"}, {"model": "gpt-4o-mini"}],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert len(data["configs"]) == 2


@pytest.mark.asyncio
async def test_create_experiment_invalid_dataset(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /replay/experiments with unknown dataset_id → 404."""
    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(None))

    response = await authed_client.post(
        "/replay/experiments",
        json={
            "dataset_id": str(uuid.uuid4()),
            "name": "bad-experiment",
            "configs": [{"model": "gpt-4o"}],
        },
    )

    assert response.status_code == 404


# ── GET /replay/experiments ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_experiments(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /replay/experiments → items list."""
    experiments = [_make_experiment(name="exp-1"), _make_experiment(name="exp-2")]
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result(experiments))

    response = await authed_client.get("/replay/experiments")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2


# ── POST /replay/experiments/{id}/run ────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_experiment(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /{id}/run → status=running, Celery worker enqueued."""
    experiment = _make_experiment()

    async def mock_refresh(obj: object) -> None:
        obj.status = "running"  # type: ignore[attr-defined]

    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(experiment))
    mock_db_session.refresh = mock_refresh

    with patch("runledger_api.workers.replay.run_experiment_worker") as mock_worker:
        mock_worker.delay = MagicMock()

        response = await authed_client.post(f"/replay/experiments/{experiment.id}/run")

        assert response.status_code == 200
        mock_worker.delay.assert_called_once_with(str(experiment.id))


# ── GET /replay/experiments/{id}/results (pending) ───────────────────────────


@pytest.mark.asyncio
async def test_get_results_pending(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET results for pending experiment → configs=[], deltas=[], status=pending."""
    experiment = _make_experiment(status="pending", results=None)
    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(experiment))

    response = await authed_client.get(f"/replay/experiments/{experiment.id}/results")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["configs"] == []
    assert data["deltas"] == []
    assert data["completed_at"] is None


# ── GET /replay/experiments/{id}/results (completed) ─────────────────────────


@pytest.mark.asyncio
async def test_get_results_completed(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET results for completed experiment → parses experiment.results dict."""
    completed_at = datetime.now(UTC).isoformat()
    results = {
        "configs": [
            {
                "model": "gpt-4o",
                "label": None,
                "run_count": 5,
                "total_input_tokens": 10000,
                "total_output_tokens": 5000,
                "projected_cost_usd": "0.15000000",
                "avg_cost_per_run": "0.03000000",
                "pricing_found": True,
                "prompt_name": "support-agent",
                "prompt_version": 2,
                "prompt_content_preview": "You are a helpful support agent...",
            },
            {
                "model": "gpt-4o-mini",
                "label": None,
                "run_count": 3,
                "total_input_tokens": 6000,
                "total_output_tokens": 3000,
                "projected_cost_usd": "0.02250000",
                "avg_cost_per_run": "0.00450000",
                "pricing_found": True,
                "prompt_name": "support-agent",
                "prompt_version": 3,
                "prompt_content_preview": "You are a concise support agent...",
            },
        ],
        "deltas": [
            {
                "config_a": "gpt-4o / support-agent@v2",
                "config_b": "gpt-4o-mini / support-agent@v3",
                "cost_delta_pct": "-85.0",
            }
        ],
        "dataset_run_count": 5,
        "completed_at": completed_at,
    }
    experiment = _make_experiment(status="completed", results=results)
    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(experiment))

    response = await authed_client.get(f"/replay/experiments/{experiment.id}/results")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["dataset_run_count"] == 5
    assert len(data["configs"]) == 2
    assert len(data["deltas"]) == 1
    assert data["configs"][0]["model"] == "gpt-4o"
    assert data["configs"][0]["prompt_name"] == "support-agent"
    assert data["configs"][0]["prompt_version"] == 2
    assert data["configs"][0]["prompt_content_preview"] == "You are a helpful support agent..."
    assert data["configs"][1]["run_count"] == 3
    assert "support-agent@v2" in data["deltas"][0]["config_a"]
    assert data["completed_at"] is not None


# ── POST /replay/experiments with prompt config ───────────────────────────────


@pytest.mark.asyncio
async def test_create_experiment_with_prompt(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Experiment configs with prompt_name + prompt_version are accepted and persisted."""
    dataset = _make_dataset()
    experiment = _make_experiment(
        dataset_id=dataset.id,
        configs=[
            {"model": "gpt-4o", "prompt_name": "support-agent", "prompt_version": 2},
            {"model": "gpt-4o", "prompt_name": "support-agent", "prompt_version": 3},
        ],
    )

    async def mock_refresh(obj: object) -> None:
        obj.id = experiment.id  # type: ignore[attr-defined]
        obj.created_at = experiment.created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh
    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(dataset))

    response = await authed_client.post(
        "/replay/experiments",
        json={
            "dataset_id": str(dataset.id),
            "name": "prompt-v2-vs-v3",
            "configs": [
                {"model": "gpt-4o", "prompt_name": "support-agent", "prompt_version": 2},
                {"model": "gpt-4o", "prompt_name": "support-agent", "prompt_version": 3},
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert len(data["configs"]) == 2
    assert data["configs"][0]["prompt_name"] == "support-agent"
    assert data["configs"][0]["prompt_version"] == 2
    assert data["configs"][1]["prompt_version"] == 3


# ── Auth guard ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_requires_auth(client: AsyncClient) -> None:
    """GET /replay/datasets without token → 401."""
    response = await client.get("/replay/datasets")
    assert response.status_code == 401
