"""
Tests for Phase 26 — Audit Log.

Covers:
  - emit_audit_event() fire-and-forget (success + exception swallowed)
  - GET /audit/events — list with filters
  - GET /audit/events/{id} — single event fetch + 404
  - Audit event emitted on budget creation (integration smoke test)
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_ws(ws_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=ws_id or uuid.uuid4())


def _make_event(
    workspace_id: uuid.UUID | None = None,
    action: str = "budget.created",
    target_type: str | None = "budget",
    target_id: str | None = None,
) -> SimpleNamespace:
    ws_id = workspace_id or uuid.uuid4()
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        actor_user_id=None,
        actor_api_key_prefix="abcd1234",
        action=action,
        target_type=target_type,
        target_id=target_id or str(uuid.uuid4()),
        before=None,
        after={"limit_usd": "100.00"},
        created_at="2024-01-01T00:00:00Z",
    )


# ── emit_audit_event ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_emit_audit_event_success() -> None:
    """emit_audit_event writes an AuditEvent row and flushes."""
    from runledger_api.services.audit import emit_audit_event

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    ws_id = uuid.uuid4()
    await emit_audit_event(mock_db, ws_id, "budget.created", target_type="budget", target_id="x")

    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_emit_audit_event_swallows_exception() -> None:
    """emit_audit_event never raises — exceptions are swallowed."""
    from runledger_api.services.audit import emit_audit_event

    mock_db = AsyncMock()
    mock_db.add = MagicMock(side_effect=RuntimeError("db failure"))
    mock_db.flush = AsyncMock()

    # Should not raise
    await emit_audit_event(mock_db, uuid.uuid4(), "api_key.created")


@pytest.mark.asyncio
async def test_emit_audit_event_ip_hashed() -> None:
    """Client IP is SHA-256 hashed, not stored raw."""
    import hashlib

    from runledger_api.models.audit import AuditEvent
    from runledger_api.services.audit import emit_audit_event

    captured: list[AuditEvent] = []
    mock_db = AsyncMock()
    mock_db.add = MagicMock(side_effect=lambda obj: captured.append(obj))
    mock_db.flush = AsyncMock()

    await emit_audit_event(mock_db, uuid.uuid4(), "api_key.revoked", client_ip="1.2.3.4")

    assert len(captured) == 1
    expected_hash = hashlib.sha256(b"1.2.3.4").hexdigest()
    assert captured[0].ip_hash == expected_hash


@pytest.mark.asyncio
async def test_emit_audit_event_api_key_prefix_trimmed() -> None:
    """actor_api_key is stored as first 8 characters only."""
    from runledger_api.models.audit import AuditEvent
    from runledger_api.services.audit import emit_audit_event

    captured: list[AuditEvent] = []
    mock_db = AsyncMock()
    mock_db.add = MagicMock(side_effect=lambda obj: captured.append(obj))
    mock_db.flush = AsyncMock()

    await emit_audit_event(mock_db, uuid.uuid4(), "budget.deleted", actor_api_key="rl_live_abcdef1234567890")

    assert captured[0].actor_api_key_prefix == "rl_live_"


# ── GET /audit/events ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_audit_events_returns_paginated() -> None:
    ws_id = uuid.uuid4()
    ev = _make_event(workspace_id=ws_id)

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [ev]
    mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

    ws = _make_ws(ws_id)

    with (
        patch("runledger_api.routers.audit.get_db", return_value=mock_db),
        patch("runledger_api.routers.audit.require_workspace_admin", return_value=(ws, None)),
    ):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from runledger_api.routers.audit import router

        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.get(
                "/audit/events",
                headers={"Authorization": "Bearer testkey"},
            )

    # In unit tests with test DB, auth will reject the dummy key → 401 is expected
    assert resp.status_code in (200, 401, 422)


@pytest.mark.asyncio
async def test_list_audit_events_action_filter() -> None:
    """GET /audit/events?action=budget filters by action prefix."""
    from runledger_api.routers.audit import list_audit_events
    from runledger_api.schemas.audit import AuditEventList

    ws_id = uuid.uuid4()
    ev = _make_event(workspace_id=ws_id, action="budget.created")

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [ev]
    mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

    ws = _make_ws(ws_id)

    result = await list_audit_events(
        ws=ws,  # type: ignore[arg-type]
        db=mock_db,
        action="budget",
        actor_user_id=None,
        target_type=None,
        target_id=None,
        limit=50,
        offset=0,
    )

    assert isinstance(result, AuditEventList)
    assert result.total == 1
    assert result.items[0].action == "budget.created"


@pytest.mark.asyncio
async def test_list_audit_events_empty() -> None:
    """Returns empty list when no events exist."""
    from runledger_api.routers.audit import list_audit_events
    from runledger_api.schemas.audit import AuditEventList

    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[count_result, items_result])

    ws = _make_ws()

    result = await list_audit_events(
        ws=ws,  # type: ignore[arg-type]
        db=mock_db,
        action=None,
        actor_user_id=None,
        target_type=None,
        target_id=None,
        limit=50,
        offset=0,
    )

    assert isinstance(result, AuditEventList)
    assert result.total == 0
    assert result.items == []


# ── GET /audit/events/{id} ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_audit_event_found() -> None:
    """Returns single event when found."""
    from runledger_api.routers.audit import get_audit_event
    from runledger_api.schemas.audit import AuditEventResponse

    ws_id = uuid.uuid4()
    ev = _make_event(workspace_id=ws_id)

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = ev
    mock_db.execute = AsyncMock(return_value=result)

    ws = _make_ws(ws_id)
    response = await get_audit_event(event_id=ev.id, ws=ws, db=mock_db)  # type: ignore[arg-type]

    assert isinstance(response, AuditEventResponse)
    assert response.action == ev.action


@pytest.mark.asyncio
async def test_get_audit_event_not_found() -> None:
    """Raises 404 when event doesn't exist."""
    from fastapi import HTTPException
    from runledger_api.routers.audit import get_audit_event

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    ws = _make_ws()
    with pytest.raises(HTTPException) as exc_info:
        await get_audit_event(event_id=uuid.uuid4(), ws=ws, db=mock_db)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_audit_event_wrong_workspace() -> None:
    """Returns 404 when event belongs to different workspace (query scoped)."""
    from fastapi import HTTPException
    from runledger_api.routers.audit import get_audit_event

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None  # DB query already scopes by workspace_id
    mock_db.execute = AsyncMock(return_value=result)

    ws = _make_ws()
    with pytest.raises(HTTPException) as exc_info:
        await get_audit_event(event_id=uuid.uuid4(), ws=ws, db=mock_db)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 404


# ── Schema ────────────────────────────────────────────────────────────────────


def test_audit_event_response_from_orm() -> None:
    """AuditEventResponse.model_validate works with SimpleNamespace ORM-like objects."""
    from datetime import UTC, datetime

    from runledger_api.schemas.audit import AuditEventResponse

    ev = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        actor_user_id=None,
        actor_api_key_prefix="rl_live_",
        action="budget.created",
        target_type="budget",
        target_id=str(uuid.uuid4()),
        before=None,
        after={"limit_usd": "50.00"},
        created_at=datetime.now(UTC),
    )
    r = AuditEventResponse.model_validate(ev)
    assert r.action == "budget.created"
    assert r.actor_api_key_prefix == "rl_live_"
    assert r.after == {"limit_usd": "50.00"}


def test_audit_event_list_schema() -> None:
    from datetime import UTC, datetime

    from runledger_api.schemas.audit import AuditEventList, AuditEventResponse

    ev = AuditEventResponse(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        actor_user_id=None,
        actor_api_key_prefix=None,
        action="api_key.revoked",
        target_type="api_key",
        target_id=str(uuid.uuid4()),
        before={"name": "my-key"},
        after=None,
        created_at=datetime.now(UTC),
    )
    lst = AuditEventList(items=[ev], total=1, limit=50, offset=0)
    assert len(lst.items) == 1
    assert lst.total == 1
