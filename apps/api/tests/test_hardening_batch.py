"""Fixes for P-09/10/15/16/23, O-21, S-10, S-17, S-20, B-01, B-06 (review)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from pydantic import ValidationError


# ── P-10 email templates escape user input ────────────────────────────────────
@pytest.mark.asyncio
async def test_email_templates_escape_user_values() -> None:
    from runledger_api.services import email

    sent: dict[str, str] = {}

    async def fake_send(to: str, subject: str, html: str, text: str, **_: object) -> None:
        sent["html"] = html

    with patch.object(email, "send_email", fake_send):
        await email.send_approval_request_email(
            to_email="a@example.com",
            full_name="<script>alert(1)</script>",
            request_type="budget_increase",
            reason="<script>alert(1)</script>",
            requester="x",
            workspace_name="ws",
            approval_url="https://app.example/approvals",
        )
    assert "<script>" not in sent["html"]
    assert "&lt;script&gt;" in sent["html"]


# ── P-09 SMTP verifies certificates and has a timeout ─────────────────────────
def test_smtp_starttls_uses_verified_context() -> None:
    from runledger_api.services import email

    smtp = MagicMock()
    smtp.__enter__ = MagicMock(return_value=smtp)
    smtp.__exit__ = MagicMock(return_value=False)
    with (
        patch.object(email.smtplib, "SMTP", return_value=smtp) as ctor,
        patch.object(email.settings, "smtp_port", 587),
    ):
        email._send_smtp("a@example.com", "s", "<p>h</p>", "t")
    assert ctor.call_args.kwargs.get("timeout")
    ctx = smtp.starttls.call_args.kwargs["context"]
    assert ctx.verify_mode.name == "CERT_REQUIRED" and ctx.check_hostname


# ── P-15 metrics token, P-16 security headers ─────────────────────────────────
def test_metrics_token_constant_time() -> None:
    from fastapi import HTTPException
    from runledger_api.routers.health import _require_metrics_token

    with patch("runledger_api.routers.health.settings") as s:
        s.effective_metrics_token = "tok"
        _require_metrics_token("Bearer tok")
        for bad in (None, "Bearer tok2", "tok"):
            with pytest.raises(HTTPException):
                _require_metrics_token(bad)
        s.effective_metrics_token = ""
        with pytest.raises(HTTPException) as exc:
            _require_metrics_token("Bearer ")
        assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_security_headers(client: AsyncClient) -> None:
    resp = await client.get("/health/live")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in resp.headers["content-security-policy"]


# ── S-10 privacy mode enum ────────────────────────────────────────────────────
def test_privacy_mode_validated() -> None:
    from runledger_api.schemas.privacy import CapturePolicyUpsert

    with pytest.raises(ValidationError):
        CapturePolicyUpsert(privacy_mode="EVERYTHING")
    with pytest.raises(ValidationError):
        CapturePolicyUpsert(privacy_mode="SAMPLED")
    with pytest.raises(ValidationError):
        CapturePolicyUpsert(privacy_mode="SAMPLED", sampled_rate=2)
    assert CapturePolicyUpsert(privacy_mode="FULL").privacy_mode == "FULL"


# ── B-06 replay worker registered ─────────────────────────────────────────────
def test_replay_task_registered() -> None:
    import importlib

    from runledger_api.core.celery_app import celery_app

    for module in celery_app.conf.include:
        importlib.import_module(module)
    assert "replay.run_experiment" in celery_app.tasks


# ── S-20 retention isolates policies ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_retention_failure_does_not_stop_other_policies() -> None:
    from runledger_api.workers.retention import _run_active_policies

    good = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        resource_type="runs",
        action="delete",
        scope=None,
        scope_value=None,
        max_age_days=30,
        last_run_at=None,
        last_purged_count=None,
    )
    bad = SimpleNamespace(**{**vars(good), "id": uuid.uuid4()})
    session = AsyncMock()
    res = MagicMock()
    res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[bad, good])))
    session.execute = AsyncMock(return_value=res)
    nested = MagicMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=nested)
    calls = {"n": 0}

    async def purge(*_a: object, **_k: object) -> tuple[int, list[object]]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return 5, []

    with patch("runledger_api.services.retention.purge_resource", purge):
        total = await _run_active_policies(session)
    assert total == 5
    assert good.last_purged_count == 5
    session.rollback.assert_awaited()


# ── O-21 telemetry chart includes the current hour ────────────────────────────
@pytest.mark.asyncio
async def test_telemetry_buckets_end_at_current_hour(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    res = MagicMock()
    res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    mock_db_session.execute = AsyncMock(return_value=res)
    resp = await authed_client.get("/v1/traces/insights")
    assert resp.status_code == 200, resp.text
    buckets = resp.json()["timeseries_24h"]
    assert len(buckets) == 24
    last = datetime.fromisoformat(buckets[-1]["timestamp"])
    now_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    assert abs(last - now_hour) < timedelta(hours=1)
