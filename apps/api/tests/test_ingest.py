"""Tests for the ingest API endpoints."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
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
async def test_unsigned_ingest_webhook_is_removed(
    client: AsyncClient,
    mock_workspace: SimpleNamespace,
) -> None:
    """An unauthenticated endpoint that let anyone write into any workspace by UUID."""
    payload = {"workspace_id": str(mock_workspace.id), "events": []}
    response = await client.post("/ingest/v1/webhook", json=payload)
    assert response.status_code in (404, 405)


class _NonceRedis:
    def __init__(self) -> None:
        self.keys: set[str] = set()

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.keys:
            return False
        self.keys.add(key)
        return True


async def _post_signed(
    client: AsyncClient,
    workspace: SimpleNamespace,
    *,
    nonce: str = "n-1",
    secret_version: int = 1,
    tamper: bool = False,
) -> Any:
    from runledger_api.services.ingest_signing import sign, workspace_signing_secret

    payload = {
        "workspace_id": str(workspace.id),
        "events": [
            {
                "event_type": "run_start",
                "run_id": str(uuid.uuid4()),
                "started_at": datetime.now(UTC).isoformat(),
                "api_key_id": str(uuid.uuid4()),  # client claim; must be stripped
            }
        ],
    }
    raw_body = json.dumps(payload).encode()
    timestamp = datetime.now(UTC).isoformat()
    secret = workspace_signing_secret(workspace.id, secret_version)
    signature = sign(secret, workspace.id, timestamp, nonce, raw_body)
    if tamper:
        raw_body = raw_body + b" "  # still valid JSON, but not what was signed
    return await client.post(
        "/ingest/v1/signed",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-RunLedger-Timestamp": timestamp,
            "X-RunLedger-Signature": signature,
            "X-RunLedger-Nonce": nonce,
        },
    )


@pytest.fixture
def signed_setup(
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> _NonceRedis:
    from runledger_api.core.redis import get_redis
    from runledger_api.main import app

    monkeypatch.setattr(settings, "ingest_signing_secret", "phase1a-secret")
    monkeypatch.setattr(
        "runledger_api.routers.ingest.validate_workspace_status",
        AsyncMock(return_value=mock_workspace),
    )
    mock_workspace.ingest_signing_version = 1
    mock_db_session.get = AsyncMock(return_value=mock_workspace)
    redis = _NonceRedis()

    async def _redis() -> _NonceRedis:
        return redis

    app.dependency_overrides[get_redis] = _redis
    return redis


@pytest.mark.asyncio
async def test_ingest_signed_accepts_valid_signature(
    client: AsyncClient, mock_workspace: SimpleNamespace, signed_setup: _NonceRedis
) -> None:
    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        response = await _post_signed(client, mock_workspace)

    assert response.status_code == 202
    assert response.json() == {"accepted": 1}
    events = mock_task.delay.call_args.kwargs["events"]
    assert events[0]["api_key_id"] is None  # unauthenticated sender cannot claim a key


@pytest.mark.asyncio
async def test_ingest_signed_rejects_replayed_nonce(
    client: AsyncClient, mock_workspace: SimpleNamespace, signed_setup: _NonceRedis
) -> None:
    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        first = await _post_signed(client, mock_workspace, nonce="same")
        second = await _post_signed(client, mock_workspace, nonce="same")
    assert first.status_code == 202
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_ingest_signed_rejects_bad_or_rotated_signature(
    client: AsyncClient, mock_workspace: SimpleNamespace, signed_setup: _NonceRedis
) -> None:
    with patch("runledger_api.routers.ingest.process_events_task"):
        tampered = await _post_signed(client, mock_workspace, nonce="a", tamper=True)
        mock_workspace.ingest_signing_version = 2  # rotated: version-1 secret is dead
        stale = await _post_signed(client, mock_workspace, nonce="b", secret_version=1)
    assert tampered.status_code == 401
    assert stale.status_code == 401


def test_workspace_signing_secrets_differ_and_ignore_admin_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runledger_api.services.ingest_signing import workspace_signing_secret

    monkeypatch.setattr(settings, "ingest_signing_secret", "")
    a = workspace_signing_secret("ws-a", 1)
    assert a != workspace_signing_secret("ws-b", 1)
    assert a != workspace_signing_secret("ws-a", 2)
    monkeypatch.setattr(settings, "admin_secret", "changed-admin-secret")
    assert workspace_signing_secret("ws-a", 1) == a


def test_ingest_events_are_attributed_to_the_sending_key() -> None:
    from runledger_api.routers.ingest import attribute_to_sending_key

    key_id = uuid.uuid4()
    request = SimpleNamespace(state=SimpleNamespace(api_key=SimpleNamespace(id=key_id)))
    events = [
        {"event_type": "run_start", "run_id": "r"},
        # A client cannot claim another key's id.
        {"event_type": "provider_call", "run_id": "r", "api_key_id": str(uuid.uuid4())},
        {"event_type": "span_start", "run_id": "r"},
    ]
    out = attribute_to_sending_key(request, events)  # type: ignore[arg-type]
    assert out[0]["api_key_id"] == str(key_id)
    assert out[1]["api_key_id"] == str(key_id)
    assert "api_key_id" not in out[2]

    oidc = SimpleNamespace(state=SimpleNamespace(api_key=None))
    assert attribute_to_sending_key(oidc, [{"event_type": "run_start"}])[0]["api_key_id"] is None  # type: ignore[arg-type]
