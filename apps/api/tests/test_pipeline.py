"""
Tests for the Celery pipeline — privacy mode enforcement.

Tests _apply_capture_policy() (pure function) and _get_capture_policy()
(DB helper) in isolation without spinning up a real Celery worker.

7 tests total.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── _apply_capture_policy (pure function) ─────────────────────────────────────


def test_full_mode_stores_metadata() -> None:
    """FULL privacy mode — metadata is persisted (after PII scrub)."""
    from runledger_api.workers.pipeline import _apply_capture_policy

    raw = {"messages": [{"role": "user", "content": "Hello"}], "response": "Hi"}
    result = _apply_capture_policy("FULL", 1.0, raw, "succeeded")

    assert result is not None
    assert result["response"] == "Hi"
    assert result["messages"][0]["content"] == "Hello"


def test_metadata_only_drops_payload() -> None:
    """METADATA_ONLY (default) — payload is never persisted."""
    from runledger_api.workers.pipeline import _apply_capture_policy

    raw = {"messages": [{"role": "user", "content": "Secret prompt"}], "response": "data"}
    result = _apply_capture_policy("METADATA_ONLY", 0.0, raw, "succeeded")

    assert result is None


def test_errors_only_stores_on_failure() -> None:
    """ERRORS_ONLY — metadata persisted when status is 'failed'."""
    from runledger_api.workers.pipeline import _apply_capture_policy

    raw = {"messages": [], "response": "error output"}
    result = _apply_capture_policy("ERRORS_ONLY", 0.0, raw, "failed")

    assert result is not None


def test_errors_only_suppresses_on_success() -> None:
    """ERRORS_ONLY — metadata NOT persisted when status is 'succeeded'."""
    from runledger_api.workers.pipeline import _apply_capture_policy

    raw = {"messages": [], "response": "ok"}
    result = _apply_capture_policy("ERRORS_ONLY", 0.0, raw, "succeeded")

    assert result is None


def test_sampled_stores_when_rate_is_one() -> None:
    """SAMPLED at rate=1.0 — always stores (100% sample rate)."""
    from runledger_api.workers.pipeline import _apply_capture_policy

    raw = {"messages": [], "response": "sampled"}
    result = _apply_capture_policy("SAMPLED", 1.0, raw, "succeeded")

    assert result is not None


def test_sampled_suppresses_when_rate_is_zero() -> None:
    """SAMPLED at rate=0.0 — never stores (0% sample rate)."""
    from runledger_api.workers.pipeline import _apply_capture_policy

    raw = {"messages": [], "response": "suppressed"}
    result = _apply_capture_policy("SAMPLED", 0.0, raw, "succeeded")

    assert result is None


def test_full_mode_pii_scrubbed() -> None:
    """FULL mode runs PII scrubbing — email addresses are redacted."""
    from runledger_api.workers.pipeline import _apply_capture_policy

    raw = {
        "messages": [{"role": "user", "content": "My email is secret@example.com"}],
        "response": "Got it",
    }
    result = _apply_capture_policy("FULL", 1.0, raw, "succeeded")

    assert result is not None
    assert "secret@example.com" not in result["messages"][0]["content"]
    assert "[REDACTED]" in result["messages"][0]["content"]


# ── _get_capture_policy (DB helper) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_capture_policy_returns_full_mode() -> None:
    """Returns FULL mode and sampled_rate from DB row."""
    from runledger_api.workers.pipeline import _get_capture_policy

    policy_row = SimpleNamespace(privacy_mode="FULL", sampled_rate=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=policy_row)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    mode, rate = await _get_capture_policy(session, str(uuid.uuid4()))

    assert mode == "FULL"
    assert rate == 0.1  # default when sampled_rate is None


@pytest.mark.asyncio
async def test_get_capture_policy_defaults_when_no_row() -> None:
    """Falls back to METADATA_ONLY when no policy row exists."""
    from runledger_api.workers.pipeline import _get_capture_policy

    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    mode, rate = await _get_capture_policy(session, str(uuid.uuid4()))

    assert mode == "METADATA_ONLY"
    assert rate == 0.0


@pytest.mark.asyncio
async def test_get_capture_policy_fails_open_on_db_error() -> None:
    """Returns METADATA_ONLY when the DB lookup raises an exception (fail open)."""
    from runledger_api.workers.pipeline import _get_capture_policy

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=Exception("DB unavailable"))

    mode, rate = await _get_capture_policy(session, str(uuid.uuid4()))

    assert mode == "METADATA_ONLY"
    assert rate == 0.0
