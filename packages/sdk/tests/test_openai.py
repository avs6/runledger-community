"""
Tests for runledger_sdk.openai instrumentation.

Uses a fake openai module so no real openai package is required.
"""

from __future__ import annotations

import sys
import types
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

import runledger_sdk.openai as rl_openai
from runledger_sdk.context import RunLedgerContext, _run_id
from runledger_sdk.openai import (
    _build_provider_call,
    _build_provider_call_error,
    _build_run_end,
    _build_run_start,
)
from runledger_sdk.transport import SyncTransport

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_fake_openai() -> types.ModuleType:
    """Build a minimal fake openai module tree for patching."""
    openai_mod = types.ModuleType("openai")
    resources = types.ModuleType("openai.resources")
    chat = types.ModuleType("openai.resources.chat")
    completions = types.ModuleType("openai.resources.chat.completions")

    class Completions:
        _client = MagicMock(base_url="http://localhost:11434")

        def create(self, **kwargs: Any) -> Any:
            raise NotImplementedError

    class AsyncCompletions:
        _client = MagicMock(base_url="http://localhost:11434")

        async def create(self, **kwargs: Any) -> Any:
            raise NotImplementedError

    completions.Completions = Completions  # type: ignore[attr-defined]
    completions.AsyncCompletions = AsyncCompletions  # type: ignore[attr-defined]

    openai_mod.resources = resources  # type: ignore[attr-defined]
    resources.chat = chat  # type: ignore[attr-defined]
    chat.completions = completions  # type: ignore[attr-defined]

    return openai_mod


def _fake_usage(
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    cached_tokens: int | None = None,
) -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    if cached_tokens is not None:
        details = MagicMock()
        details.cached_tokens = cached_tokens
        usage.prompt_tokens_details = details
    else:
        usage.prompt_tokens_details = None
    return usage


def _fake_response(
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    cached_tokens: int | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.usage = _fake_usage(prompt_tokens, completion_tokens, cached_tokens)
    return resp


# ── _build_run_start ─────────────────────────────────────────────────────────


def test_build_run_start_minimal() -> None:
    run_id = str(uuid.uuid4())
    started = datetime.now(UTC)
    event = _build_run_start(run_id, {}, started)
    assert event["event_type"] == "run_start"
    assert event["run_id"] == run_id
    assert "end_user_id" not in event
    assert "feature_tag" not in event


def test_build_run_start_with_context() -> None:
    run_id = str(uuid.uuid4())
    ctx = {
        "end_user_id": "u1",
        "feature_tag": "chat",
        "session_id": None,
        "deployment_version": None,
        "run_id": run_id,
    }
    event = _build_run_start(run_id, ctx, datetime.now(UTC))
    assert event["end_user_id"] == "u1"
    assert event["feature_tag"] == "chat"
    assert "session_id" not in event


# ── _build_provider_call ─────────────────────────────────────────────────────


def test_build_provider_call_extracts_usage() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    event = _build_provider_call(run_id, span_id, "gpt-4o", resp, 250)
    assert event["event_type"] == "provider_call"
    assert event["provider"] == "openai"
    assert event["model"] == "gpt-4o"
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["latency_ms"] == 250
    assert event["status"] == "success"
    assert "cached_input_tokens" not in event


def test_build_provider_call_with_cached_tokens() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(200, 80, cached_tokens=50)
    event = _build_provider_call(run_id, span_id, "gpt-4o", resp, 300)
    assert event["cached_input_tokens"] == 50


# ── _build_provider_call — Phase 4: request ID + token details ───────────────


def test_build_provider_call_captures_request_id() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    resp.id = "chatcmpl-abc123"
    event = _build_provider_call(run_id, span_id, "gpt-4o", resp, 250)
    assert event["provider_request_id"] == "chatcmpl-abc123"


def test_build_provider_call_no_id_omits_field() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    resp.id = None
    event = _build_provider_call(run_id, span_id, "gpt-4o", resp, 250)
    assert "provider_request_id" not in event


def test_build_provider_call_captures_reasoning_tokens() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(200, 100)
    resp.id = "chatcmpl-xyz"
    comp_details = MagicMock()
    comp_details.reasoning_tokens = 40
    comp_details.audio_tokens = None
    comp_details.text_tokens = None
    resp.usage.completion_tokens_details = comp_details
    resp.usage.prompt_tokens_details = None
    event = _build_provider_call(run_id, span_id, "o1-preview", resp, 3000)
    assert event["output_tokens_details"] == {"reasoning_tokens": 40}
    assert "input_tokens_details" not in event


def test_build_provider_call_captures_input_token_details() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(500, 200, cached_tokens=300)
    resp.id = "chatcmpl-def"
    resp.usage.prompt_tokens_details.audio_tokens = None
    resp.usage.prompt_tokens_details.text_tokens = None
    resp.usage.completion_tokens_details = None
    event = _build_provider_call(run_id, span_id, "gpt-4o", resp, 1500)
    assert event["input_tokens_details"] == {"cached_tokens": 300}


# ── _build_provider_call_error ────────────────────────────────────────────────


def test_build_provider_call_error() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    exc = ValueError("rate limited")
    event = _build_provider_call_error(run_id, span_id, "gpt-4o", exc, 100)
    assert event["status"] == "error"
    assert event["error_type"] == "ValueError"


# ── _build_run_end ────────────────────────────────────────────────────────────


def test_build_run_end_success_with_totals() -> None:
    run_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    event = _build_run_end(run_id, "succeeded", resp)
    assert event["event_type"] == "run_end"
    assert event["status"] == "succeeded"
    assert event["total_input_tokens"] == 100
    assert event["total_output_tokens"] == 50


def test_build_run_end_failed_no_result() -> None:
    run_id = str(uuid.uuid4())
    event = _build_run_end(run_id, "failed", None)
    assert event["status"] == "failed"
    assert "total_input_tokens" not in event


# ── instrument_openai (sync patch) ────────────────────────────────────────────


def test_instrument_openai_patches_sync_create() -> None:
    rl_openai._patched = False  # reset
    fake = _make_fake_openai()

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.tool_enforcement = False
    transport.enqueue = lambda event: captured.append(event)

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "openai", fake)
        mp.setitem(sys.modules, "openai.resources", fake.resources)
        mp.setitem(sys.modules, "openai.resources.chat", fake.resources.chat)
        mp.setitem(
            sys.modules,
            "openai.resources.chat.completions",
            fake.resources.chat.completions,
        )

        # Give Completions.create a real implementation
        fake_resp = _fake_response(10, 5)

        def real_create(self: Any, **kwargs: Any) -> Any:
            return fake_resp

        fake.resources.chat.completions.Completions.create = real_create

        rl_openai.instrument_openai(transport)

        instance = fake.resources.chat.completions.Completions()
        _run_id.set(None)
        with RunLedgerContext(end_user_id="u_patch"):
            instance.create(model="gpt-4o", messages=[])

    rl_openai._patched = False  # reset after test

    event_types = [e["event_type"] for e in captured]
    assert "run_start" in event_types
    assert "provider_call" in event_types
    assert "run_end" in event_types

    pc = next(e for e in captured if e["event_type"] == "provider_call")
    assert pc["model"] == "gpt-4o"
    assert pc["input_tokens"] == 10
    assert pc["output_tokens"] == 5


def test_instrument_openai_captures_error() -> None:
    rl_openai._patched = False
    fake = _make_fake_openai()

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.enqueue = lambda event: captured.append(event)

    def failing_create(self: Any, **kwargs: Any) -> Any:
        raise ConnectionError("timeout")

    fake.resources.chat.completions.Completions.create = failing_create

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "openai", fake)
        mp.setitem(sys.modules, "openai.resources", fake.resources)
        mp.setitem(sys.modules, "openai.resources.chat", fake.resources.chat)
        mp.setitem(
            sys.modules,
            "openai.resources.chat.completions",
            fake.resources.chat.completions,
        )

        rl_openai.instrument_openai(transport)
        instance = fake.resources.chat.completions.Completions()
        _run_id.set(None)
        with pytest.raises(ConnectionError):
            instance.create(model="gpt-4o", messages=[])

    rl_openai._patched = False

    event_types = [e["event_type"] for e in captured]
    assert "run_start" in event_types
    assert "run_end" in event_types
    pc = next(e for e in captured if e["event_type"] == "provider_call")
    assert pc["status"] == "error"
    assert pc["error_type"] == "ConnectionError"

    run_end = next(e for e in captured if e["event_type"] == "run_end")
    assert run_end["status"] == "failed"


# ── instrument idempotency ────────────────────────────────────────────────────


def test_instrument_openai_is_idempotent() -> None:
    rl_openai._patched = False
    fake = _make_fake_openai()
    transport = MagicMock(spec=SyncTransport)

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "openai", fake)
        mp.setitem(sys.modules, "openai.resources", fake.resources)
        mp.setitem(sys.modules, "openai.resources.chat", fake.resources.chat)
        mp.setitem(
            sys.modules,
            "openai.resources.chat.completions",
            fake.resources.chat.completions,
        )

        rl_openai.instrument_openai(transport)
        first_create = fake.resources.chat.completions.Completions.create

        rl_openai.instrument_openai(transport)  # second call — no-op
        second_create = fake.resources.chat.completions.Completions.create

    assert first_create is second_create
    rl_openai._patched = False
