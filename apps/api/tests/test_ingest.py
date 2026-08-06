"""Tests for the ingest API endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from runledger_api.core.config import settings
from runledger_api.models.events import RunStatusEnum


@pytest.mark.asyncio
async def test_ingest_single_event_accepted(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    run_id = str(uuid.uuid4())
    # quota check returns None (no quota row → fail open)
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_db_session.commit = AsyncMock()
    payload = {
        "event_type": "run_start",
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
    }
    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        response = await authed_client.post("/ingest/v1/events", json=payload)

    assert response.status_code == 202
    assert response.json() == {"accepted": 1}
    mock_task.delay.assert_called_once()
    call_kwargs = mock_task.delay.call_args.kwargs
    assert call_kwargs["events"][0]["event_type"] == "run_start"
    assert call_kwargs["events"][0]["run_id"] == run_id


@pytest.mark.asyncio
async def test_ingest_batch_accepted(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    run_id = str(uuid.uuid4())
    # quota check returns None (no quota row → fail open)
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_db_session.commit = AsyncMock()
    payload = {
        "events": [
            {
                "event_type": "run_start",
                "run_id": run_id,
                "started_at": datetime.now(UTC).isoformat(),
            },
            {
                "event_type": "run_end",
                "run_id": run_id,
                "status": "succeeded",
                "ended_at": datetime.now(UTC).isoformat(),
            },
        ]
    }
    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        response = await authed_client.post("/ingest/v1/batch", json=payload)

    assert response.status_code == 202
    assert response.json() == {"accepted": 2}
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_empty_batch(authed_client: AsyncClient) -> None:
    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        response = await authed_client.post("/ingest/v1/batch", json={"events": []})

    assert response.status_code == 202
    assert response.json() == {"accepted": 0}
    mock_task.delay.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_requires_auth(client: AsyncClient) -> None:
    """Without an Authorization header, the endpoint must reject the request."""
    response = await client.post(
        "/ingest/v1/events",
        json={
            "event_type": "run_start",
            "run_id": str(uuid.uuid4()),
            "started_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_ingest_invalid_event_type(authed_client: AsyncClient) -> None:
    response = await authed_client.post(
        "/ingest/v1/events",
        json={"event_type": "not_a_real_event"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_runs(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    run_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    mock_run = SimpleNamespace(
        id=run_id,
        workspace_id=workspace_id,
        application_id=None,
        end_user_id=None,
        session_id=None,
        feature_tag=None,
        deployment_version=None,
        status=RunStatusEnum.succeeded,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        total_cost_usd=None,
        total_input_tokens=None,
        total_output_tokens=None,
    )

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_run]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock
    mock_db_session.execute = AsyncMock(return_value=execute_result)

    response = await authed_client.get("/ingest/v1/runs")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(run_id)
    assert data[0]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_ingest_webhook_accepts_workspace_payload(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    run_id = str(uuid.uuid4())
    mock_db_session.get = AsyncMock(return_value=mock_workspace)
    payload = {
        "workspace_id": str(mock_workspace.id),
        "events": [
            {
                "event_type": "run_start",
                "run_id": run_id,
                "started_at": datetime.now(UTC).isoformat(),
            }
        ],
    }
    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        response = await client.post("/ingest/v1/webhook", json=payload)

    assert response.status_code == 202
    assert response.json() == {"accepted": 1}
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_signed_accepts_valid_signature(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ingest_signing_secret", "phase1a-secret")
    mock_db_session.get = AsyncMock(return_value=mock_workspace)
    payload = {
        "workspace_id": str(mock_workspace.id),
        "events": [
            {
                "event_type": "run_start",
                "run_id": str(uuid.uuid4()),
                "started_at": datetime.now(UTC).isoformat(),
            }
        ],
    }
    raw_body = json.dumps(payload).encode()
    timestamp = datetime.now(UTC).isoformat()
    signature = hmac.new(
        settings.effective_ingest_signing_secret.encode(),
        b".".join([str(mock_workspace.id).encode(), timestamp.encode(), raw_body]),
        hashlib.sha256,
    ).hexdigest()
    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        response = await client.post(
            "/ingest/v1/signed",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-RunLedger-Timestamp": timestamp,
                "X-RunLedger-Signature": signature,
            },
        )

    assert response.status_code == 202
    assert response.json() == {"accepted": 1}
    mock_task.delay.assert_called_once()
