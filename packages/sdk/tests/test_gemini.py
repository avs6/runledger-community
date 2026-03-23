"""Tests for runledger_sdk.gemini instrumentation (google-genai v2)."""

from __future__ import annotations

import sys
import types
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

import runledger_sdk.gemini as rl_gemini
from runledger_sdk.context import RunLedgerContext, _run_id
from runledger_sdk.gemini import (
    _build_provider_call,
    _build_provider_call_error,
    _build_run_end,
    _extract_text,
    _extract_usage,
)
from runledger_sdk.transport import SyncTransport

# ── Fake google-genai module ──────────────────────────────────────────────────


def _make_fake_genai() -> tuple[types.ModuleType, types.ModuleType]:
    """Return (genai_top_mod, models_mod) with fake Models / AsyncModels classes."""
    genai_mod = types.ModuleType("google.genai")
    models_mod = types.ModuleType("google.genai.models")

    class Models:
        def generate_content(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

    class AsyncModels:
        async def generate_content(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

    models_mod.Models = Models  # type: ignore[attr-defined]
    models_mod.AsyncModels = AsyncModels  # type: ignore[attr-defined]
    genai_mod.models = models_mod  # type: ignore[attr-defined]
    return genai_mod, models_mod


def _fake_usage_meta(
    prompt_token_count: int = 100,
    candidates_token_count: int = 50,
    cached_content_token_count: int | None = None,
) -> MagicMock:
    meta = MagicMock()
    meta.prompt_token_count = prompt_token_count
    meta.candidates_token_count = candidates_token_count
    meta.cached_content_token_count = cached_content_token_count
    return meta


def _fake_response(
    prompt_tokens: int = 100,
    candidates_tokens: int = 50,
    text: str = "Hello from Gemini!",
    cached: int | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.usage_metadata = _fake_usage_meta(prompt_tokens, candidates_tokens, cached)
    resp.text = text
    resp.candidates = None
    return resp


# ── _extract_usage ────────────────────────────────────────────────────────────


def test_extract_usage_basic() -> None:
    resp = _fake_response(200, 80)
    in_tok, out_tok, cached = _extract_usage(resp)
    assert in_tok == 200
    assert out_tok == 80
    assert cached is None


def test_extract_usage_with_cache() -> None:
    resp = _fake_response(200, 80, cached=30)
    _, _, cached = _extract_usage(resp)
    assert cached == 30


def test_extract_usage_no_metadata() -> None:
    resp = MagicMock()
    resp.usage_metadata = None
    in_tok, out_tok, cached = _extract_usage(resp)
    assert in_tok is None and out_tok is None and cached is None


# ── _extract_text ─────────────────────────────────────────────────────────────


def test_extract_text_from_text_property() -> None:
    resp = _fake_response(text="Gemini says hi")
    assert _extract_text(resp) == "Gemini says hi"


def test_extract_text_none_when_missing() -> None:
    resp = MagicMock()
    resp.text = None
    resp.candidates = None
    assert _extract_text(resp) is None


# ── _build_provider_call ──────────────────────────────────────────────────────


def test_build_provider_call_extracts_usage() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    event = _build_provider_call(run_id, span_id, "gemini-2.0-flash", resp, 350)
    assert event["event_type"] == "provider_call"
    assert event["provider"] == "google"
    assert event["model"] == "gemini-2.0-flash"
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["latency_ms"] == 350
    assert event["status"] == "success"
    assert "cached_input_tokens" not in event


def test_build_provider_call_with_cache_tokens() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(200, 80, cached=40)
    event = _build_provider_call(run_id, span_id, "gemini-1.5-pro", resp, 400)
    assert event["cached_input_tokens"] == 40


# ── _build_provider_call_error ────────────────────────────────────────────────


def test_build_provider_call_error() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    exc = ConnectionError("quota exceeded")
    event = _build_provider_call_error(run_id, span_id, "gemini-2.0-flash", exc, 100)
    assert event["status"] == "error"
    assert event["error_type"] == "ConnectionError"
    assert event["provider"] == "google"


# ── _build_run_end ────────────────────────────────────────────────────────────


def test_build_run_end_success() -> None:
    run_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    event = _build_run_end(run_id, "succeeded", resp)
    assert event["status"] == "succeeded"
    assert event["total_input_tokens"] == 100
    assert event["total_output_tokens"] == 50


def test_build_run_end_failed_no_result() -> None:
    run_id = str(uuid.uuid4())
    event = _build_run_end(run_id, "failed", None)
    assert event["status"] == "failed"
    assert "total_input_tokens" not in event


# ── instrument_gemini (sync patch) ────────────────────────────────────────────


def test_instrument_gemini_patches_sync() -> None:
    rl_gemini._patched = False
    _, models_mod = _make_fake_genai()

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.enqueue = lambda e: captured.append(e)

    fake_resp = _fake_response(10, 5)

    def real_generate(self: Any, *args: Any, **kwargs: Any) -> Any:
        return fake_resp

    models_mod.Models.generate_content = real_generate

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "google.genai.models", models_mod)
        rl_gemini.instrument_gemini(transport)

        instance = models_mod.Models()
        _run_id.set(None)
        with RunLedgerContext(end_user_id="u_gemini"):
            instance.generate_content(model="gemini-2.0-flash", contents="Hi")

    rl_gemini._patched = False

    types_ = [e["event_type"] for e in captured]
    assert types_ == ["run_start", "span_start", "span_end", "provider_call", "run_end"]
    pc = next(e for e in captured if e["event_type"] == "provider_call")
    assert pc["provider"] == "google"
    assert pc["model"] == "gemini-2.0-flash"
    assert pc["input_tokens"] == 10


def test_instrument_gemini_captures_error() -> None:
    rl_gemini._patched = False
    _, models_mod = _make_fake_genai()

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.enqueue = lambda e: captured.append(e)

    def failing_generate(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise TimeoutError("deadline exceeded")

    models_mod.Models.generate_content = failing_generate

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "google.genai.models", models_mod)
        rl_gemini.instrument_gemini(transport)
        instance = models_mod.Models()
        _run_id.set(None)
        with pytest.raises(TimeoutError):
            instance.generate_content(model="gemini-2.0-flash", contents="Hi")

    rl_gemini._patched = False

    pc = next(e for e in captured if e["event_type"] == "provider_call")
    assert pc["status"] == "error"
    assert pc["error_type"] == "TimeoutError"
    re = next(e for e in captured if e["event_type"] == "run_end")
    assert re["status"] == "failed"


def test_instrument_gemini_is_idempotent() -> None:
    rl_gemini._patched = False
    _, models_mod = _make_fake_genai()
    transport = MagicMock(spec=SyncTransport)

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "google.genai.models", models_mod)
        rl_gemini.instrument_gemini(transport)
        first = models_mod.Models.generate_content
        rl_gemini.instrument_gemini(transport)
        second = models_mod.Models.generate_content

    assert first is second
    rl_gemini._patched = False
