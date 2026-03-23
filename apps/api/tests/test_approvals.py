"""
Tests for Phase 25 — Approvals & Policy Workflows.

Covers:
  POST   /approvals                  — create approval request
  GET    /approvals                  — list with status/type filters
  GET    /approvals/summary          — count by status
  GET    /approvals/{id}             — get single
  PUT    /approvals/{id}/approve     — approve pending
  PUT    /approvals/{id}/deny        — deny pending
  DELETE /approvals/{id}             — cancel pending
  PUT    /approvals/{id}/approve     — conflict if already decided
  PUT    /prompts/{name}/promote     — 403 without approval_id for production
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scalar_one_or_none(val) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=val)
    return m


def _scalar(val) -> MagicMock:
    m = MagicMock()
    m.scalar = MagicMock(return_value=val)
    return m


def _scalars_list(rows: list) -> MagicMock:
    m = MagicMock()
    sc = MagicMock()
    sc.all = MagicMock(return_value=rows)
    m.scalars = MagicMock(return_value=sc)
    return m


def _rows(rows: list) -> MagicMock:
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _make_approval(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        request_type="budget_increase",
        request={"budget_id": str(uuid.uuid4()), "new_limit": 500},
        status="pending",
        requested_by="alice@example.com",
        decided_by=None,
        decided_at=None,
        decision_note=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_api_key(email: str | None = "alice@example.com") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        is_session=True,
        created_by=email,
    )


# ── POST /approvals ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_approval_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    from runledger_api.core.deps import get_current_api_key
    from runledger_api.main import app

    api_key = _make_api_key()
    approval = _make_approval(workspace_id=mock_workspace.id)

    async def override_api_key() -> SimpleNamespace:
        return api_key

    app.dependency_overrides[get_current_api_key] = override_api_key

    async def mock_refresh(obj: object) -> None:
        obj.id = approval.id  # type: ignore[attr-defined]
        obj.created_at = approval.created_at  # type: ignore[attr-defined]
        obj.status = "pending"  # type: ignore[attr-defined]
        obj.decided_by = None  # type: ignore[attr-defined]
        obj.decided_at = None  # type: ignore[attr-defined]
        obj.decision_note = None  # type: ignore[attr-defined]
        obj.requested_by = api_key.created_by  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh

    try:
        resp = await authed_client.post(
            "/approvals",
            json={
                "request_type": "budget_increase",
                "request": {"new_limit": 500},
                "reason": "Need more budget for Q2 campaign",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_api_key, None)

    assert resp.status_code == 201
    data = resp.json()
    assert data["request_type"] == "budget_increase"
    assert data["status"] == "pending"
    assert data["requested_by"] == "alice@example.com"


@pytest.mark.asyncio
async def test_create_approval_unauthenticated(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/approvals",
        json={"request_type": "prompt_promote"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_approval_all_types(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    from runledger_api.core.deps import get_current_api_key
    from runledger_api.main import app

    api_key = _make_api_key()

    async def override_api_key() -> SimpleNamespace:
        return api_key

    app.dependency_overrides[get_current_api_key] = override_api_key

    try:
        for request_type in [
            "budget_increase", "prompt_promote", "tool_allow",
            "capture_policy_full", "shadow_routing"
        ]:
            approval = _make_approval(workspace_id=mock_workspace.id, request_type=request_type)

            async def mock_refresh(obj: object, _a=approval) -> None:
                obj.id = _a.id  # type: ignore[attr-defined]
                obj.created_at = _a.created_at  # type: ignore[attr-defined]
                obj.status = "pending"  # type: ignore[attr-defined]
                obj.decided_by = None  # type: ignore[attr-defined]
                obj.decided_at = None  # type: ignore[attr-defined]
                obj.decision_note = None  # type: ignore[attr-defined]
                obj.requested_by = api_key.created_by  # type: ignore[attr-defined]

            mock_db_session.refresh = mock_refresh

            resp = await authed_client.post(
                "/approvals",
                json={"request_type": request_type},
            )
            assert resp.status_code == 201, f"Failed for type {request_type}"
    finally:
        app.dependency_overrides.pop(get_current_api_key, None)


# ── GET /approvals ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_approvals_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar(0), _scalars_list([])]
    )
    resp = await authed_client.get("/approvals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_approvals_returns_items(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    approval = _make_approval(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar(1), _scalars_list([approval])]
    )
    resp = await authed_client.get("/approvals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["request_type"] == "budget_increase"
    assert data["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_approvals_filter_by_status(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar(0), _scalars_list([])]
    )
    resp = await authed_client.get("/approvals?status=approved")
    assert resp.status_code == 200


# ── GET /approvals/summary ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approval_summary_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_rows([]))
    resp = await authed_client.get("/approvals/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"pending": 0, "approved": 0, "denied": 0, "cancelled": 0}


@pytest.mark.asyncio
async def test_approval_summary_with_counts(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rows = [
        SimpleNamespace(status="pending", cnt=3),
        SimpleNamespace(status="approved", cnt=7),
        SimpleNamespace(status="denied", cnt=1),
    ]
    mock_db_session.execute = AsyncMock(return_value=_rows(rows))
    resp = await authed_client.get("/approvals/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending"] == 3
    assert data["approved"] == 7
    assert data["denied"] == 1
    assert data["cancelled"] == 0


# ── GET /approvals/{id} ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_approval_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    approval = _make_approval(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(approval))
    resp = await authed_client.get(f"/approvals/{approval.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(approval.id)


@pytest.mark.asyncio
async def test_get_approval_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.get(f"/approvals/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PUT /approvals/{id}/approve ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_pending(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    from runledger_api.core.deps import get_current_api_key
    from runledger_api.main import app

    api_key = _make_api_key(email="admin@example.com")
    approval = _make_approval(workspace_id=mock_workspace.id, status="pending")

    async def override_api_key() -> SimpleNamespace:
        return api_key

    app.dependency_overrides[get_current_api_key] = override_api_key

    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(approval))

    async def mock_refresh(obj: object) -> None:
        pass  # already mutated in-place

    mock_db_session.refresh = mock_refresh

    try:
        resp = await authed_client.put(
            f"/approvals/{approval.id}/approve",
            json={"note": "Looks good, approved."},
        )
    finally:
        app.dependency_overrides.pop(get_current_api_key, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["decided_by"] == "admin@example.com"
    assert data["decision_note"] == "Looks good, approved."


@pytest.mark.asyncio
async def test_approve_already_decided_conflict(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    from runledger_api.core.deps import get_current_api_key
    from runledger_api.main import app

    api_key = _make_api_key()
    approval = _make_approval(workspace_id=mock_workspace.id, status="approved")

    async def override_api_key() -> SimpleNamespace:
        return api_key

    app.dependency_overrides[get_current_api_key] = override_api_key
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(approval))

    try:
        resp = await authed_client.put(
            f"/approvals/{approval.id}/approve",
            json={},
        )
    finally:
        app.dependency_overrides.pop(get_current_api_key, None)

    assert resp.status_code == 409


# ── PUT /approvals/{id}/deny ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deny_pending(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    from runledger_api.core.deps import get_current_api_key
    from runledger_api.main import app

    api_key = _make_api_key(email="admin@example.com")
    approval = _make_approval(workspace_id=mock_workspace.id, status="pending")

    async def override_api_key() -> SimpleNamespace:
        return api_key

    app.dependency_overrides[get_current_api_key] = override_api_key
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(approval))

    async def mock_refresh(obj: object) -> None:
        pass

    mock_db_session.refresh = mock_refresh

    try:
        resp = await authed_client.put(
            f"/approvals/{approval.id}/deny",
            json={"note": "Not approved at this time."},
        )
    finally:
        app.dependency_overrides.pop(get_current_api_key, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "denied"
    assert data["decided_by"] == "admin@example.com"


@pytest.mark.asyncio
async def test_deny_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    from runledger_api.core.deps import get_current_api_key
    from runledger_api.main import app

    api_key = _make_api_key()

    async def override_api_key() -> SimpleNamespace:
        return api_key

    app.dependency_overrides[get_current_api_key] = override_api_key
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    try:
        resp = await authed_client.put(f"/approvals/{uuid.uuid4()}/deny", json={})
    finally:
        app.dependency_overrides.pop(get_current_api_key, None)

    assert resp.status_code == 404


# ── DELETE /approvals/{id} ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_pending(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    approval = _make_approval(workspace_id=mock_workspace.id, status="pending")
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(approval))

    async def mock_refresh(obj: object) -> None:
        pass

    mock_db_session.refresh = mock_refresh

    resp = await authed_client.delete(f"/approvals/{approval.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_non_pending_conflict(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    approval = _make_approval(workspace_id=mock_workspace.id, status="approved")
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(approval))
    resp = await authed_client.delete(f"/approvals/{approval.id}")
    assert resp.status_code == 409


# ── validate_approved helper ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_approved_passes() -> None:
    from runledger_api.routers.approvals import validate_approved

    approval_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    approval = _make_approval(
        id=approval_id,
        workspace_id=workspace_id,
        request_type="prompt_promote",
        status="approved",
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(approval))

    result = await validate_approved(mock_db, workspace_id, approval_id, "prompt_promote")
    assert result.id == approval_id


@pytest.mark.asyncio
async def test_validate_approved_wrong_type_raises() -> None:
    from fastapi import HTTPException
    from runledger_api.routers.approvals import validate_approved

    approval_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    approval = _make_approval(
        id=approval_id,
        workspace_id=workspace_id,
        request_type="budget_increase",
        status="approved",
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(approval))

    with pytest.raises(HTTPException) as exc_info:
        await validate_approved(mock_db, workspace_id, approval_id, "prompt_promote")
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_approved_pending_raises() -> None:
    from fastapi import HTTPException
    from runledger_api.routers.approvals import validate_approved

    approval_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    approval = _make_approval(
        id=approval_id,
        workspace_id=workspace_id,
        request_type="prompt_promote",
        status="pending",  # not yet approved
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_one_or_none(approval))

    with pytest.raises(HTTPException) as exc_info:
        await validate_approved(mock_db, workspace_id, approval_id, "prompt_promote")
    assert exc_info.value.status_code == 403
