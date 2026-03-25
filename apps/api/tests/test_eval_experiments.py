"""Tests for eval experiments, datasets, and GitHub prompt sync."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── helpers ────────────────────────────────────────────────────────────────────


def _ds(workspace_id: uuid.UUID | None = None, **kw) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        name=kw.get("name", "Test Dataset"),
        description=kw.get("description"),
        source="manual",
        items=kw.get("items", []),
        item_count=kw.get("item_count", 0),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _exp(workspace_id: uuid.UUID | None = None, **kw) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        dataset_id=kw.get("dataset_id"),
        name=kw.get("name", "Test Experiment"),
        description=kw.get("description"),
        prompt_name=kw.get("prompt_name"),
        prompt_version=kw.get("prompt_version"),
        evaluator_ids=[],
        models=[],
        status=kw.get("status", "pending"),
        results=kw.get("results"),
        run_count=0,
        scores_created=0,
        started_at=None,
        completed_at=None,
        created_by=None,
        created_at=datetime.now(UTC),
    )


# ── Datasets ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_dataset(authed_client, mock_db_session, mock_workspace):
    ds = _ds(workspace_id=mock_workspace.id, name="QA Suite", item_count=2)
    ds.items = [{"input": "What is 2+2?", "expected_output": "4", "metadata": {}}]

    def _refresh(obj):
        obj.id = ds.id
        obj.created_at = ds.created_at
        obj.updated_at = ds.updated_at

    mock_db_session.refresh = AsyncMock(side_effect=_refresh)

    resp = await authed_client.post(
        "/datasets",
        json={
            "name": "QA Suite",
            "items": [{"input": "What is 2+2?", "expected_output": "4"}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "QA Suite"


@pytest.mark.asyncio
async def test_list_datasets(authed_client, mock_db_session, mock_workspace):
    ds = _ds(workspace_id=mock_workspace.id)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [ds]
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get("/datasets")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_dataset(authed_client, mock_db_session, mock_workspace):
    ds_id = uuid.uuid4()
    ds = _ds(workspace_id=mock_workspace.id)
    mock_db_session.get = AsyncMock(return_value=ds)

    resp = await authed_client.get(f"/datasets/{ds_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_dataset_not_found(authed_client, mock_db_session, mock_workspace):
    mock_db_session.get = AsyncMock(return_value=None)

    resp = await authed_client.get(f"/datasets/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_dataset_wrong_workspace(authed_client, mock_db_session, mock_workspace):
    ds = _ds(workspace_id=uuid.uuid4())  # different workspace
    mock_db_session.get = AsyncMock(return_value=ds)

    resp = await authed_client.get(f"/datasets/{ds.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_dataset(authed_client, mock_db_session, mock_workspace):
    ds = _ds(workspace_id=mock_workspace.id)
    mock_db_session.get = AsyncMock(return_value=ds)
    mock_db_session.delete = AsyncMock()

    resp = await authed_client.delete(f"/datasets/{ds.id}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(ds)


# ── Experiments ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_experiment(authed_client, mock_db_session, mock_workspace):
    exp = _exp(workspace_id=mock_workspace.id, name="GPT-4o eval")

    def _refresh(obj):
        obj.id = exp.id
        obj.created_at = exp.created_at

    mock_db_session.refresh = AsyncMock(side_effect=_refresh)
    # No dataset, no prompt — skips validation queries
    mock_db_session.get = AsyncMock(return_value=None)

    resp = await authed_client.post(
        "/experiments",
        json={"name": "GPT-4o eval"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "GPT-4o eval"


@pytest.mark.asyncio
async def test_create_experiment_with_dataset(authed_client, mock_db_session, mock_workspace):
    ds_id = uuid.uuid4()
    ds = _ds(workspace_id=mock_workspace.id)
    exp = _exp(workspace_id=mock_workspace.id, dataset_id=ds_id)

    def _get_side(model, pk):
        if model.__tablename__ == "eval_datasets":
            return ds
        return None

    mock_db_session.get = AsyncMock(side_effect=_get_side)

    def _refresh(obj):
        obj.id = exp.id
        obj.created_at = exp.created_at

    mock_db_session.refresh = AsyncMock(side_effect=_refresh)

    resp = await authed_client.post(
        "/experiments",
        json={"name": "Eval with dataset", "dataset_id": str(ds_id)},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_experiments(authed_client, mock_db_session, mock_workspace):
    exp = _exp(workspace_id=mock_workspace.id)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [exp]
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get("/experiments")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_experiments_status_filter(authed_client, mock_db_session, mock_workspace):
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get("/experiments?status=completed")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_experiment(authed_client, mock_db_session, mock_workspace):
    exp = _exp(workspace_id=mock_workspace.id)
    mock_db_session.get = AsyncMock(return_value=exp)
    mock_db_session.delete = AsyncMock()

    resp = await authed_client.delete(f"/experiments/{exp.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_run_experiment(authed_client, mock_db_session, mock_workspace):
    exp = _exp(workspace_id=mock_workspace.id, status="pending")
    mock_db_session.get = AsyncMock(return_value=exp)

    scores_result = MagicMock()
    scores_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=scores_result)

    def _refresh(obj):
        pass  # obj already mutated in-place

    mock_db_session.refresh = AsyncMock(side_effect=_refresh)

    resp = await authed_client.post(f"/experiments/{exp.id}/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_run_experiment_already_running(authed_client, mock_db_session, mock_workspace):
    exp = _exp(workspace_id=mock_workspace.id, status="running")
    mock_db_session.get = AsyncMock(return_value=exp)

    resp = await authed_client.post(f"/experiments/{exp.id}/run")
    assert resp.status_code == 409


# ── GitHub sync ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_github_config_none(authed_client, mock_db_session, mock_workspace):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get("/prompts/github-config")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_create_github_config(authed_client, mock_db_session, mock_workspace):
    cfg = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=mock_workspace.id,
        repo="acme/prompts",
        branch="main",
        path_prefix="prompts/",
        token_enc=None,
        auto_sync=False,
        last_sync_at=None,
        last_sync_status=None,
        last_sync_message=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    # No existing config
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    def _refresh(obj):
        obj.id = cfg.id
        obj.created_at = cfg.created_at
        obj.updated_at = cfg.updated_at

    mock_db_session.refresh = AsyncMock(side_effect=_refresh)

    resp = await authed_client.post(
        "/prompts/github-config",
        json={"repo": "acme/prompts", "branch": "main"},
    )
    assert resp.status_code == 201
    assert resp.json()["repo"] == "acme/prompts"


@pytest.mark.asyncio
async def test_push_to_github_no_config(authed_client, mock_db_session, mock_workspace):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.post("/prompts/sync/push")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pull_from_github_no_config(authed_client, mock_db_session, mock_workspace):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.post("/prompts/sync/pull")
    assert resp.status_code == 404
