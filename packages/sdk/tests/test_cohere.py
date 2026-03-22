"""Tests for runledger_sdk.cohere instrumentation."""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

import runledger_sdk.cohere as rl_cohere
from runledger_sdk.cohere import (
    _build_provider_call,
    _build_provider_call_error,
    _build_run_end,
    _extract_text,
    _extract_usage,
)
from runledger_sdk.transport import SyncTransport


# ── Helpers ────────────────────────────────────────────────────────────────────


def _fake_response(
    input_tokens: int = 100,
    output_tokens: int = 50,
    text: str = "Command!",
) -> MagicMock:
    resp = MagicMock()
    # v5 token structure
    tokens = MagicMock()
    tokens.input_tokens = input_tokens
    tokens.output_tokens = output_tokens
    resp.usage = MagicMock()
    resp.usage.tokens = tokens
    resp.usage.billed_units = None
    # message content
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text
    resp.message = MagicMock()
    resp.message.content = [content_block]
    return resp


# ── _extract_usage ─────────────────────────────────────────────────────────────


def test_extract_usage_from_tokens() -> None:
    resp = _fake_response(200, 80)
    in_tok, out_tok = _extract_usage(resp)
    assert in_tok == 200
    assert out_tok == 80


def test_extract_usage_falls_back_to_billed_units() -> None:
    resp = MagicMock()
    resp.usage = MagicMock()
    resp.usage.tokens = None
    billed = MagicMock()
    billed.input_tokens = 150
    billed.output_tokens = 60
    resp.usage.billed_units = billed
    in_tok, out_tok = _extract_usage(resp)
    assert in_tok == 150
    assert out_tok == 60


def test_extract_usage_no_usage() -> None:
    resp = MagicMock()
    resp.usage = None
    in_tok, out_tok = _extract_usage(resp)
    assert in_tok is None
    assert out_tok is None


# ── _extract_text ──────────────────────────────────────────────────────────────


def test_extract_text() -> None:
    resp = _fake_response(text="Hello Cohere")
    assert _extract_text(resp) == "Hello Cohere"


def test_extract_text_none_when_no_content() -> None:
    resp = MagicMock()
    resp.message = None
    assert _extract_text(resp) is None


# ── _build_provider_call ───────────────────────────────────────────────────────


def test_build_provider_call_tokens() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    event = _build_provider_call(run_id, span_id, "command-r-plus", resp, 400)
    assert event["provider"] == "cohere"
    assert event["model"] == "command-r-plus"
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["status"] == "success"


def test_build_provider_call_error() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    exc = RuntimeError("API unavailable")
    event = _build_provider_call_error(run_id, span_id, "command-r", exc, 50)
    assert event["status"] == "error"
    assert event["error_type"] == "RuntimeError"
    assert event["provider"] == "cohere"


def test_build_run_end_tokens() -> None:
    run_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    event = _build_run_end(run_id, "succeeded", resp)
    assert event["total_input_tokens"] == 100
    assert event["total_output_tokens"] == 50


# ── instrument_cohere with fake ClientV2 ──────────────────────────────────────


def test_instrument_cohere_with_fake_client() -> None:
    """Test that instrument_cohere patches a fake ClientV2 correctly."""
    rl_cohere._patched = False

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.enqueue = lambda e: captured.append(e)

    fake_resp = _fake_response(20, 10)

    import types  # noqa: PLC0415

    class FakeClientV2:
        def chat(self, *args: Any, **kwargs: Any) -> Any:
            return fake_resp

    fake_cohere_mod = types.ModuleType("cohere")
    fake_cohere_mod.ClientV2 = FakeClientV2  # type: ignore[attr-defined]
    fake_cohere_mod.AsyncClientV2 = None  # type: ignore[attr-defined]

    import sys  # noqa: PLC0415
    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "cohere", fake_cohere_mod)
        rl_cohere.instrument_cohere(transport)

        client = FakeClientV2()
        result = client.chat(model="command-r-plus", messages=[{"role": "user", "content": "Hi"}])

    rl_cohere._patched = False

    assert result is fake_resp
    types_ = [e["event_type"] for e in captured]
    assert "run_start" in types_
    assert "provider_call" in types_
    assert "run_end" in types_

    pc = next(e for e in captured if e["event_type"] == "provider_call")
    assert pc["provider"] == "cohere"
    assert pc["model"] == "command-r-plus"
    assert pc["input_tokens"] == 20


def test_instrument_cohere_skips_when_package_missing() -> None:
    rl_cohere._patched = False
    transport = MagicMock(spec=SyncTransport)

    import sys  # noqa: PLC0415
    import builtins  # noqa: PLC0415

    real_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "cohere":
            raise ImportError("No module named 'cohere'")
        return real_import(name, *args, **kwargs)

    with pytest.MonkeyPatch().context() as mp:
        mp.delitem(sys.modules, "cohere", raising=False)
        mp.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="cohere"):
            rl_cohere.instrument_cohere(transport)

    rl_cohere._patched = False
