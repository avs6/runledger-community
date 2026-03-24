"""
Tests for the RunLedger email notification system.

Covers:
1.  GET /settings/email/preferences — creates default if not exists
2.  PUT /settings/email/preferences — updates fields
3.  POST /settings/email/test       — calls send_email, returns ok=True
4.  GET  /settings/email/log        — returns recent log items
5.  GET /auth/unsubscribe?token=valid   — disables notifications
6.  GET /auth/unsubscribe?token=invalid — returns ok=False
7.  Alert worker respects prefs.alerts_enabled=False
8.  Alert worker uses workspace.name not UUID
9.  Budget runaway fires email to admins
10. Billing period close fires email to admins
11. Invoice dispute_line fires email to admins
12. Weekly report skips workspace when report_frequency='never'
"""

from __future__ import annotations

import uuid
from datetime import UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Shared fixtures ────────────────────────────────────────────────────────────

WORKSPACE_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
PREFS_ID = uuid.uuid4()


def make_workspace(name: str = "Test Workspace") -> SimpleNamespace:
    return SimpleNamespace(id=WORKSPACE_ID, name=name, tenant_id=uuid.uuid4())


def make_user(email: str = "admin@example.com") -> SimpleNamespace:
    return SimpleNamespace(
        id=USER_ID,
        email=email,
        full_name="Test Admin",
        is_active=True,
        email_notifications_enabled=True,
        email_unsubscribe_token=None,
    )


def make_prefs(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=PREFS_ID,
        workspace_id=WORKSPACE_ID,
        report_frequency="weekly",
        alerts_enabled=True,
        approvals_enabled=True,
        reconciliation_enabled=True,
        budget_alerts_enabled=True,
        billing_closed_enabled=True,
        score_regression_enabled=True,
        dispute_flagged_enabled=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_api_key(created_by: str = "admin@example.com") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=WORKSPACE_ID,
        key_hash="hash",
        key_prefix="rl_test",
        name="session",
        scopes=[],
        revoked_at=None,
        is_session=True,
        created_by=created_by,
        created_at="2026-01-01T00:00:00Z",
    )


# ── Test 1: GET /settings/email/preferences — creates default ─────────────────


@pytest.mark.asyncio
async def test_get_email_preferences_creates_default() -> None:
    from runledger_api.routers.settings import get_email_preferences

    mock_db = AsyncMock()
    # First query returns None (no existing prefs)
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_scalar)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    async def mock_refresh(obj: object) -> None:
        obj.id = PREFS_ID  # type: ignore[attr-defined]
        obj.created_at = "2026-01-01T00:00:00Z"  # type: ignore[attr-defined]
        obj.updated_at = "2026-01-01T00:00:00Z"  # type: ignore[attr-defined]

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    workspace = make_workspace()
    await get_email_preferences(workspace=workspace, db=mock_db)  # type: ignore[arg-type]

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


# ── Test 2: PUT /settings/email/preferences — updates fields ──────────────────


@pytest.mark.asyncio
async def test_update_email_preferences() -> None:
    from runledger_api.routers.settings import update_email_preferences
    from runledger_api.schemas.email_prefs import EmailPreferenceUpdate

    mock_db = AsyncMock()
    prefs_obj = make_prefs(report_frequency="weekly", alerts_enabled=True)
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=prefs_obj)
    mock_db.execute = AsyncMock(return_value=mock_execute)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    workspace = make_workspace()
    body = EmailPreferenceUpdate(report_frequency="never", alerts_enabled=False)

    await update_email_preferences(body=body, workspace=workspace, db=mock_db)  # type: ignore[arg-type]

    assert prefs_obj.report_frequency == "never"
    assert prefs_obj.alerts_enabled is False
    mock_db.commit.assert_awaited_once()


# ── Test 3: POST /settings/email/test — calls send_email ──────────────────────


@pytest.mark.asyncio
async def test_email_test_endpoint_ok() -> None:
    from runledger_api.routers.settings import test_email_send

    mock_db = AsyncMock()
    session_key = make_api_key("admin@example.com")
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=session_key)
    mock_db.execute = AsyncMock(return_value=mock_execute)

    workspace = make_workspace()

    with patch(
        "runledger_api.routers.settings.send_email", new_callable=AsyncMock
    ) as mock_send:
        result = await test_email_send(workspace=workspace, db=mock_db)  # type: ignore[arg-type]

    assert result["ok"] is True
    assert result["error"] is None
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_email_test_endpoint_no_user() -> None:
    from runledger_api.routers.settings import test_email_send

    mock_db = AsyncMock()
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_execute)

    workspace = make_workspace()
    result = await test_email_send(workspace=workspace, db=mock_db)  # type: ignore[arg-type]

    assert result["ok"] is False
    assert result["error"] is not None


# ── Test 4: GET /settings/email/log ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_email_log() -> None:
    from runledger_api.routers.settings import get_email_log

    mock_db = AsyncMock()
    log_item = SimpleNamespace(
        id=uuid.uuid4(),
        to_email="admin@example.com",
        subject="Test",
        event_type="test",
        status="sent",
        error_message=None,
        sent_at="2026-01-01T00:00:00Z",
    )

    # Two execute calls: one for items, one for total count
    mock_exec1 = AsyncMock()
    mock_exec1.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[log_item])))
    mock_exec2 = AsyncMock()
    mock_exec2.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[log_item])))
    mock_db.execute = AsyncMock(side_effect=[mock_exec1, mock_exec2])

    workspace = make_workspace()
    result = await get_email_log(workspace=workspace, db=mock_db)  # type: ignore[arg-type]

    assert result.total == 1
    assert len(result.items) == 1


# ── Test 5: GET /auth/unsubscribe?token=valid ────────────────────────────────


@pytest.mark.asyncio
async def test_unsubscribe_valid_token() -> None:
    from runledger_api.routers.login import unsubscribe_email

    mock_db = AsyncMock()
    user = make_user()
    user.email_notifications_enabled = True
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=user)
    mock_db.execute = AsyncMock(return_value=mock_execute)
    mock_db.commit = AsyncMock()

    result = await unsubscribe_email(token="valid-token-123", db=mock_db)  # type: ignore[arg-type]

    assert result["ok"] is True
    assert user.email_notifications_enabled is False
    mock_db.commit.assert_awaited_once()


# ── Test 6: GET /auth/unsubscribe?token=invalid ──────────────────────────────


@pytest.mark.asyncio
async def test_unsubscribe_invalid_token() -> None:
    from runledger_api.routers.login import unsubscribe_email

    mock_db = AsyncMock()
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_execute)

    result = await unsubscribe_email(token="bad-token", db=mock_db)  # type: ignore[arg-type]

    assert result["ok"] is False
    assert "Invalid" in result["message"]


# ── Test 7: Alert worker respects prefs.alerts_enabled=False ────────────────


@pytest.mark.asyncio
async def test_alert_worker_respects_prefs_disabled() -> None:
    from runledger_api.workers.alerts import _run_evaluation

    prefs = make_prefs(alerts_enabled=False)
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=WORKSPACE_ID,
        name="High Error Rate",
        metric="error_rate",
        operator="gt",
        threshold=0.5,
        window_minutes=60,
        is_active=True,
        email_enabled=True,
        channel_id=None,
    )

    call_count = [0]

    def make_mock(n: int) -> MagicMock:
        mock = MagicMock()
        if n == 1:
            # rules query — scalars().all() must be sync
            mock.scalars.return_value = MagicMock(all=MagicMock(return_value=[rule]))
        elif n == 2:
            mock.scalar_one.return_value = 10  # total runs
        elif n == 3:
            mock.scalar_one.return_value = 8  # failed runs
        elif n == 4:
            mock.scalar_one_or_none.return_value = None  # dedup
        else:
            mock.scalar_one_or_none.return_value = None
        return mock

    async def side_effect_execute(stmt: object) -> MagicMock:
        call_count[0] += 1
        return make_mock(call_count[0])

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=side_effect_execute)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)

    with (
        patch("runledger_api.workers.alerts._make_session_factory", return_value=mock_factory),
        patch("runledger_api.workers.alerts.get_email_preference", new_callable=AsyncMock, return_value=prefs),
        patch("runledger_api.workers.alerts._send_alert_emails", new_callable=AsyncMock) as mock_emails,
    ):
        await _run_evaluation()

    # email should NOT be called because alerts_enabled=False
    mock_emails.assert_not_awaited()


# ── Test 8: Alert worker uses workspace.name not UUID ────────────────────────


@pytest.mark.asyncio
async def test_alert_emails_uses_workspace_name() -> None:
    from decimal import Decimal

    from runledger_api.workers.alerts import _send_alert_emails

    rule = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=WORKSPACE_ID,
        name="Test Rule",
        metric="error_rate",
        operator="gt",
        threshold=Decimal("0.1"),
    )
    workspace = make_workspace(name="My Workspace")
    user = make_user()

    mock_session = AsyncMock()
    ws_exec = AsyncMock()
    ws_exec.scalar_one_or_none = MagicMock(return_value=workspace)
    mock_session.execute = AsyncMock(return_value=ws_exec)

    with (
        patch(
            "runledger_api.workers.alerts.get_workspace_admin_users",
            new_callable=AsyncMock,
            return_value=[user],
        ),
        patch(
            "runledger_api.workers.alerts.send_alert_fired_email",
            new_callable=AsyncMock,
        ) as mock_email,
    ):
        await _send_alert_emails(mock_session, rule, Decimal("0.5"))

    mock_email.assert_awaited_once()
    kwargs = mock_email.call_args.kwargs
    assert kwargs["workspace_name"] == "My Workspace"


# ── Test 9: Budget runaway fires email to admins ──────────────────────────────


@pytest.mark.asyncio
async def test_budget_runaway_emails_admins() -> None:
    from runledger_api.workers.budgets import _run_runaway_protection

    run = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=WORKSPACE_ID,
        status="running",
        started_at="2026-01-01T00:00:00Z",
    )
    workspace = make_workspace()
    user = make_user()
    prefs = make_prefs(budget_alerts_enabled=True)

    call_count = [0]

    def make_exec_mock(n: int) -> MagicMock:
        mock = MagicMock()
        if n == 1:
            # active runs — list(result.scalars()) pattern
            mock.scalars.return_value = [run]
        elif n == 2:
            mock.scalar_one.return_value = 25  # storm count >20
        elif n == 3:
            mock.scalar_one.return_value = 0  # spike count
        elif n == 4:
            mock.scalars.return_value = []  # notifications
        elif n == 5:
            mock.scalar_one_or_none.return_value = workspace  # workspace lookup
        else:
            mock.scalars.return_value = []
            mock.scalar_one_or_none.return_value = None
            mock.scalar_one.return_value = 0
        return mock

    async def execute_side_effect(stmt: object) -> MagicMock:
        call_count[0] += 1
        return make_exec_mock(call_count[0])

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=execute_side_effect)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with (
        patch("runledger_api.workers.budgets._make_session_factory", return_value=mock_factory),
        patch("runledger_api.workers.budgets._make_redis", return_value=mock_redis),
        patch("runledger_api.workers.budgets.get_email_preference", new_callable=AsyncMock, return_value=prefs),
        patch("runledger_api.workers.budgets.get_workspace_admin_users", new_callable=AsyncMock, return_value=[user]),
        patch("runledger_api.workers.budgets.send_budget_breach_email", new_callable=AsyncMock) as mock_email,
        patch("runledger_api.workers.budgets.send_notification", new_callable=AsyncMock),
    ):
        await _run_runaway_protection()

    mock_email.assert_awaited()


# ── Test 10: Billing period close fires email ─────────────────────────────────


@pytest.mark.asyncio
async def test_billing_close_fires_email() -> None:
    from datetime import date, datetime

    from runledger_api.routers.billing import close_period

    period_id = uuid.uuid4()
    signing_key_id = uuid.uuid4()
    period = SimpleNamespace(
        id=period_id,
        workspace_id=WORKSPACE_ID,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status="open",
        total_cost_usd="42.00",
    )
    snapshot = SimpleNamespace(
        id=uuid.uuid4(),
        billing_period_id=str(period_id),
        signature="abcdef1234567890abcdef1234567890",
        signing_key_id=str(signing_key_id),
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    workspace = make_workspace()
    auth = (workspace,)

    mock_db = AsyncMock()
    period_exec = MagicMock()
    period_exec.scalar_one_or_none = MagicMock(return_value=period)
    mock_db.execute = AsyncMock(return_value=period_exec)

    with (
        patch(
            "runledger_api.routers.billing.close_billing_period",
            new_callable=AsyncMock,
            return_value=snapshot,
        ),
        patch(
            "runledger_api.routers.billing.get_email_preference",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "runledger_api.routers.billing.get_workspace_admin_users",
            new_callable=AsyncMock,
            return_value=[make_user()],
        ),
        patch(
            "runledger_api.routers.billing.send_billing_period_closed_email",
            new_callable=AsyncMock,
        ),
        patch("runledger_api.routers.billing._asyncio.create_task") as mock_task,
    ):
        await close_period(period_id=period_id, auth=auth, db=mock_db)  # type: ignore[arg-type]

    # create_task was called (fire-and-forget pattern)
    mock_task.assert_called_once()


# ── Test 11: Invoice dispute_line fires email ──────────────────────────────────


@pytest.mark.asyncio
async def test_dispute_line_fires_email() -> None:
    from datetime import date, datetime
    from decimal import Decimal

    from runledger_api.routers.invoices import dispute_line
    from runledger_api.schemas.invoices import DisputeRequest

    invoice_id = uuid.uuid4()
    line_id = uuid.uuid4()
    invoice = SimpleNamespace(
        id=invoice_id,
        workspace_id=WORKSPACE_ID,
        provider="openai",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        currency="USD",
        total_amount=Decimal("100.00"),
        line_count=10,
        matched_count=8,
        unmatched_amount=Decimal("5.00"),
        status="reconciled",
        filename="openai.csv",
        created_at=datetime(2026, 1, 15, tzinfo=UTC),
    )
    line = SimpleNamespace(
        id=line_id,
        invoice_id=invoice_id,
        provider_request_id=None,
        model=None,
        input_tokens=None,
        output_tokens=None,
        amount=Decimal("2.50"),
        occurred_at=datetime(2026, 1, 10, tzinfo=UTC),
        match_status="unmatched",
        matched_call_id=None,
        token_delta=None,
        cost_delta=Decimal("0.10"),
        dispute_note=None,
        raw={},
    )
    workspace = make_workspace()

    call_count = [0]

    def make_exec_mock(n: int) -> MagicMock:
        mock = MagicMock()
        if n == 1:
            mock.scalar_one_or_none = MagicMock(return_value=invoice)  # invoice ownership
        elif n == 2:
            mock.scalar_one_or_none = MagicMock(return_value=line)  # line query
        elif n == 3:
            mock.scalar_one_or_none = MagicMock(return_value=invoice)  # re-load invoice
        else:
            mock.scalar_one_or_none = MagicMock(return_value=None)
        return mock

    async def execute_side_effect(stmt: object) -> MagicMock:
        call_count[0] += 1
        return make_exec_mock(call_count[0])

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    body = DisputeRequest(note="Mismatch in token count")

    with (
        patch("runledger_api.routers.invoices.get_email_preference", new_callable=AsyncMock, return_value=None),
        patch("runledger_api.routers.invoices.get_workspace_admin_users", new_callable=AsyncMock, return_value=[make_user()]),
        patch("runledger_api.routers.invoices.send_dispute_flagged_email", new_callable=AsyncMock),
        patch("runledger_api.routers.invoices._asyncio.create_task") as mock_task,
    ):
        await dispute_line(
            invoice_id=invoice_id,
            line_id=line_id,
            body=body,
            workspace=workspace,  # type: ignore[arg-type]
            db=mock_db,  # type: ignore[arg-type]
        )

    mock_task.assert_called_once()


# ── Test 12: Weekly report skips workspace when frequency='never' ─────────────


@pytest.mark.asyncio
async def test_weekly_report_skips_never_frequency() -> None:
    from runledger_api.workers.email_reports import _run_weekly_reports

    workspace = make_workspace()
    prefs = make_prefs(report_frequency="never")

    usage_row = SimpleNamespace(
        day="2026-01-15",
        provider="openai",
        model="gpt-4o",
        cost_usd="1.23",
        input_tokens=1000,
        output_tokens=500,
        call_count=5,
    )

    call_count = [0]

    def make_exec_mock(n: int) -> MagicMock:
        mock = MagicMock()
        if n == 1:
            # workspace list — scalars().all() must be sync
            mock.scalars.return_value = MagicMock(all=MagicMock(return_value=[workspace]))
        elif n == 2:
            # usage rows
            mock.scalars.return_value = MagicMock(all=MagicMock(return_value=[usage_row]))
        else:
            mock.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        return mock

    async def execute_side_effect(stmt: object) -> MagicMock:
        call_count[0] += 1
        return make_exec_mock(call_count[0])

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=execute_side_effect)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)

    with (
        patch("runledger_api.workers.email_reports._make_session_factory", return_value=mock_factory),
        patch("runledger_api.workers.email_reports.get_email_preference", new_callable=AsyncMock, return_value=prefs),
        patch("runledger_api.workers.email_reports.get_workspace_admin_users", new_callable=AsyncMock, return_value=[make_user()]),
        patch("runledger_api.workers.email_reports.send_analytics_report_email", new_callable=AsyncMock) as mock_email,
    ):
        result = await _run_weekly_reports()

    # Email should NOT be sent because frequency='never'
    mock_email.assert_not_awaited()
    assert result["emails_sent"] == 0
