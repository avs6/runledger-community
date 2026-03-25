"""
Tests for Phase 29 — SSO / OIDC + SCIM.

Covers:
  GET  /auth/sso/authorize/{config_id}  — returns authorization URL
  GET  /auth/sso/callback/{config_id}   — OIDC callback (error path)
  POST /auth/sso/exchange               — exchange SSO token
  GET  /sso/configs                     — list SSO configs
  POST /sso/configs                     — create SSO config
  GET  /sso/configs/{id}                — get config
  PUT  /sso/configs/{id}                — update config
  DELETE /sso/configs/{id}              — delete config
  GET  /sso/tokens                      — list SCIM tokens
  POST /sso/tokens                      — create SCIM token
  DELETE /sso/tokens/{id}               — delete SCIM token
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Helpers ───────────────────────────────────────────────────────────────────


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


TENANT_ID = uuid.uuid4()
CONFIG_ID = uuid.uuid4()
TOKEN_ID = uuid.uuid4()


def _make_sso_config(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=CONFIG_ID,
        tenant_id=TENANT_ID,
        provider="google",
        issuer_url="https://accounts.google.com",
        client_id="client_abc",
        client_secret_enc="b64:c2VjcmV0",
        scopes="openid email profile",
        default_role="member",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_scim_token(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=TOKEN_ID,
        tenant_id=TENANT_ID,
        token_hash="abc123",
        token_prefix="scim_abcdefg",
        label="SCIM provisioning",
        enabled=True,
        last_used_at=None,
        expires_at=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── SSO Config CRUD ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sso_configs_empty(authed_client: AsyncClient, mock_db_session: AsyncMock):
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([]))
    resp = await authed_client.get("/sso/configs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_sso_configs(authed_client: AsyncClient, mock_db_session: AsyncMock):
    cfg = _make_sso_config()
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([cfg]))
    resp = await authed_client.get("/sso/configs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["provider"] == "google"


@pytest.mark.asyncio
async def test_create_sso_config(authed_client: AsyncClient, mock_db_session: AsyncMock):
    # No existing config
    no_dup = _scalar_one_or_none(None)

    created = _make_sso_config()

    call_count = 0

    def _execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return no_dup
        return _scalar_one_or_none(created)

    mock_db_session.execute = AsyncMock(side_effect=_execute_side_effect)

    def _mock_refresh(obj):
        obj.id = created.id
        obj.created_at = created.created_at
        obj.updated_at = created.updated_at
        obj.tenant_id = created.tenant_id

    mock_db_session.refresh = AsyncMock(side_effect=_mock_refresh)

    resp = await authed_client.post(
        "/sso/configs",
        json={
            "provider": "google",
            "issuer_url": "https://accounts.google.com",
            "client_id": "client_abc",
            "client_secret": "secret_xyz",
            "scopes": "openid email profile",
            "default_role": "member",
            "enabled": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "google"
    assert data["issuer_url"] == "https://accounts.google.com"


@pytest.mark.asyncio
async def test_create_sso_config_duplicate(authed_client: AsyncClient, mock_db_session: AsyncMock):
    existing = _make_sso_config()
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(existing))
    resp = await authed_client.post(
        "/sso/configs",
        json={
            "provider": "google",
            "issuer_url": "https://accounts.google.com",
            "client_id": "c",
            "client_secret": "s",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_sso_config(authed_client: AsyncClient, mock_db_session: AsyncMock):
    cfg = _make_sso_config()
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))
    resp = await authed_client.get(f"/sso/configs/{CONFIG_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(CONFIG_ID)


@pytest.mark.asyncio
async def test_get_sso_config_not_found(authed_client: AsyncClient, mock_db_session: AsyncMock):
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.get(f"/sso/configs/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_sso_config(authed_client: AsyncClient, mock_db_session: AsyncMock):
    cfg = _make_sso_config()
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))
    mock_db_session.refresh = AsyncMock(side_effect=lambda obj: None)
    resp = await authed_client.put(f"/sso/configs/{CONFIG_ID}", json={"enabled": False})
    assert resp.status_code == 200
    # enabled was mutated on the SimpleNamespace
    assert cfg.enabled is False


@pytest.mark.asyncio
async def test_delete_sso_config(authed_client: AsyncClient, mock_db_session: AsyncMock):
    cfg = _make_sso_config()
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))
    mock_db_session.delete = AsyncMock()
    resp = await authed_client.delete(f"/sso/configs/{CONFIG_ID}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(cfg)


# ── SCIM Token CRUD ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_scim_tokens_empty(authed_client: AsyncClient, mock_db_session: AsyncMock):
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([]))
    resp = await authed_client.get("/sso/tokens")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_create_scim_token(authed_client: AsyncClient, mock_db_session: AsyncMock):
    tok = _make_scim_token()

    def _refresh(obj):
        obj.id = tok.id
        obj.created_at = tok.created_at
        obj.tenant_id = tok.tenant_id
        obj.token_prefix = tok.token_prefix
        obj.label = tok.label
        obj.enabled = tok.enabled
        obj.last_used_at = tok.last_used_at
        obj.expires_at = tok.expires_at

    mock_db_session.refresh = AsyncMock(side_effect=_refresh)

    resp = await authed_client.post("/sso/tokens", json={"label": "My SCIM token"})
    assert resp.status_code == 201
    data = resp.json()
    assert "raw_token" in data
    assert data["raw_token"].startswith("scim_")


@pytest.mark.asyncio
async def test_delete_scim_token(authed_client: AsyncClient, mock_db_session: AsyncMock):
    tok = _make_scim_token()
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(tok))
    mock_db_session.delete = AsyncMock()
    resp = await authed_client.delete(f"/sso/tokens/{TOKEN_ID}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(tok)


@pytest.mark.asyncio
async def test_delete_scim_token_not_found(authed_client: AsyncClient, mock_db_session: AsyncMock):
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.delete(f"/sso/tokens/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── OIDC authorize ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sso_authorize(authed_client: AsyncClient, mock_db_session: AsyncMock):
    cfg = _make_sso_config()
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(cfg))

    discovery_doc = {
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
    }

    with patch(
        "runledger_api.routers.sso.discover_oidc",
        new_callable=AsyncMock,
        return_value=discovery_doc,
    ):
        resp = await authed_client.get(f"/auth/sso/authorize/{CONFIG_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert "authorization_url" in data
    assert "accounts.google.com" in data["authorization_url"]
    assert "response_type=code" in data["authorization_url"]


@pytest.mark.asyncio
async def test_sso_authorize_not_found(authed_client: AsyncClient, mock_db_session: AsyncMock):
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    with patch("runledger_api.routers.sso.discover_oidc", new_callable=AsyncMock):
        resp = await authed_client.get(f"/auth/sso/authorize/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── OIDC callback error path ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sso_callback_error_param(client: AsyncClient):
    resp = await client.get(
        f"/auth/sso/callback/{CONFIG_ID}?error=access_denied", follow_redirects=False
    )
    assert resp.status_code in (302, 307)
    assert "error=access_denied" in resp.headers["location"]


@pytest.mark.asyncio
async def test_sso_callback_missing_params(client: AsyncClient):
    resp = await client.get(f"/auth/sso/callback/{CONFIG_ID}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "error=missing_params" in resp.headers["location"]


# ── SSO exchange ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sso_exchange_invalid_token(client: AsyncClient):
    with patch(
        "runledger_api.routers.sso._pop_sso_token", new_callable=AsyncMock, return_value=None
    ):
        resp = await client.post("/auth/sso/exchange", json={"token": "bad_token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sso_exchange_valid(client: AsyncClient):
    from runledger_api.schemas.runs import LoginResponse  # noqa: PLC0415

    fake_resp = LoginResponse(
        email="test@example.com",
        full_name="Test User",
        user_id=str(uuid.uuid4()),
        workspace_id=str(uuid.uuid4()),
        workspace_name="Test Workspace",
        tenant_id=str(uuid.uuid4()),
        api_key="rl_dev_test",
        is_platform_admin=False,
        tenant_role="org_member",
        workspace_role="member",
        workspace_ids=[],
    )

    with patch(
        "runledger_api.routers.sso._pop_sso_token", new_callable=AsyncMock, return_value=fake_resp
    ):
        resp = await client.post("/auth/sso/exchange", json={"token": "sso_goodtoken"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["api_key"] == "rl_dev_test"
