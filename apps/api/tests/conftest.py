from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

# Run all tests with a synthetic unlimited enterprise license so feature-gated
# endpoints are accessible.  We inject directly into the module-level cache
# rather than relying on RUNLEDGER_MODE so the license system is exercised.
from runledger_api.core import license as _license_module  # noqa: E402
from runledger_api.core.db import get_db

_license_module._license_cache = _license_module._legacy_enterprise_license()
from runledger_api.core.deps import (  # noqa: E402
    get_current_workspace,
    require_member,
    require_org_admin,
    require_workspace_admin,
)
from runledger_api.core.redis import get_redis  # noqa: E402
from runledger_api.main import app  # noqa: E402

# ── License fixtures for feature-gate tests ────────────────────────────────────


@pytest.fixture
def oss_license(monkeypatch: pytest.MonkeyPatch) -> _license_module.ParsedLicense:
    """Override the license cache with a community (OSS) license for gate tests."""
    community = _license_module._community_license()
    monkeypatch.setattr(_license_module, "_license_cache", community)
    return community


@pytest.fixture
def expired_license(monkeypatch: pytest.MonkeyPatch) -> _license_module.ParsedLicense:
    """Override the license cache with a hard-expired enterprise license (20 days past)."""
    expired = _license_module._make_test_license(edition="enterprise", expires_offset_days=-20)
    monkeypatch.setattr(_license_module, "_license_cache", expired)
    return expired


@pytest.fixture
def grace_period_license(monkeypatch: pytest.MonkeyPatch) -> _license_module.ParsedLicense:
    """Override the license cache with a license 7 days past expiry (within grace period)."""
    grace = _license_module._make_test_license(edition="enterprise", expires_offset_days=-7)
    monkeypatch.setattr(_license_module, "_license_cache", grace)
    return grace


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

    async def override_get_db() -> AsyncGenerator[AsyncMock]:
        yield mock_db_session

    async def override_get_redis() -> AsyncMock:
        return mock_redis_client

    async def override_get_workspace() -> SimpleNamespace:
        return mock_workspace

    async def override_require_workspace_admin() -> tuple:
        return (mock_workspace, None, None)

    async def override_require_member() -> tuple:
        return (mock_workspace, None, None)

    async def override_require_org_admin() -> tuple:
        return (mock_workspace, None, None)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_current_workspace] = override_get_workspace
    app.dependency_overrides[require_workspace_admin] = override_require_workspace_admin
    app.dependency_overrides[require_member] = override_require_member
    app.dependency_overrides[require_org_admin] = override_require_org_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
