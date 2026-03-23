"""
Tests for Phase 27 — Data Retention & Deletion Policy APIs.

Covers:
  - RetentionPolicyCreate schema validation
  - CRUD endpoints (create, list, get, update, delete)
  - POST /retention/purge — dry_run and live for each resource type
  - End-user erasure (GDPR scope)
  - purge_resource() service function
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Fixtures & helpers ────────────────────────────────────────────────────────


def _make_ws(ws_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=ws_id or uuid.uuid4())


def _make_policy(
    workspace_id: uuid.UUID | None = None,
    resource_type: str = "runs",
    action: str = "delete",
    scope: str = "workspace",
    scope_value: str | None = None,
    max_age_days: int | None = 90,
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        resource_type=resource_type,
        action=action,
        scope=scope,
        scope_value=scope_value,
        max_age_days=max_age_days,
        is_active=is_active,
        created_at=datetime.now(UTC),
        last_run_at=None,
        last_purged_count=None,
    )


def _scalar_result(value: object) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = value
    r.scalars.return_value.all.return_value = [value] if value is not None else []
    return r


def _rowcount_result(n: int) -> MagicMock:
    r = MagicMock()
    r.rowcount = n
    r.scalar.return_value = n
    return r


# ── Schema validation ─────────────────────────────────────────────────────────


def test_create_policy_workspace_scope_valid() -> None:
    from runledger_api.schemas.retention import RetentionPolicyCreate
    p = RetentionPolicyCreate(resource_type="runs", action="delete", max_age_days=90)
    assert p.scope == "workspace"
    assert p.max_age_days == 90


def test_create_policy_end_user_scope_valid() -> None:
    from runledger_api.schemas.retention import RetentionPolicyCreate
    p = RetentionPolicyCreate(
        resource_type="runs", action="delete", scope="end_user", scope_value="u123"
    )
    assert p.scope == "end_user"
    assert p.scope_value == "u123"
    assert p.max_age_days is None


def test_create_policy_workspace_scope_no_age_fails() -> None:
    from pydantic import ValidationError
    from runledger_api.schemas.retention import RetentionPolicyCreate
    with pytest.raises(ValidationError, match="max_age_days"):
        RetentionPolicyCreate(resource_type="runs", action="delete", scope="workspace")


def test_create_policy_end_user_no_scope_value_fails() -> None:
    from pydantic import ValidationError
    from runledger_api.schemas.retention import RetentionPolicyCreate
    with pytest.raises(ValidationError, match="scope_value"):
        RetentionPolicyCreate(resource_type="runs", action="delete", scope="end_user")


def test_create_policy_scrub_invalid_resource_fails() -> None:
    from pydantic import ValidationError
    from runledger_api.schemas.retention import RetentionPolicyCreate
    with pytest.raises(ValidationError, match="scrub"):
        RetentionPolicyCreate(resource_type="runs", action="scrub", max_age_days=30)


def test_create_policy_scrub_payloads_valid() -> None:
    from runledger_api.schemas.retention import RetentionPolicyCreate
    p = RetentionPolicyCreate(resource_type="payloads", action="scrub", max_age_days=30)
    assert p.action == "scrub"


# ── POST /retention/policies ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_retention_policy() -> None:
    from runledger_api.routers.retention import create_retention_policy
    from runledger_api.schemas.retention import RetentionPolicyCreate, RetentionPolicyResponse

    ws_id = uuid.uuid4()
    policy = _make_policy(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", policy.id) or
                                 setattr(obj, "created_at", policy.created_at) or
                                 setattr(obj, "last_run_at", None) or
                                 setattr(obj, "last_purged_count", None))

    ws = _make_ws(ws_id)
    body = RetentionPolicyCreate(resource_type="runs", action="delete", max_age_days=90)

    with patch("runledger_api.routers.retention.emit_audit_event", new_callable=AsyncMock):
        result = await create_retention_policy(body=body, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert isinstance(result, RetentionPolicyResponse)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


# ── GET /retention/policies ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_retention_policies() -> None:
    from runledger_api.routers.retention import list_retention_policies
    from runledger_api.schemas.retention import RetentionPolicyList

    ws_id = uuid.uuid4()
    policy = _make_policy(workspace_id=ws_id)

    mock_db = AsyncMock()
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [policy]
    mock_db.execute = AsyncMock(return_value=items_result)

    ws = _make_ws(ws_id)
    result = await list_retention_policies(auth=(ws, None), db=mock_db, resource_type=None, include_inactive=False)  # type: ignore[arg-type]

    assert isinstance(result, RetentionPolicyList)
    assert result.total == 1
    assert result.items[0].resource_type == "runs"


@pytest.mark.asyncio
async def test_list_retention_policies_empty() -> None:
    from runledger_api.routers.retention import list_retention_policies
    from runledger_api.schemas.retention import RetentionPolicyList

    mock_db = AsyncMock()
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=items_result)

    ws = _make_ws()
    result = await list_retention_policies(auth=(ws, None), db=mock_db, resource_type=None, include_inactive=False)  # type: ignore[arg-type]

    assert isinstance(result, RetentionPolicyList)
    assert result.total == 0


# ── GET /retention/policies/{id} ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_retention_policy_found() -> None:
    from runledger_api.routers.retention import get_retention_policy
    from runledger_api.schemas.retention import RetentionPolicyResponse

    ws_id = uuid.uuid4()
    policy = _make_policy(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(policy))

    ws = _make_ws(ws_id)
    result = await get_retention_policy(policy_id=policy.id, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert isinstance(result, RetentionPolicyResponse)
    assert result.resource_type == "runs"


@pytest.mark.asyncio
async def test_get_retention_policy_not_found() -> None:
    from fastapi import HTTPException
    from runledger_api.routers.retention import get_retention_policy

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(None))

    ws = _make_ws()
    with pytest.raises(HTTPException) as exc_info:
        await get_retention_policy(policy_id=uuid.uuid4(), auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 404


# ── PUT /retention/policies/{id} ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_retention_policy() -> None:
    from runledger_api.routers.retention import update_retention_policy
    from runledger_api.schemas.retention import RetentionPolicyResponse, RetentionPolicyUpdate

    ws_id = uuid.uuid4()
    policy = _make_policy(workspace_id=ws_id, max_age_days=90, is_active=True)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(policy))
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    ws = _make_ws(ws_id)
    body = RetentionPolicyUpdate(is_active=False)

    with patch("runledger_api.routers.retention.emit_audit_event", new_callable=AsyncMock):
        result = await update_retention_policy(
            policy_id=policy.id, body=body, auth=(ws, None), db=mock_db  # type: ignore[arg-type]
        )

    assert isinstance(result, RetentionPolicyResponse)
    assert policy.is_active is False  # mutated by handler


# ── DELETE /retention/policies/{id} ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_retention_policy() -> None:
    from runledger_api.routers.retention import delete_retention_policy

    ws_id = uuid.uuid4()
    policy = _make_policy(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(policy))
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    ws = _make_ws(ws_id)

    with patch("runledger_api.routers.retention.emit_audit_event", new_callable=AsyncMock):
        await delete_retention_policy(policy_id=policy.id, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    mock_db.delete.assert_awaited_once_with(policy)
    mock_db.commit.assert_awaited()


# ── POST /retention/purge — purge service ────────────────────────────────────


@pytest.mark.asyncio
async def test_purge_runs_dry_run() -> None:
    from runledger_api.services.retention import purge_resource

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 7
    mock_db.execute = AsyncMock(return_value=count_result)

    ws_id = uuid.uuid4()
    count, cutoff = await purge_resource(
        mock_db,
        workspace_id=ws_id,
        resource_type="runs",
        action="delete",
        max_age_days=30,
        dry_run=True,
    )

    assert count == 7
    assert cutoff is not None
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_purge_runs_live() -> None:
    from runledger_api.services.retention import purge_resource

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_rowcount_result(5))

    ws_id = uuid.uuid4()
    count, cutoff = await purge_resource(
        mock_db,
        workspace_id=ws_id,
        resource_type="runs",
        action="delete",
        max_age_days=90,
        dry_run=False,
    )

    assert count == 5
    assert cutoff is not None


@pytest.mark.asyncio
async def test_purge_provider_calls() -> None:
    from runledger_api.services.retention import purge_resource

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_rowcount_result(12))

    ws_id = uuid.uuid4()
    count, cutoff = await purge_resource(
        mock_db,
        workspace_id=ws_id,
        resource_type="provider_calls",
        action="delete",
        max_age_days=60,
        dry_run=False,
    )

    assert count == 12
    assert cutoff is not None


@pytest.mark.asyncio
async def test_purge_payload_scrub() -> None:
    from runledger_api.services.retention import purge_resource

    mock_db = AsyncMock()
    # scrub calls 2 UPDATE statements; each returns a result with rowcount
    r1 = _rowcount_result(3)
    r2 = _rowcount_result(4)
    mock_db.execute = AsyncMock(side_effect=[r1, r2])

    ws_id = uuid.uuid4()
    count, cutoff = await purge_resource(
        mock_db,
        workspace_id=ws_id,
        resource_type="payloads",
        action="scrub",
        max_age_days=30,
        dry_run=False,
    )

    assert count == 7  # 3 + 4
    assert cutoff is not None


@pytest.mark.asyncio
async def test_purge_end_user_erasure() -> None:
    from runledger_api.services.retention import purge_resource

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_rowcount_result(2))

    ws_id = uuid.uuid4()
    count, cutoff = await purge_resource(
        mock_db,
        workspace_id=ws_id,
        resource_type="runs",
        action="delete",
        scope="end_user",
        scope_value="user-123",
        dry_run=False,
    )

    assert count == 2
    assert cutoff is None  # end_user scope has no cutoff


@pytest.mark.asyncio
async def test_purge_end_user_dry_run() -> None:
    from runledger_api.services.retention import purge_resource

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 3
    mock_db.execute = AsyncMock(return_value=count_result)

    ws_id = uuid.uuid4()
    count, cutoff = await purge_resource(
        mock_db,
        workspace_id=ws_id,
        resource_type="runs",
        action="delete",
        scope="end_user",
        scope_value="user-xyz",
        dry_run=True,
    )

    assert count == 3
    assert cutoff is None


@pytest.mark.asyncio
async def test_purge_workspace_scope_missing_age_raises() -> None:
    from runledger_api.services.retention import purge_resource

    mock_db = AsyncMock()
    with pytest.raises(ValueError, match="max_age_days"):
        await purge_resource(
            mock_db,
            workspace_id=uuid.uuid4(),
            resource_type="runs",
            action="delete",
            scope="workspace",
            max_age_days=None,
        )


# ── Unauthenticated ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_purge_unauthenticated() -> None:
    """Ensure the endpoint requires auth."""
    import httpx
    from runledger_api.main import app

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/retention/purge",
            json={"resource_type": "runs", "action": "delete", "max_age_days": 30},
        )
    assert resp.status_code == 401
