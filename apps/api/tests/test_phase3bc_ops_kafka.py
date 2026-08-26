from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _result(rows):
    result = MagicMock()
    result.scalars.return_value = MagicMock(all=MagicMock(return_value=rows))
    result.scalar_one.return_value = len(rows)
    return result


def _backup_run(**overrides: object) -> SimpleNamespace:
    now = datetime.now(UTC)
    defaults = {
        "id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "trigger_mode": "manual",
        "status": "queued",
        "backup_scope": "full",
        "target": "localai-s3://runledger-backups",
        "command": "python scripts/localai/localai_s3_backup.py backup",
        "triggered_by": "ops@example.com",
        "size_bytes": None,
        "checksum": None,
        "output_excerpt": None,
        "error_detail": None,
        "details": None,
        "started_at": now,
        "completed_at": None,
        "created_at": now,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_kafka_envelope_has_stable_idempotency_key() -> None:
    from runledger_api.services.kafka_export import envelope

    workspace_id = uuid.uuid4()
    payload = {"run_id": "run_123", "trace_id": "trace_123", "cost_usd": "1.23"}

    first = envelope(workspace_id=workspace_id, event_type="run.completed", payload=payload)
    second = envelope(workspace_id=workspace_id, event_type="run.completed", payload=payload)

    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["event_id"] != second["event_id"]


def test_kafka_event_topic_supports_single_topic_mode() -> None:
    from runledger_api.services.kafka_export import event_topic

    config = SimpleNamespace(
        single_topic_mode=True,
        single_topic_name="runledger.events",
        topic_prefix="runledger.dev",
    )
    assert event_topic(config, "alert.fired") == "runledger.events"


def test_kafka_prepare_event_payload_supports_metadata_only_redaction() -> None:
    from runledger_api.services.kafka_export import prepare_event_payload

    config = SimpleNamespace(redaction_mode="metadata_only")
    payload = {
        "run_id": "run_123",
        "trace_id": "trace_123",
        "source": "runledger.tests",
        "status": "failed",
        "prompt": "secret prompt",
    }

    prepared = prepare_event_payload(config, payload)

    assert prepared == {
        "run_id": "run_123",
        "trace_id": "trace_123",
        "source": "runledger.tests",
        "status": "failed",
    }


def test_kafka_prepare_event_payload_redacts_sensitive_keys_recursively() -> None:
    from runledger_api.services.kafka_export import prepare_event_payload

    config = SimpleNamespace(redaction_mode="none")
    payload = {
        "prompt": "top secret",
        "nested": {"content": "hide me", "ok": "keep me"},
        "items": [{"arguments": {"x": 1}}, {"safe": True}],
    }

    prepared = prepare_event_payload(config, payload)

    assert prepared["prompt"] == "[redacted]"
    assert prepared["nested"]["content"] == "[redacted]"
    assert prepared["nested"]["ok"] == "keep me"
    assert prepared["items"][0]["arguments"] == "[redacted]"


def test_backup_run_defaults_include_checksum_fields() -> None:
    run = _backup_run(size_bytes=123, checksum="abc123")
    assert run.size_bytes == 123
    assert run.checksum == "abc123"


@pytest.mark.asyncio
async def test_get_backup_history_returns_items() -> None:
    from runledger_api.routers.settings import get_backup_history

    workspace_id = uuid.uuid4()
    workspace = SimpleNamespace(id=workspace_id)
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([_backup_run(workspace_id=workspace_id, status="success")]),
            MagicMock(scalar_one=MagicMock(return_value=1)),
        ]
    )

    result = await get_backup_history(auth=(workspace, None), db=db, limit=20)  # type: ignore[arg-type]

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].status == "success"


@pytest.mark.asyncio
async def test_run_backup_now_requires_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException
    from runledger_api.routers import settings as settings_router

    monkeypatch.setattr(settings_router.app_settings, "backup_enabled", False)

    with pytest.raises(HTTPException) as exc_info:
        await settings_router.run_backup_now(
            auth=(SimpleNamespace(id=uuid.uuid4()), None), db=AsyncMock()
        )  # type: ignore[arg-type]

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_run_backup_now_queues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    from runledger_api.routers import settings as settings_router

    workspace = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(email="ops@example.com")
    queued = _backup_run(workspace_id=workspace.id, triggered_by=user.email)

    monkeypatch.setattr(settings_router.app_settings, "backup_enabled", True)
    with patch(
        "runledger_api.routers.settings.backup_ops.queue_backup_run",
        new=AsyncMock(return_value=queued),
    ) as mock_queue:
        result = await settings_router.run_backup_now(auth=(workspace, user), db=AsyncMock())  # type: ignore[arg-type]

    mock_queue.assert_awaited_once()
    assert str(result.workspace_id) == str(workspace.id)
    assert result.triggered_by == "ops@example.com"
