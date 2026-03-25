"""
Tests for Kafka export configs, delivery log, and dispatch service.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from runledger_api.routers.kafka_export import router

# ── App fixture ───────────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router)


def _ws():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def authed_client(mock_db):
    from runledger_api.core.deps import get_db, require_workspace_admin

    ws = _ws()
    app.dependency_overrides[get_db] = lambda: mock_db
    # require_workspace_admin returns (workspace, user, workspace_user)
    app.dependency_overrides[require_workspace_admin] = lambda: (ws, None, None)
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test"), mock_db, ws
    app.dependency_overrides.clear()


# ── Helper: make a mock KafkaExportConfig ─────────────────────────────────────

def _cfg(workspace_id=None, **kwargs):
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        label="test kafka",
        bootstrap_servers="localhost:9092",
        topic_prefix="runledger",
        security_protocol="PLAINTEXT",
        sasl_mechanism=None,
        sasl_username=None,
        sasl_password_encrypted=None,
        ssl_ca_cert=None,
        event_types=["run.completed", "alert.fired"],
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        **kwargs,
    )


def _delivery(config_id):
    return SimpleNamespace(
        id=uuid.uuid4(),
        config_id=config_id,
        event_type="run.completed",
        topic="runledger.runs",
        status="success",
        error_detail=None,
        attempt=1,
        delivered_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


# ── POST /integrations/kafka/configs ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_kafka_config(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)

    async def mock_refresh(obj, **kw):
        obj.id = cfg.id
        obj.workspace_id = ws.id
        obj.enabled = True
        obj.event_types = obj.event_types or ["run.completed", "alert.fired"]
        obj.created_at = cfg.created_at
        obj.updated_at = cfg.updated_at

    db.refresh.side_effect = mock_refresh

    resp = await client.post(
        "/integrations/kafka/configs",
        json={
            "label": "prod kafka",
            "bootstrap_servers": "broker:9092",
            "topic_prefix": "rl",
            "security_protocol": "PLAINTEXT",
            "event_types": ["run.completed", "alert.fired"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["bootstrap_servers"] == "broker:9092"
    assert data["topic_prefix"] == "rl"
    assert "sasl_password" not in data  # secret never returned


@pytest.mark.asyncio
async def test_create_kafka_config_with_sasl(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)

    async def mock_refresh(obj, **kw):
        obj.id = cfg.id
        obj.workspace_id = ws.id
        obj.enabled = True
        obj.event_types = obj.event_types or ["run.completed"]
        obj.sasl_mechanism = obj.sasl_mechanism
        obj.sasl_username = obj.sasl_username
        obj.ssl_ca_cert = None
        obj.created_at = cfg.created_at
        obj.updated_at = cfg.updated_at

    db.refresh.side_effect = mock_refresh

    resp = await client.post(
        "/integrations/kafka/configs",
        json={
            "bootstrap_servers": "broker:9093",
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "PLAIN",
            "sasl_username": "user",
            "sasl_password": "s3cret",
            "event_types": ["run.completed"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["security_protocol"] == "SASL_SSL"
    assert data["sasl_username"] == "user"
    assert "sasl_password" not in data


# ── GET /integrations/kafka/configs ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_kafka_configs(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [cfg]
    db.execute = AsyncMock(return_value=result_mock)

    resp = await client.get("/integrations/kafka/configs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["bootstrap_servers"] == "localhost:9092"


@pytest.mark.asyncio
async def test_list_kafka_configs_empty(authed_client):
    client, db, ws = authed_client

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    resp = await client.get("/integrations/kafka/configs")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


# ── PUT /integrations/kafka/configs/{id} ──────────────────────────────────────

@pytest.mark.asyncio
async def test_update_kafka_config(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = cfg

    async def mock_refresh(obj, **kw):
        # cfg is mutated in-place; just ensure required fields are set
        obj.workspace_id = ws.id

    db.execute = AsyncMock(return_value=result_mock)
    db.refresh.side_effect = mock_refresh

    resp = await client.put(
        f"/integrations/kafka/configs/{cfg.id}",
        json={"enabled": False, "label": "updated"},
    )
    assert resp.status_code == 200
    assert cfg.enabled is False
    assert cfg.label == "updated"


@pytest.mark.asyncio
async def test_update_kafka_config_not_found(authed_client):
    client, db, ws = authed_client

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    resp = await client.put(
        f"/integrations/kafka/configs/{uuid.uuid4()}",
        json={"enabled": False},
    )
    assert resp.status_code == 404


# ── DELETE /integrations/kafka/configs/{id} ───────────────────────────────────

@pytest.mark.asyncio
async def test_delete_kafka_config(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = cfg
    db.execute = AsyncMock(return_value=result_mock)

    resp = await client.delete(f"/integrations/kafka/configs/{cfg.id}")
    assert resp.status_code == 204
    db.delete.assert_called_once_with(cfg)


@pytest.mark.asyncio
async def test_delete_kafka_config_not_found(authed_client):
    client, db, ws = authed_client

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    resp = await client.delete(f"/integrations/kafka/configs/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── POST /integrations/kafka/configs/{id}/test ────────────────────────────────

@pytest.mark.asyncio
async def test_test_kafka_config_ok(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = cfg
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "runledger_api.services.kafka_export.test_connection",
        new=AsyncMock(return_value=(True, None)),
    ):
        resp = await client.post(f"/integrations/kafka/configs/{cfg.id}/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["topic"] == "runledger.runs"


@pytest.mark.asyncio
async def test_test_kafka_config_fail(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = cfg
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "runledger_api.services.kafka_export.test_connection",
        new=AsyncMock(return_value=(False, "Connection refused")),
    ):
        resp = await client.post(f"/integrations/kafka/configs/{cfg.id}/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "Connection refused" in data["error"]


# ── GET /integrations/kafka/configs/{id}/deliveries ───────────────────────────

@pytest.mark.asyncio
async def test_list_kafka_deliveries(authed_client):
    client, db, ws = authed_client
    cfg = _cfg(workspace_id=ws.id)
    d = _delivery(cfg.id)

    cfg_result = MagicMock()
    cfg_result.scalar_one_or_none.return_value = cfg
    del_result = MagicMock()
    del_result.scalars.return_value.all.return_value = [d]
    db.execute = AsyncMock(side_effect=[cfg_result, del_result])

    resp = await client.get(f"/integrations/kafka/configs/{cfg.id}/deliveries")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["event_type"] == "run.completed"
    assert items[0]["status"] == "success"


# ── Service: dispatch_to_kafka ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_skips_unsubscribed_event():
    """Config only subscribes to run.completed — alert.fired should be skipped."""
    from runledger_api.services.kafka_export import dispatch_to_kafka

    cfg = _cfg()
    cfg.event_types = ["run.completed"]  # does NOT include alert.fired

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [cfg]
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("runledger_api.services.kafka_export.AIOKafkaProducer", create=True):
        await dispatch_to_kafka(db, cfg.workspace_id, "alert.fired", {"event": "alert.fired"})

    # No delivery should be logged and commit is called with nothing added
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_no_configs():
    """No enabled configs → no producer created, commit still called."""
    from runledger_api.services.kafka_export import dispatch_to_kafka

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    # Should return early without error
    await dispatch_to_kafka(db, uuid.uuid4(), "run.completed", {})
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_records_failed_delivery():
    """Producer raises — delivery is logged as failed."""
    from runledger_api.services.kafka_export import dispatch_to_kafka

    cfg = _cfg()
    cfg.event_types = ["run.completed"]

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [cfg]
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()

    mock_producer = AsyncMock()
    mock_producer.start = AsyncMock()
    mock_producer.send_and_wait = AsyncMock(side_effect=Exception("broker down"))
    mock_producer.stop = AsyncMock()

    with patch("aiokafka.AIOKafkaProducer", return_value=mock_producer):
        await dispatch_to_kafka(db, cfg.workspace_id, "run.completed", {"run_id": "abc"})

    db.add.assert_called_once()
    delivery_arg = db.add.call_args[0][0]
    assert delivery_arg.status == "failed"
    assert "broker down" in delivery_arg.error_detail


# ── Topic routing ─────────────────────────────────────────────────────────────

def test_topic_routing():
    from runledger_api.services.kafka_export import _topic_for

    assert _topic_for("rl", "run.completed") == "rl.runs"
    assert _topic_for("rl", "run.failed") == "rl.runs"
    assert _topic_for("rl", "alert.fired") == "rl.alerts"
    assert _topic_for("rl", "budget.breached") == "rl.budgets"
    assert _topic_for("rl", "score.submitted") == "rl.scores"
    assert _topic_for("myapp", "unknown.event") == "myapp.events"
