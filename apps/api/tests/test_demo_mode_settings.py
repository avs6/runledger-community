from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_platform_admin
from runledger_api.core.redis import get_redis
from runledger_api.main import app


@pytest.fixture(autouse=True)
def _setup_redis(mock_redis_client: AsyncMock) -> None:
    mock_redis_client.incr = AsyncMock(return_value=1)
    mock_redis_client.expire = AsyncMock(return_value=True)
    mock_redis_client.ttl = AsyncMock(return_value=60)


@pytest.fixture
async def platform_authed_client(
    mock_workspace,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> AsyncGenerator[AsyncClient]:
    async def override_get_db():
        yield mock_db_session

    async def override_get_redis():
        return mock_redis_client

    async def override_get_workspace():
        return mock_workspace

    async def override_require_platform_admin():
        return (mock_workspace, None, None)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_current_workspace] = override_get_workspace
    app.dependency_overrides[require_platform_admin] = override_require_platform_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_demo_status(
    platform_authed_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "runledger_api.routers.settings.read_demo_state",
        lambda: {
            "status": "idle",
            "action": None,
            "profile": "full",
            "message": "Demo mode has not been run yet.",
            "pid": None,
            "started_at": None,
            "finished_at": None,
            "updated_at": "2026-08-06T12:00:00Z",
            "runbook_path": "C:/demo-runbook.md",
            "available_profiles": [],
        },
    )

    resp = await platform_authed_client.get("/settings/demo-status")

    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


@pytest.mark.asyncio
async def test_trigger_demo_seed(
    platform_authed_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "runledger_api.routers.settings.launch_demo_process",
        lambda action, profile="full": {
            "status": "started",
            "message": f"Demo {profile} {action} started in background",
            "state": {
                "status": "queued",
                "action": action,
                "profile": profile,
                "message": "Demo task queued.",
                "pid": 12345,
                "started_at": "2026-08-06T12:00:00Z",
                "finished_at": None,
                "updated_at": "2026-08-06T12:00:00Z",
                "runbook_path": "C:/demo-runbook.md",
                "available_profiles": [],
            },
        },
    )

    resp = await platform_authed_client.post("/settings/demo-seed")

    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    assert resp.json()["state"]["action"] == "seed"


@pytest.mark.asyncio
async def test_trigger_demo_reset(
    platform_authed_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "runledger_api.routers.settings.launch_demo_process",
        lambda action, profile="full": {
            "status": "started",
            "message": f"Demo {profile} {action} started in background",
            "state": {
                "status": "queued",
                "action": action,
                "profile": profile,
                "message": "Demo task queued.",
                "pid": 12345,
                "started_at": "2026-08-06T12:00:00Z",
                "finished_at": None,
                "updated_at": "2026-08-06T12:00:00Z",
                "runbook_path": "C:/demo-runbook.md",
                "available_profiles": [],
            },
        },
    )

    resp = await platform_authed_client.post("/settings/demo-reset")

    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    assert resp.json()["state"]["action"] == "reset"
