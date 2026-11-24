"""Stream W1-B: prompt refs (B-23), decision trace (ENH), cache profile (G-09),
request memo (cd:gw-perf) and pass-through redirects (G-15)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from runledger_api.services.gateway_cache import CacheProfile, _to_profile
from runledger_api.services.gateway_decision import DecisionTrace
from runledger_api.services.gateway_hotpath import (
    TTLCache,
    is_missing,
    memo_get,
    memo_put,
    request_memo,
)
from runledger_api.services.gateway_prompts import parse_prompt_ref, render_prompt


def test_prompt_ref_forms() -> None:
    assert parse_prompt_ref("triage").environment is None
    assert parse_prompt_ref("triage@prod").environment == "production"
    assert parse_prompt_ref("triage@dev").environment == "development"
    assert parse_prompt_ref("triage@canary").environment == "canary"
    assert parse_prompt_ref("triage@3").version == 3
    assert parse_prompt_ref("triage@v7").version == 7
    with pytest.raises(HTTPException) as exc:
        parse_prompt_ref("a@b@c")
    assert exc.value.status_code == 422


def test_render_prompt_reports_missing_variables() -> None:
    text, missing = render_prompt("Hi {{ name }}, {{product}} {{name}}", {"name": "Ada"})
    assert text == "Hi Ada, {{product}} Ada"
    assert missing == ["product"]


def test_decision_header_and_dict() -> None:
    trace = DecisionTrace(request_id=uuid.uuid4(), model_requested="chat")
    trace.cache = {"exact": "miss", "semantic": "off"}
    trace.budget = {"status": "downgrade", "budget_id": "b1"}
    trace.guardrail = {"pre_call": "modify", "checked": 2}
    trace.prompt = {"prompt_name": "triage", "prompt_version": 2}
    assert trace.header() == "cache=miss; budget=downgrade; guardrail=modified; prompt=triage@2"
    data = trace.as_dict()
    assert data["cache"]["result"] == "miss"
    assert data["guardrail"]["result"] == "modified"
    assert data["prompt"]["prompt_version"] == 2

    hit = DecisionTrace(request_id=uuid.uuid4(), model_requested="chat")
    hit.cache = {"exact": "hit"}
    hit.guardrail = {"pre_call": "off"}
    assert hit.header().startswith("route=cache; cache=exact")


def test_cache_profile_enforces_enabled_and_scope() -> None:
    assert CacheProfile().allows("anything")
    assert not CacheProfile(is_enabled=False).allows("chat")
    scoped = CacheProfile(scope_models=frozenset({"chat"}))
    assert scoped.allows("chat") and not scoped.allows("other")
    row = SimpleNamespace(
        id=uuid.uuid4(),
        is_enabled=True,
        ttl_seconds=60,
        max_entries=5,
        eviction_policy="'lfu'",
        similarity_threshold=0.9,
        scope_models=["chat"],
    )
    profile = _to_profile(row)  # type: ignore[arg-type]
    assert profile.eviction_policy == "lfu"
    assert profile.ttl_seconds == 60 and profile.max_entries == 5
    assert profile.similarity_threshold == pytest.approx(0.9)


def test_request_memo_is_scoped() -> None:
    assert is_missing(memo_get("k"))
    memo_put("k", 1)  # no memo active: ignored
    assert is_missing(memo_get("k"))
    with request_memo():
        memo_put("k", [1])
        assert memo_get("k") == [1]
        with request_memo():  # nested reuses the outer memo
            assert memo_get("k") == [1]
    assert is_missing(memo_get("k"))


def test_ttl_cache_expiry_and_zero_ttl() -> None:
    cache = TTLCache(max_items=2)
    cache.put("a", 1, ttl=60)
    assert cache.get("a") == 1
    cache.put("b", 2, ttl=0)  # disabled
    assert is_missing(cache.get("b"))
    cache.put("c", 3, ttl=-1)
    assert is_missing(cache.get("c"))


def test_passthrough_never_follows_redirects() -> None:
    import inspect  # noqa: PLC0415

    from runledger_api.routers import gateway_passthrough  # noqa: PLC0415

    source = inspect.getsource(gateway_passthrough)
    assert "follow_redirects=True" not in source
    assert source.count("follow_redirects=False") == 2
