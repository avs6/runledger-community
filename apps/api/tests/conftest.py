from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_workspace,
    require_member,
    require_org_admin,
    require_workspace_admin,
)
from runledger_api.core.redis import get_redis
from runledger_api.main import app

# ── DB / Redis mocks ───────────────────────────────────────────────────────────


@pytest.fixture
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    # Return a proper MagicMock so callers can use .scalar_one_or_none() etc.
    _default_result = MagicMock()
    _default_result.scalar_one_or_none.return_value = None
    _default_result.scalar.return_value = None
    _default_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=_default_result)
    # session.add() is synchronous in SQLAlchemy — avoid unawaited-coroutine warnings
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=60)
    return redis


@pytest.fixture
def mock_workspace() -> SimpleNamespace:
    """A minimal namespace object acting as a Workspace for dependency overrides."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="test-workspace",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
async def client(
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> AsyncGenerator[AsyncClient]:
    """HTTP test client with DB and Redis dependencies mocked."""

    async def override_get_db() -> AsyncGenerator[AsyncMock]:
        yield mock_db_session

    async def override_get_redis() -> AsyncMock:
        return mock_redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def authed_client(
    mock_workspace: SimpleNamespace,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> AsyncGenerator[AsyncClient]:
    """HTTP test client with workspace auth bypassed."""
    mock_user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Test Admin",
    )

    async def override_get_db() -> AsyncGenerator[AsyncMock]:
        yield mock_db_session

    async def override_get_redis() -> AsyncMock:
        return mock_redis_client

    async def override_get_workspace() -> SimpleNamespace:
        return mock_workspace

    async def override_require_workspace_admin() -> tuple:
        return (mock_workspace, mock_user, SimpleNamespace(workspace_id=mock_workspace.id))

    async def override_require_member() -> tuple:
        return (mock_workspace, mock_user, None)

    async def override_require_org_admin() -> tuple:
        return (mock_workspace, mock_user, None)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_current_workspace] = override_get_workspace
    app.dependency_overrides[require_workspace_admin] = override_require_workspace_admin
    app.dependency_overrides[require_member] = override_require_member
    app.dependency_overrides[require_org_admin] = override_require_org_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
