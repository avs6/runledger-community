"""
Tests for runledger_sdk.anthropic instrumentation.

Uses a fake anthropic module so no real anthropic package is required.
"""

from __future__ import annotations

import sys
import types
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

import runledger_sdk.anthropic as rl_anthropic
from runledger_sdk.anthropic import (
    _build_messages_payload,
    _build_provider_call,
    _build_provider_call_error,
    _build_run_end,
    _build_run_start,
)
from runledger_sdk.context import RunLedgerContext, _run_id
from runledger_sdk.mcp import _infer_tool_type, instrument_mcp_session
from runledger_sdk.transport import SyncTransport

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_fake_anthropic() -> types.ModuleType:
    """Build a minimal fake anthropic module tree for patching."""
    anthropic_mod = types.ModuleType("anthropic")
    resources = types.ModuleType("anthropic.resources")
    messages_mod = types.ModuleType("anthropic.resources.messages")

    class Messages:
        def create(self, **kwargs: Any) -> Any:
            raise NotImplementedError

    class AsyncMessages:
        async def create(self, **kwargs: Any) -> Any:
            raise NotImplementedError

    messages_mod.Messages = Messages  # type: ignore[attr-defined]
    messages_mod.AsyncMessages = AsyncMessages  # type: ignore[attr-defined]

    anthropic_mod.resources = resources  # type: ignore[attr-defined]
    resources.messages = messages_mod  # type: ignore[attr-defined]

    return anthropic_mod


def _fake_usage(
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read_input_tokens: int | None = None,
    cache_creation_input_tokens: int | None = None,
) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = cache_read_input_tokens
    usage.cache_creation_input_tokens = cache_creation_input_tokens
    return usage


def _fake_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _fake_tool_use_block(name: str) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    return block


def _fake_response(
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read_input_tokens: int | None = None,
    cache_creation_input_tokens: int | None = None,
    text: str = "Paris is the capital of France.",
) -> MagicMock:
    resp = MagicMock()
    resp.usage = _fake_usage(
        input_tokens,
        output_tokens,
        cache_read_input_tokens,
        cache_creation_input_tokens,
    )
    resp.content = [_fake_text_block(text)]
    resp.stop_reason = "end_turn"
    return resp


# ── _build_run_start ──────────────────────────────────────────────────────────


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
        "feature_tag": "anthropic-demo",
        "session_id": None,
        "deployment_version": None,
        "run_id": run_id,
    }
    event = _build_run_start(run_id, ctx, datetime.now(UTC))
    assert event["end_user_id"] == "u1"
    assert event["feature_tag"] == "anthropic-demo"
    assert "session_id" not in event


# ── _build_provider_call ──────────────────────────────────────────────────────


def test_build_provider_call_extracts_usage() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    event = _build_provider_call(run_id, span_id, "claude-3-haiku-20240307", resp, 250)
    assert event["event_type"] == "provider_call"
    assert event["provider"] == "anthropic"
    assert event["model"] == "claude-3-haiku-20240307"
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["latency_ms"] == 250
    assert event["status"] == "success"
    assert "cached_input_tokens" not in event


def test_build_provider_call_with_cache_read_tokens() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(200, 80, cache_read_input_tokens=40)
    event = _build_provider_call(
        run_id, span_id, "claude-3-5-sonnet-20241022", resp, 300
    )
    assert event["cached_input_tokens"] == 40


# ── _build_provider_call — Phase 4: request ID + token details ────────────────


def test_build_provider_call_captures_message_id() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    resp.id = "msg_01XxYy"
    event = _build_provider_call(
        run_id, span_id, "claude-3-5-sonnet-20241022", resp, 300
    )
    assert event["provider_request_id"] == "msg_01XxYy"


def test_build_provider_call_no_id_omits_field() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(100, 50)
    resp.id = None
    event = _build_provider_call(run_id, span_id, "claude-3-haiku-20240307", resp, 250)
    assert "provider_request_id" not in event


def test_build_provider_call_captures_cache_write_tokens_in_details() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    resp = _fake_response(
        200, 80, cache_read_input_tokens=40, cache_creation_input_tokens=160
    )
    resp.id = "msg_01abc"
    event = _build_provider_call(
        run_id, span_id, "claude-3-5-sonnet-20241022", resp, 500
    )
    assert event["cached_input_tokens"] == 40
    assert event["input_tokens_details"] == {
        "cached_tokens": 40,
        "cache_creation_tokens": 160,
    }


# ── _build_provider_call_error ────────────────────────────────────────────────


def test_build_provider_call_error() -> None:
    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    exc = ValueError("rate limited")
    event = _build_provider_call_error(
        run_id, span_id, "claude-3-haiku-20240307", exc, 100
    )
    assert event["status"] == "error"
    assert event["error_type"] == "ValueError"
    assert event["provider"] == "anthropic"


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


# ── _build_messages_payload ────────────────────────────────────────────────────


def test_build_messages_payload_system_string_prepended() -> None:
    kwargs: dict[str, Any] = {
        "messages": [{"role": "user", "content": "Hello"}],
        "system": "You are a helpful assistant.",
    }
    result = _build_messages_payload(kwargs)
    assert result[0] == {"role": "system", "content": "You are a helpful assistant."}
    assert result[1] == {"role": "user", "content": "Hello"}


def test_build_messages_payload_system_list_prepended() -> None:
    kwargs: dict[str, Any] = {
        "messages": [{"role": "user", "content": "Hello"}],
        "system": [{"type": "text", "text": "Be concise."}],
    }
    result = _build_messages_payload(kwargs)
    assert result[0]["role"] == "system"
    assert "Be concise." in result[0]["content"]


def test_build_messages_payload_no_system() -> None:
    kwargs: dict[str, Any] = {
        "messages": [{"role": "user", "content": "Hi"}],
    }
    result = _build_messages_payload(kwargs)
    assert len(result) == 1
    assert result[0]["role"] == "user"


# ── instrument_anthropic (sync patch) ─────────────────────────────────────────


def test_instrument_anthropic_patches_sync_create() -> None:
    rl_anthropic._patched = False  # reset
    fake = _make_fake_anthropic()

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.enqueue = lambda event: captured.append(event)

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "anthropic", fake)
        mp.setitem(sys.modules, "anthropic.resources", fake.resources)
        mp.setitem(sys.modules, "anthropic.resources.messages", fake.resources.messages)

        fake_resp = _fake_response(10, 5)

        def real_create(self: Any, **kwargs: Any) -> Any:
            return fake_resp

        fake.resources.messages.Messages.create = real_create

        rl_anthropic.instrument_anthropic(transport)

        instance = fake.resources.messages.Messages()
        _run_id.set(None)
        with RunLedgerContext(end_user_id="u_patch"):
            instance.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": "Hi"}],
            )

    rl_anthropic._patched = False  # reset after test

    event_types = [e["event_type"] for e in captured]
    assert "run_start" in event_types
    assert "span_start" in event_types
    assert "span_end" in event_types
    assert "provider_call" in event_types
    assert "run_end" in event_types

    pc = next(e for e in captured if e["event_type"] == "provider_call")
    assert pc["model"] == "claude-3-haiku-20240307"
    assert pc["input_tokens"] == 10
    assert pc["output_tokens"] == 5
    assert pc["provider"] == "anthropic"


def test_instrument_anthropic_captures_error() -> None:
    rl_anthropic._patched = False
    fake = _make_fake_anthropic()

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.enqueue = lambda event: captured.append(event)

    def failing_create(self: Any, **kwargs: Any) -> Any:
        raise ConnectionError("timeout")

    fake.resources.messages.Messages.create = failing_create

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "anthropic", fake)
        mp.setitem(sys.modules, "anthropic.resources", fake.resources)
        mp.setitem(sys.modules, "anthropic.resources.messages", fake.resources.messages)

        rl_anthropic.instrument_anthropic(transport)
        instance = fake.resources.messages.Messages()
        _run_id.set(None)
        with pytest.raises(ConnectionError):
            instance.create(model="claude-3-haiku-20240307", messages=[])

    rl_anthropic._patched = False

    event_types = [e["event_type"] for e in captured]
    assert "run_start" in event_types
    assert "run_end" in event_types
    pc = next(e for e in captured if e["event_type"] == "provider_call")
    assert pc["status"] == "error"
    assert pc["error_type"] == "ConnectionError"

    run_end = next(e for e in captured if e["event_type"] == "run_end")
    assert run_end["status"] == "failed"


def test_instrument_anthropic_is_idempotent() -> None:
    rl_anthropic._patched = False
    fake = _make_fake_anthropic()
    transport = MagicMock(spec=SyncTransport)

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "anthropic", fake)
        mp.setitem(sys.modules, "anthropic.resources", fake.resources)
        mp.setitem(sys.modules, "anthropic.resources.messages", fake.resources.messages)

        rl_anthropic.instrument_anthropic(transport)
        first_create = fake.resources.messages.Messages.create

        rl_anthropic.instrument_anthropic(transport)  # second call — no-op
        second_create = fake.resources.messages.Messages.create

    assert first_create is second_create
    rl_anthropic._patched = False


def test_uninstrument_anthropic_restores_original() -> None:
    rl_anthropic._patched = False
    fake = _make_fake_anthropic()

    original_create = fake.resources.messages.Messages.create
    transport = MagicMock(spec=SyncTransport)

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "anthropic", fake)
        mp.setitem(sys.modules, "anthropic.resources", fake.resources)
        mp.setitem(sys.modules, "anthropic.resources.messages", fake.resources.messages)

        rl_anthropic.instrument_anthropic(transport)
        assert fake.resources.messages.Messages.create is not original_create

        rl_anthropic.uninstrument_anthropic()
        assert fake.resources.messages.Messages.create is original_create
        assert rl_anthropic._patched is False


# ── Event ordering ────────────────────────────────────────────────────────────


def test_instrument_anthropic_event_order() -> None:
    """Events must arrive in the correct order: run_start, span_start, span_end, provider_call, run_end."""
    rl_anthropic._patched = False
    fake = _make_fake_anthropic()

    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.budget_check = False
    transport.enqueue = lambda event: captured.append(event)

    fake_resp = _fake_response(10, 5)

    def real_create(self: Any, **kwargs: Any) -> Any:
        return fake_resp

    fake.resources.messages.Messages.create = real_create

    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "anthropic", fake)
        mp.setitem(sys.modules, "anthropic.resources", fake.resources)
        mp.setitem(sys.modules, "anthropic.resources.messages", fake.resources.messages)

        rl_anthropic.instrument_anthropic(transport)
        instance = fake.resources.messages.Messages()
        _run_id.set(None)
        instance.create(model="claude-3-5-sonnet-20241022", messages=[])

    rl_anthropic._patched = False

    event_types = [e["event_type"] for e in captured]
    assert event_types == [
        "run_start",
        "span_start",
        "span_end",
        "provider_call",
        "run_end",
    ]


# ── MCP tool type inference ────────────────────────────────────────────────────


def test_infer_tool_type_read() -> None:
    assert _infer_tool_type("get_file") == "read"
    assert _infer_tool_type("list_directory") == "read"
    assert _infer_tool_type("search_database") == "read"


def test_infer_tool_type_write() -> None:
    assert _infer_tool_type("write_file") == "write"
    assert _infer_tool_type("create_record") == "write"
    assert _infer_tool_type("delete_entry") == "write"
    assert _infer_tool_type("update_config") == "write"
    assert _infer_tool_type("send_message") == "write"


def test_infer_tool_type_privileged() -> None:
    assert _infer_tool_type("execute_query") == "privileged"
    assert _infer_tool_type("run_script") == "privileged"
    assert _infer_tool_type("bash_command") == "privileged"
    assert _infer_tool_type("admin_reset") == "privileged"
    assert _infer_tool_type("deploy_service") == "privileged"


# ── instrument_mcp_session ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_instrument_mcp_session_patches_call_tool() -> None:
    """instrument_mcp_session patches call_tool and emits a tool_call event."""
    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.enqueue = lambda event: captured.append(event)

    # Build a minimal fake session
    class FakeSession:
        async def call_tool(
            self, name: str, arguments: dict[str, Any] | None = None, **kwargs: Any
        ) -> Any:
            return {"result": "ok"}

    session = FakeSession()
    instrument_mcp_session(session, transport)

    _run_id.set(None)
    with RunLedgerContext(end_user_id="u_mcp"):
        result = await session.call_tool("search_web", {"query": "test"})

    assert result == {"result": "ok"}
    assert len(captured) == 1
    event = captured[0]
    assert event["event_type"] == "tool_call"
    assert event["tool_name"] == "search_web"
    assert event["tool_type"] == "read"
    assert event["status"] == "success"
    assert event["duration_ms"] >= 0
    assert "tool_call_id" in event


@pytest.mark.asyncio
async def test_instrument_mcp_session_captures_error() -> None:
    """instrument_mcp_session captures errors and emits tool_call with status=error."""
    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.enqueue = lambda event: captured.append(event)

    class FakeSession:
        async def call_tool(
            self, name: str, arguments: dict[str, Any] | None = None, **kwargs: Any
        ) -> Any:
            raise RuntimeError("tool failed")

    session = FakeSession()
    instrument_mcp_session(session, transport)

    _run_id.set(None)
    with pytest.raises(RuntimeError):
        await session.call_tool("execute_code", {"code": "bad"})

    assert len(captured) == 1
    event = captured[0]
    assert event["status"] == "error"
    assert event["error_type"] == "RuntimeError"
    assert event["tool_type"] == "privileged"  # "execute" keyword
