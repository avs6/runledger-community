"""
Tests for production hardening.

Covers:
  Rate limiting — ingest (600/min), analytics (120/min), management (60/min)
  Rate limit fail-open on Redis error
  PII scrubbing — email, SSN, credit card, recursive dict
  Health probes — /health/live, /health/ready (ok + degraded)
  Metrics endpoint — /metrics token protection + plaintext export

15 tests total.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Scrubbing unit tests ───────────────────────────────────────────────────────


def test_scrub_value_email() -> None:
    """scrub_value() replaces email addresses with a typed placeholder (shared redactor, S-11)."""
    from runledger_api.services.scrubbing import scrub_value

    result = scrub_value("Contact us at user@example.com for help.")
    assert "[EMAIL]" in result
    assert "user@example.com" not in result


def test_scrub_value_ssn() -> None:
    """scrub_value() replaces SSN patterns with a typed placeholder (shared redactor, S-11)."""
    from runledger_api.services.scrubbing import scrub_value

    result = scrub_value("SSN: 123-45-6789")
    assert "[SSN]" in result
    assert "123-45-6789" not in result


def test_scrub_value_credit_card() -> None:
    """scrub_value() replaces credit card numbers with a typed placeholder (shared redactor, S-11)."""
    from runledger_api.services.scrubbing import scrub_value

    result = scrub_value("Card: 4111 1111 1111 1111")
    assert "[CARD]" in result
    assert "4111 1111 1111 1111" not in result


def test_scrub_dict_recursive() -> None:
    """scrub_dict() recursively scrubs all string values in nested dicts."""
    from runledger_api.services.scrubbing import scrub_dict

    d = {
        "name": "Alice",
        "email": "alice@example.com",
        "nested": {
            "card": "4111-1111-1111-1111",
            "count": 5,
        },
    }
    result = scrub_dict(d)
    assert result is not None
    assert "[EMAIL]" in result["email"]
    assert "alice@example.com" not in result["email"]
    assert "[CARD]" in result["nested"]["card"]
    assert result["nested"]["count"] == 5  # non-string unchanged
    assert result["name"] == "Alice"  # no PII, unchanged


def test_scrub_dict_none() -> None:
    """scrub_dict(None) returns None without error."""
    from runledger_api.services.scrubbing import scrub_dict

    assert scrub_dict(None) is None


# ── Health probe tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient) -> None:
    """GET /health/live always returns 200."""
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready_ok(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    """GET /health/ready returns 200 when DB and Redis are both reachable."""
    mock_db_session.execute = AsyncMock(return_value=None)
    mock_redis_client.ping = AsyncMock(return_value=True)

    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.asyncio
async def test_health_ready_degraded(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    """GET /health/ready returns 503 when Redis is unreachable."""
    mock_db_session.execute = AsyncMock(return_value=None)
    mock_redis_client.ping = AsyncMock(side_effect=Exception("Connection refused"))

    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["status"] == "degraded"
    assert detail["redis"] == "error"
    assert detail["db"] == "ok"


@pytest.mark.asyncio
async def test_metrics_requires_token(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /metrics rejects requests without the metrics bearer token, and is
    disabled (503) when no METRICS_TOKEN is set — no admin-secret fallback."""
    from runledger_api.core.config import settings  # noqa: PLC0415

    monkeypatch.setattr(settings, "metrics_token", "")
    assert (await client.get("/metrics", headers={"Authorization": "Bearer x"})).status_code == 503
    monkeypatch.setattr(settings, "metrics_token", "test-metrics-token")
    assert (await client.get("/metrics")).status_code == 401


@pytest.mark.asyncio
async def test_metrics_plaintext_export(
    client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /metrics returns the documented Prometheus-style gauges."""
    scalar_values = [
        3,
        datetime.now(UTC) - timedelta(seconds=42),
        120,
        20,
        80,
        20,
        4,
    ]

    def _result(value: object) -> MagicMock:
        result = MagicMock()
        result.scalar_one.return_value = value
        return result

    mock_db_session.execute = AsyncMock(side_effect=[_result(v) for v in scalar_values])
    mock_redis_client.llen = AsyncMock(side_effect=[5, 1, 0])

    from runledger_api.core.config import settings  # noqa: PLC0415

    monkeypatch.setattr(settings, "metrics_token", "test-metrics-token")
    resp = await client.get(
        "/metrics",
        headers={"Authorization": "Bearer test-metrics-token"},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    assert "runledger_uptime_seconds" in body
    assert "runledger_active_runs 3" in body
    assert "runledger_pipeline_lag_seconds" in body
    assert "runledger_provider_calls_last_hour 120" in body
    assert "runledger_gateway_requests_last_hour 80" in body
    assert 'runledger_celery_queue_depth{queue="celery"} 5' in body


# ── Rate limit tests ───────────────────────────────────────────────────────────


def _window(redis: AsyncMock, count: int | None = None, error: Exception | None = None) -> None:
    """Make the sliding-window pipeline report ``count`` hits in the window."""
    import time as _time

    pipe = MagicMock()
    if error is not None:
        pipe.execute = AsyncMock(side_effect=error)
    else:
        pipe.execute = AsyncMock(return_value=[0, 1, count, [("m", _time.time())], True])
    redis.pipeline = MagicMock(return_value=pipe)


@pytest.mark.asyncio
async def test_ingest_rate_limit_allows_under_limit(
    authed_client: AsyncClient,
    mock_redis_client: AsyncMock,
) -> None:
    """Under the 600/min ingest limit → request passes (202)."""
    _window(mock_redis_client, 1)

    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post(
            "/ingest/v1/events",
            headers={"Authorization": "Bearer test-key"},
            json={
                "event_type": "run_start",
                "run_id": str(uuid.uuid4()),
                "started_at": "2026-01-01T00:00:00Z",
            },
        )

    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_ingest_rate_limit_blocks_over_limit(
    authed_client: AsyncClient,
    mock_redis_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Over the 600/min ingest limit → request rejected (429) with Retry-After header."""
    from runledger_api.core.config import settings

    monkeypatch.setattr(settings, "ingest_rate_limit_per_minute", 600)
    _window(mock_redis_client, 601)

    resp = await authed_client.post(
        "/ingest/v1/events",
        headers={"Authorization": "Bearer test-key"},
        json={
            "event_type": "run_start",
            "run_id": str(uuid.uuid4()),
            "started_at": "2026-01-01T00:00:00Z",
        },
    )

    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_analytics_rate_limit_blocks(
    authed_client: AsyncClient,
    mock_redis_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Over the 120/min analytics limit → 429."""
    from runledger_api.core.config import settings

    monkeypatch.setattr(settings, "analytics_rate_limit_per_minute", 120)
    _window(mock_redis_client, 121)

    resp = await authed_client.get(
        "/analytics/summary",
        headers={"Authorization": "Bearer test-key"},
    )

    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_management_rate_limit_blocks(
    authed_client: AsyncClient,
    mock_redis_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Over the 60/min management limit → 429."""
    from runledger_api.core.config import settings

    monkeypatch.setattr(settings, "management_rate_limit_per_minute", 60)
    _window(mock_redis_client, 61)

    resp = await authed_client.get(
        "/budgets",
        headers={"Authorization": "Bearer test-key"},
    )

    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_fail_open(
    authed_client: AsyncClient,
    mock_redis_client: AsyncMock,
) -> None:
    """Redis error during rate limiting → request passes through (fail open, no 429)."""
    _window(mock_redis_client, error=Exception("Redis unavailable"))

    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post(
            "/ingest/v1/events",
            headers={"Authorization": "Bearer test-key"},
            json={
                "event_type": "run_start",
                "run_id": str(uuid.uuid4()),
                "started_at": "2026-01-01T00:00:00Z",
            },
        )

    assert resp.status_code != 429
