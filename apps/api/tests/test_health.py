from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.asyncio
async def test_health_db_error(
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    from httpx import ASGITransport, AsyncClient
    from runledger_api.core.db import get_db
    from runledger_api.core.redis import get_redis
    from runledger_api.main import app

    mock_db_session.execute.side_effect = Exception("connection refused")

    async def override_get_db():  # type: ignore[return]
        yield mock_db_session

    async def override_get_redis() -> AsyncMock:
        return mock_redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "error"
    assert data["redis"] == "ok"


@pytest.mark.asyncio
async def test_health_redis_error(
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    from httpx import ASGITransport, AsyncClient
    from runledger_api.core.db import get_db
    from runledger_api.core.redis import get_redis
    from runledger_api.main import app

    mock_redis_client.ping.side_effect = Exception("connection refused")

    async def override_get_db():  # type: ignore[return]
        yield mock_db_session

    async def override_get_redis() -> AsyncMock:
        return mock_redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "ok"
    assert data["redis"] == "error"
