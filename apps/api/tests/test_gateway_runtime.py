"""
Tests for Phase 30 — Gateway Runtime Controls.

Covers:
  - PII redaction (gateway_redact)
  - Cost cap checks (gateway_controls)
  - Per-user RPM rate limiting (gateway_controls)
  - Gateway health worker logic
  - New route columns persisted via router
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── PII Redaction ─────────────────────────────────────────────────────────────
from runledger_api.services.gateway_redact import redact_messages, redact_text


def test_redact_email():
    assert (
        redact_text("Contact us at user@example.com for help") == "Contact us at [EMAIL] for help"
    )


def test_redact_phone_us():
    result = redact_text("Call me at 555-867-5309 today")
    assert "[PHONE]" in result
    assert "555-867-5309" not in result


def test_redact_ssn():
    result = redact_text("My SSN is 123-45-6789.")
    assert "[SSN]" in result
    assert "123-45-6789" not in result


def test_redact_credit_card():
    result = redact_text("Card number 4111 1111 1111 1111 for payment")
    assert "[CARD]" in result
    assert "4111" not in result


def test_redact_multiple_pii_types():
    text = "Email user@test.com phone 800-555-1234 ssn 987-65-4321"
    result = redact_text(text)
    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "[SSN]" in result
    assert "user@test.com" not in result


def test_redact_messages_string_content():
    messages = [
        {"role": "user", "content": "My email is foo@bar.com"},
        {"role": "assistant", "content": "Noted."},
    ]
    redacted = redact_messages(messages)
    assert "[EMAIL]" in redacted[0]["content"]
    assert redacted[1]["content"] == "Noted."


def test_redact_messages_multipart_content():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "SSN 111-22-3333"},
                {"type": "image_url", "image_url": "https://example.com/img"},
            ],
        }
    ]
    redacted = redact_messages(messages)
    assert "[SSN]" in redacted[0]["content"][0]["text"]
    # Non-text parts untouched
    assert redacted[0]["content"][1]["image_url"] == "https://example.com/img"


def test_redact_messages_no_pii():
    messages = [{"role": "user", "content": "Hello world, how are you?"}]
    redacted = redact_messages(messages)
    assert redacted[0]["content"] == "Hello world, how are you?"


# ── Cost Cap ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_cost_cap_no_limits_skips():
    """No cost limits configured → no DB query, no exception."""
    from runledger_api.services.gateway_controls import check_cost_cap

    route = SimpleNamespace(
        id=uuid.uuid4(),
        daily_cost_limit_usd=None,
        monthly_cost_limit_usd=None,
    )
    db = MagicMock()
    # Should not raise and not call db
    await check_cost_cap(db, route, uuid.uuid4())
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_check_cost_cap_daily_under_limit():
    """Under daily limit → no exception raised."""
    from runledger_api.services.gateway_controls import check_cost_cap

    route = SimpleNamespace(
        id=uuid.uuid4(),
        daily_cost_limit_usd=Decimal("50.00"),
        monthly_cost_limit_usd=None,
    )
    # Simulate DB returning 0 tokens (cost = $0)
    mock_row = SimpleNamespace(total_input=None, total_output=None)
    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    await check_cost_cap(db, route, uuid.uuid4())  # should not raise


@pytest.mark.asyncio
async def test_check_cost_cap_daily_exceeded():
    """Over daily limit → HTTP 429 with X-Cost-Cap-Reason header."""
    from fastapi import HTTPException
    from runledger_api.services.gateway_controls import check_cost_cap

    route = SimpleNamespace(
        id=uuid.uuid4(),
        daily_cost_limit_usd=Decimal("0.00"),  # cap at zero
        monthly_cost_limit_usd=None,
    )
    # Simulate 2M input tokens → estimated cost > $0
    mock_monthly_row = SimpleNamespace(total_input=None, total_output=None)
    mock_daily_row = SimpleNamespace(total_input=2_000_000, total_output=0)
    monthly_result = MagicMock()
    monthly_result.one.return_value = mock_monthly_row
    daily_result = MagicMock()
    daily_result.one.return_value = mock_daily_row
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[monthly_result, daily_result])

    with pytest.raises(HTTPException) as exc_info:
        await check_cost_cap(db, route, uuid.uuid4())
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["X-Cost-Cap-Reason"] == "daily_limit_exceeded"


@pytest.mark.asyncio
async def test_check_cost_cap_monthly_exceeded():
    """Over monthly limit → HTTP 429 with X-Cost-Cap-Reason header."""
    from fastapi import HTTPException
    from runledger_api.services.gateway_controls import check_cost_cap

    route = SimpleNamespace(
        id=uuid.uuid4(),
        daily_cost_limit_usd=None,
        monthly_cost_limit_usd=Decimal("0.00"),
    )
    mock_monthly_row = SimpleNamespace(total_input=5_000_000, total_output=0)
    monthly_result = MagicMock()
    monthly_result.one.return_value = mock_monthly_row
    db = AsyncMock()
    db.execute = AsyncMock(return_value=monthly_result)

    with pytest.raises(HTTPException) as exc_info:
        await check_cost_cap(db, route, uuid.uuid4())
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["X-Cost-Cap-Reason"] == "monthly_limit_exceeded"


# ── Per-user RPM ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_per_user_rpm_under_limit():
    """Under rate limit → no exception."""
    from runledger_api.services.gateway_controls import check_per_user_rpm

    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=5)
    redis.expire = AsyncMock(return_value=True)

    await check_per_user_rpm(redis, uuid.uuid4(), "user-1", uuid.uuid4(), 60)


@pytest.mark.asyncio
async def test_per_user_rpm_exceeded():
    """Over RPM limit → HTTP 429 with Retry-After header."""
    from fastapi import HTTPException
    from runledger_api.services.gateway_controls import check_per_user_rpm

    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=61)
    redis.expire = AsyncMock(return_value=True)

    with pytest.raises(HTTPException) as exc_info:
        await check_per_user_rpm(redis, uuid.uuid4(), "user-1", uuid.uuid4(), 60)
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_per_user_rpm_redis_error_fails_open():
    """Redis failure → fail open, no exception raised."""
    from runledger_api.services.gateway_controls import check_per_user_rpm

    redis = AsyncMock()
    redis.incr = AsyncMock(side_effect=ConnectionError("redis down"))

    # Should not raise
    await check_per_user_rpm(redis, uuid.uuid4(), "user-1", uuid.uuid4(), 60)


# ── Gateway health worker ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gateway_health_check_auto_disables_unhealthy_route():
    """Route with >5% error rate over 3 consecutive windows is auto-disabled."""
    import runledger_api.workers.gateway_health as _gh

    route_id = uuid.uuid4()
    route = SimpleNamespace(
        id=route_id,
        alias="gpt-4o",
        is_active=True,
        health_auto_disable=True,
        consecutive_health_failures=2,  # about to hit threshold
        disabled_reason=None,
    )

    # Health stats: 10 requests, 1 error → 10% → above threshold
    health_row = SimpleNamespace(total=10, errors=1)
    health_result = MagicMock()
    health_result.one.return_value = health_row

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=health_result)

    routes_result = MagicMock()
    routes_result.scalars.return_value.all.return_value = [route]

    call_count = 0

    async def _execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return routes_result
        return health_result

    mock_db.execute = AsyncMock(side_effect=_execute)
    mock_db.commit = AsyncMock()

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch.object(_gh, "_make_session_factory", return_value=factory):
        result = await _gh._run_health_check()

    # disabled=1 since route hits threshold (3)
    assert result["checked"] == 1
    assert result["disabled"] == 1


@pytest.mark.asyncio
async def test_gateway_health_check_recovers_route():
    """Route that was auto-disabled but is now healthy gets re-enabled."""
    import runledger_api.workers.gateway_health as _gh

    route = SimpleNamespace(
        id=uuid.uuid4(),
        alias="gpt-4o",
        is_active=False,
        health_auto_disable=True,
        consecutive_health_failures=5,
        disabled_reason="Auto-disabled: too many errors",
    )

    # Health stats: 20 requests, 0 errors → 0% → healthy
    health_row = SimpleNamespace(total=20, errors=0)
    health_result = MagicMock()
    health_result.one.return_value = health_row

    routes_result = MagicMock()
    routes_result.scalars.return_value.all.return_value = [route]

    call_count = 0

    async def _execute(stmt, *a, **kw):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return routes_result
        return health_result

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=_execute)
    mock_db.commit = AsyncMock()

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch.object(_gh, "_make_session_factory", return_value=factory):
        result = await _gh._run_health_check()

    assert result["recovered"] == 1
    assert result["disabled"] == 0
