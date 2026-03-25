"""
Tests for Phase 29 — SCIM 2.0 provisioning endpoints.

Covers:
  GET    /scim/v2/Users          — list users
  POST   /scim/v2/Users          — provision user
  GET    /scim/v2/Users/{id}     — get user
  PUT    /scim/v2/Users/{id}     — replace user
  PATCH  /scim/v2/Users/{id}    — partial update (deactivate)
  DELETE /scim/v2/Users/{id}    — deprovision user
  GET    /scim/v2/Users          — filter by userName
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from runledger_api.core.db import get_db
from runledger_api.core.redis import get_redis
from runledger_api.main import app

# ── Helpers ───────────────────────────────────────────────────────────────────

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
SCIM_RAW = "scim_thetesttoken123456789012345"
SCIM_HASH = hashlib.sha256(SCIM_RAW.encode()).hexdigest()


def _scalar_one_or_none(val):
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=val)
    return m


def _scalars_list(rows: list):
    m = MagicMock()
    sc = MagicMock()
    sc.all = MagicMock(return_value=rows)
    m.scalars = MagicMock(return_value=sc)
    return m


def _make_scim_token_obj() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        token_hash=SCIM_HASH,
        token_prefix="scim_thetest",
        label="test",
        enabled=True,
        last_used_at=None,
        expires_at=None,
        created_at=datetime.now(UTC),
    )


def _make_tenant() -> SimpleNamespace:
    return SimpleNamespace(id=TENANT_ID, name="Test Org", status=None)


def _make_user(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=USER_ID,
        email="alice@example.com",
        full_name="Alice Example",
        is_active=True,
        is_platform_admin=False,
        email_verified=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── SCIM auth fixture ─────────────────────────────────────────────────────────


@pytest.fixture
async def scim_client(mock_db_session: AsyncMock, mock_redis_client: AsyncMock):
    """Client that sends valid SCIM Bearer token; mocks out token + tenant lookup."""

    async def override_get_db():
        yield mock_db_session

    async def override_get_redis():
        return mock_redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    from httpx import ASGITransport  # noqa: PLC0415
    from httpx import AsyncClient as HClient

    async with HClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SCIM_RAW}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scim_list_users(scim_client: AsyncClient, mock_db_session: AsyncMock):
    user = _make_user()
    scim_tok = _make_scim_token_obj()
    tenant = _make_tenant()

    call_count = 0

    def _side(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _scalar_one_or_none(scim_tok)
        if call_count == 2:
            return _scalar_one_or_none(tenant)
        return _scalars_list([user])

    mock_db_session.execute = AsyncMock(side_effect=_side)
    mock_db_session.flush = AsyncMock()

    resp = await scim_client.get("/scim/v2/Users")
    assert resp.status_code == 200
    data = resp.json()
    assert data["totalResults"] == 1
    assert data["Resources"][0]["userName"] == "alice@example.com"


@pytest.mark.asyncio
async def test_scim_provision_new_user(scim_client: AsyncClient, mock_db_session: AsyncMock):
    scim_tok = _make_scim_token_obj()
    tenant = _make_tenant()
    workspace = SimpleNamespace(id=uuid.uuid4(), tenant_id=TENANT_ID, created_at=datetime.now(UTC))

    new_user = _make_user(email="bob@example.com", full_name="Bob Builder", id=uuid.uuid4())

    call_count = 0

    def _side(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _scalar_one_or_none(scim_tok)
        if call_count == 2:
            return _scalar_one_or_none(tenant)
        if call_count == 3:
            return _scalar_one_or_none(None)  # no existing user by email
        if call_count == 4:
            return _scalar_one_or_none(workspace)  # primary workspace
        return _scalar_one_or_none(new_user)

    mock_db_session.execute = AsyncMock(side_effect=_side)
    mock_db_session.flush = AsyncMock()
    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: (
            setattr(obj, "id", new_user.id)
            or setattr(obj, "full_name", new_user.full_name)
            or setattr(obj, "email", new_user.email)
            or setattr(obj, "is_active", new_user.is_active)
        )
    )

    resp = await scim_client.post(
        "/scim/v2/Users",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "bob@example.com",
            "name": {"givenName": "Bob", "familyName": "Builder"},
            "emails": [{"value": "bob@example.com", "type": "work", "primary": True}],
            "active": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["userName"] == "bob@example.com"


@pytest.mark.asyncio
async def test_scim_get_user(scim_client: AsyncClient, mock_db_session: AsyncMock):
    scim_tok = _make_scim_token_obj()
    tenant = _make_tenant()
    user = _make_user()

    call_count = 0

    def _side(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _scalar_one_or_none(scim_tok)
        if call_count == 2:
            return _scalar_one_or_none(tenant)
        return _scalar_one_or_none(user)

    mock_db_session.execute = AsyncMock(side_effect=_side)
    mock_db_session.flush = AsyncMock()

    resp = await scim_client.get(f"/scim/v2/Users/{USER_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(USER_ID)


@pytest.mark.asyncio
async def test_scim_get_user_not_found(scim_client: AsyncClient, mock_db_session: AsyncMock):
    scim_tok = _make_scim_token_obj()
    tenant = _make_tenant()

    call_count = 0

    def _side(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _scalar_one_or_none(scim_tok)
        if call_count == 2:
            return _scalar_one_or_none(tenant)
        return _scalar_one_or_none(None)

    mock_db_session.execute = AsyncMock(side_effect=_side)
    mock_db_session.flush = AsyncMock()

    resp = await scim_client.get(f"/scim/v2/Users/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scim_patch_deactivate(scim_client: AsyncClient, mock_db_session: AsyncMock):
    scim_tok = _make_scim_token_obj()
    tenant = _make_tenant()
    user = _make_user()

    call_count = 0

    def _side(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _scalar_one_or_none(scim_tok)
        if call_count == 2:
            return _scalar_one_or_none(tenant)
        return _scalar_one_or_none(user)

    mock_db_session.execute = AsyncMock(side_effect=_side)
    mock_db_session.flush = AsyncMock()
    mock_db_session.refresh = AsyncMock()

    resp = await scim_client.patch(
        f"/scim/v2/Users/{USER_ID}",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "value": {"active": False}}],
        },
    )
    assert resp.status_code == 200
    assert user.is_active is False


@pytest.mark.asyncio
async def test_scim_delete_user(scim_client: AsyncClient, mock_db_session: AsyncMock):
    scim_tok = _make_scim_token_obj()
    tenant = _make_tenant()
    user = _make_user()
    tu = SimpleNamespace(id=uuid.uuid4())

    call_count = 0

    def _side(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _scalar_one_or_none(scim_tok)
        if call_count == 2:
            return _scalar_one_or_none(tenant)
        if call_count == 3:
            return _scalar_one_or_none(user)
        return _scalar_one_or_none(tu)  # TenantUser

    mock_db_session.execute = AsyncMock(side_effect=_side)
    mock_db_session.flush = AsyncMock()
    mock_db_session.delete = AsyncMock()

    resp = await scim_client.delete(f"/scim/v2/Users/{USER_ID}")
    assert resp.status_code == 204
    assert user.is_active is False


@pytest.mark.asyncio
async def test_scim_no_auth(client: AsyncClient):
    resp = await client.get("/scim/v2/Users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_scim_invalid_username(scim_client: AsyncClient, mock_db_session: AsyncMock):
    scim_tok = _make_scim_token_obj()
    tenant = _make_tenant()

    call_count = 0

    def _side(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _scalar_one_or_none(scim_tok)
        return _scalar_one_or_none(tenant)

    mock_db_session.execute = AsyncMock(side_effect=_side)
    mock_db_session.flush = AsyncMock()

    resp = await scim_client.post(
        "/scim/v2/Users",
        json={
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "notanemail",
        },
    )
    assert resp.status_code == 422
