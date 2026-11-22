"""Gateway cache keys, semantic scope and guardrail modify mapping (review G-05–G-08)."""

from __future__ import annotations

from types import SimpleNamespace

from runledger_api.routers.gateway_runtime import (
    _apply_modified_texts,
    _cache_params,
    _guardrail_texts,
    _semantic_scope,
)
from runledger_api.services.gateway import make_cache_key

MSGS = [{"role": "user", "content": "hi"}]


def test_cache_key_covers_output_affecting_params() -> None:
    base = make_cache_key("gpt-4o", MSGS, {})
    for params in (
        {"temperature": 0.7},
        {"tools": [{"type": "function", "function": {"name": "x"}}]},
        {"tool_choice": "required"},
        {"response_format": {"type": "json_object"}},
        {"seed": 1},
        {"max_tokens": 5},
    ):
        assert make_cache_key("gpt-4o", MSGS, params) != base, params
    assert make_cache_key("gpt-4o", MSGS, {"seed": 1}) == make_cache_key(
        "gpt-4o", MSGS, {"seed": 1}
    )


def test_cache_params_picks_only_relevant_fields() -> None:
    req = SimpleNamespace(
        model_dump=lambda exclude_none: {
            "model": "m",
            "messages": [],
            "temperature": 0.2,
            "metadata": {"a": 1},
        }
    )
    assert _cache_params(req) == {"temperature": 0.2}


def test_semantic_scope_is_per_caller_and_params() -> None:
    k1, k2 = SimpleNamespace(id="key-1"), SimpleNamespace(id="key-2")
    a = _semantic_scope(k1, "alice", {})
    assert a != _semantic_scope(k2, "alice", {})
    assert a != _semantic_scope(k1, "bob", {})
    assert a != _semantic_scope(k1, "alice", {"temperature": 1})
    assert a == _semantic_scope(k1, "alice", {})


def test_modify_rewrites_the_right_message() -> None:
    messages = [
        {"role": "system", "content": "be nice"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t1"}]},
        {"role": "tool", "content": None, "tool_call_id": "t1"},
        {"role": "user", "content": "my card is 4111"},
    ]
    positions, texts = _guardrail_texts(messages)
    assert positions == [0, 3] and texts == ["be nice", "my card is 4111"]
    _apply_modified_texts(
        messages,
        positions,
        [{"decision": "modify", "modified_texts": ["be nice", "my card is [REDACTED]"]}],
    )
    assert messages[3]["content"] == "my card is [REDACTED]"
    assert messages[1]["content"] == "" and messages[2]["content"] is None
    assert messages[0]["content"] == "be nice"
