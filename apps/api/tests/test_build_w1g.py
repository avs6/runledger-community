"""W1-G Build stream: gateway client, experiment runner, judge, prompt governance,
diff, runbook export (review B-02, B-03, B-05, B-07, B-08, B-09, B-12, B-13)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from runledger_api.services import gateway_client
from runledger_api.services.gateway_client import GatewayCallResult

# ── Gateway client ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_completion_posts_to_gateway_with_caller_key() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["tags"] = request.headers.get("x-runledger-tags")
        seen["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "id": "resp_1",
                "model": "gpt-4o-mini",
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 2},
            },
            headers={"x-runledger-cache": "exact"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await gateway_client.chat_completion(
            "Bearer k1",
            model="fast",
            messages=[{"role": "user", "content": "hi"}],
            metadata={"feature_tag": "playground"},
            tags=["playground"],
            client=client,
        )
    assert seen["url"].endswith("/gateway/chat/completions")
    assert seen["auth"] == "Bearer k1"
    assert seen["tags"] == "playground"
    assert b"runledger.request_ref" in seen["body"]
    assert result.ok and result.text == "hello"
    assert (result.input_tokens, result.output_tokens) == (7, 2)
    assert result.cache == "exact"


@pytest.mark.asyncio
async def test_chat_completion_reports_refusals_without_raising() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "budget exceeded"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await gateway_client.chat_completion(
            "Bearer k", model="fast", messages=[], client=client
        )
    assert not result.ok
    assert result.status_code == 429
    assert result.error == "budget exceeded"


@pytest.mark.asyncio
async def test_chat_completion_unreachable_gateway_is_503() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await gateway_client.chat_completion(
            "Bearer k", model="fast", messages=[], client=client
        )
    assert not result.ok and result.status_code == 503
    assert "unreachable" in (result.error or "")


def test_bearer_from_headers() -> None:
    assert gateway_client.bearer_from_headers({"authorization": "Bearer x"}) == "Bearer x"
    assert gateway_client.bearer_from_headers({"authorization": "Basic x"}) is None
    assert gateway_client.bearer_from_headers({}) is None


# ── Experiment runner ──────────────────────────────────────────────────────────


def test_item_messages_and_templates() -> None:
    from runledger_api.services.experiments import expected_match, item_messages

    msgs = item_messages(
        {"input": "2+2?", "metadata": {"variables": {"tone": "terse"}}},
        "eval",
        "Be {{tone}}. Unknown {{x}}",
    )
    assert msgs == [
        {"role": "system", "content": "Be terse. Unknown {{x}}"},
        {"role": "user", "content": "2+2?"},
    ]
    replay = item_messages({"messages": [{"role": "user", "content": "hi"}]}, "replay", None)
    assert replay == [{"role": "user", "content": "hi"}]
    assert item_messages({"input": "x"}, "replay", None) is None
    assert expected_match("The answer is 4.", "4") == 1.0
    assert expected_match("five", "4") == 0.0
    assert expected_match("x", None) is None


def _dataset(ws: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws,
        items=[
            {"input": "2+2?", "expected_output": "4"},
            {"input": "capital of France?", "expected_output": "Paris"},
        ],
    )


@pytest.mark.asyncio
async def test_execute_experiment_runs_every_item_through_gateway_and_scores() -> None:
    from runledger_api.services.experiments import execute_experiment

    ws = uuid.uuid4()
    ds = _dataset(ws)
    exp = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws,
        dataset_id=ds.id,
        mode="eval",
        models=[{"model": "big"}, {"model": "small"}],
        prompt_name=None,
        prompt_version=None,
        evaluator_ids=[],
        status="pending",
        results=None,
        run_count=0,
        scores_created=0,
        started_at=None,
        completed_at=None,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=ds)
    db.add = MagicMock()

    answers = {"big": {"2+2?": "4", "capital of France?": "Paris"}, "small": {"2+2?": "4"}}
    calls: list[str] = []

    async def fake_chat(authorization, *, model, messages, **kw):
        calls.append(model)
        assert authorization == "Bearer caller"
        assert kw["metadata"]["feature_tag"] == "experiment"
        question = messages[-1]["content"]
        return GatewayCallResult(
            ok=True,
            status_code=200,
            model=model,
            request_ref="r",
            text=answers[model].get(question, "no idea"),
            input_tokens=10,
            output_tokens=2,
            latency_ms=100 if model == "big" else 50,
            cost_usd=Decimal("0.002") if model == "big" else Decimal("0.0005"),
        )

    with (
        patch.object(gateway_client, "chat_completion", side_effect=fake_chat),
        patch.object(gateway_client, "attach_run", AsyncMock(side_effect=lambda _d, _w, r: r)),
    ):
        out = await execute_experiment(db, exp, "Bearer caller")

    assert out.status == "completed"
    assert sorted(calls) == ["big", "big", "small", "small"]
    res = out.results
    assert res["summary"]["calls"] == 4 and res["summary"]["via"] == "gateway"
    rows = {r["model"]: r for r in res["models"]}
    assert rows["big"]["avg_score"] == 1.0
    assert rows["small"]["avg_score"] == 0.5
    assert res["deltas"][0]["score_delta"] == -0.5
    assert len(res["items"]) == 2 and len(res["items"][0]["outputs"]) == 2


@pytest.mark.asyncio
async def test_execute_experiment_without_models_fails_cleanly() -> None:
    from runledger_api.services.experiments import execute_experiment

    ws = uuid.uuid4()
    ds = _dataset(ws)
    exp = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws,
        dataset_id=ds.id,
        mode="eval",
        models=[],
        prompt_name=None,
        prompt_version=None,
        evaluator_ids=[],
        status="pending",
        results=None,
        run_count=0,
        scores_created=0,
        started_at=None,
        completed_at=None,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=ds)
    out = await execute_experiment(db, exp, "Bearer caller")
    assert out.status == "failed"
    assert "no models" in out.results["error"]


def test_pick_recommendation_prefers_cheaper_model_holding_quality() -> None:
    from runledger_api.services.experiments import pick_recommendation

    results = {
        "models": [
            {"model": "big", "items_run": 10, "avg_score": 0.90, "avg_cost_usd": "0.01"},
            {"model": "mid", "items_run": 10, "avg_score": 0.89, "avg_cost_usd": "0.004"},
            {"model": "tiny", "items_run": 10, "avg_score": 0.60, "avg_cost_usd": "0.001"},
        ]
    }
    picked = pick_recommendation(results)
    assert picked is not None
    assert picked[1]["model"] == "mid"
    assert pick_recommendation({"models": results["models"][:1]}) is None


# ── LLM judge ──────────────────────────────────────────────────────────────────


def test_judge_config_is_gateway_only_and_secret_write_only() -> None:
    from runledger_api.services.evaluators import normalize_judge_config, public_config

    with pytest.raises(ValueError):
        normalize_judge_config({"model": "fast", "api_key": "sk-x"})
    with pytest.raises(ValueError):
        normalize_judge_config({"model": "fast", "base_url": "http://x"})
    with pytest.raises(ValueError):
        normalize_judge_config({})
    cfg = normalize_judge_config({"model": "fast", "gateway_api_key": "rl_secret"})
    assert cfg["gateway_key_ref"].startswith("enc::")
    assert "gateway_api_key" not in cfg
    # Update without a key keeps the stored ref.
    kept = normalize_judge_config({"model": "fast", "criteria": "c"}, cfg)
    assert kept["gateway_key_ref"] == cfg["gateway_key_ref"]
    pub = public_config("llm_judge", kept)
    assert pub["gateway_key_set"] is True and "gateway_key_ref" not in pub


@pytest.mark.asyncio
async def test_judge_calls_gateway_with_stored_key_and_payloads() -> None:
    from runledger_api.services.evaluators import normalize_judge_config, run_llm_judge

    cfg = normalize_judge_config({"model": "judge", "gateway_api_key": "rl_judge"})
    fake = GatewayCallResult(
        ok=True,
        status_code=200,
        model="judge",
        request_ref="r",
        text='{"score": 0.8, "reasoning": "fine"}',
    )
    chat = AsyncMock(return_value=fake)
    with patch.object(gateway_client, "chat_completion", chat):
        score, evidence = await run_llm_judge(
            cfg,
            {
                "id": "run-1",
                "input_payload": [{"role": "user", "content": "What is 2+2?"}],
                "output_payload": "4",
            },
        )
    assert score == Decimal("0.8")
    assert evidence["via"] == "gateway"
    args, kwargs = chat.call_args
    assert args[0] == "Bearer rl_judge"
    prompt = kwargs["messages"][-1]["content"]
    assert "What is 2+2?" in prompt and "Output: 4" in prompt


@pytest.mark.asyncio
async def test_judge_refuses_empty_payloads() -> None:
    from runledger_api.services.evaluators import run_llm_judge

    with pytest.raises(ValueError, match="nothing to score"):
        await run_llm_judge({"model": "judge"}, {"id": "r"}, authorization="Bearer x")


# ── Prompts: diff, approval governance ─────────────────────────────────────────


def test_build_diff_counts_changes() -> None:
    from runledger_api.routers.prompts import build_diff

    lines, added, removed = build_diff("a\nb\nc", "a\nB\nc\nd")
    assert (added, removed) == (2, 1)
    kinds = [line.kind for line in lines]
    assert kinds[0] == "hunk" and "add" in kinds and "remove" in kinds


def test_pulled_versions_never_land_in_production() -> None:
    from runledger_api.routers.prompts import _pulled_environment

    assert _pulled_environment("production") == "staging"
    assert _pulled_environment(None) == "staging"
    assert _pulled_environment("dev") == "dev"


def _approval(prompt_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        request={"prompt_name": prompt_name, "version": 2},
        status="approved",
    )


@pytest.mark.asyncio
async def test_production_requires_matching_unused_approval() -> None:
    from runledger_api.routers import prompts as pr

    db = AsyncMock()
    ws = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        await pr._require_production_approval(db, ws, "support", None)
    assert exc.value.status_code == 403

    with (
        patch.object(pr, "validate_approved", AsyncMock(return_value=_approval("other"))),
        pytest.raises(HTTPException) as exc,
    ):
        await pr._require_production_approval(db, ws, "support", uuid.uuid4())
    assert exc.value.status_code == 403

    used = MagicMock()
    used.scalar_one_or_none.return_value = 3
    db.execute = AsyncMock(return_value=used)
    with (
        patch.object(pr, "validate_approved", AsyncMock(return_value=_approval("support"))),
        pytest.raises(HTTPException) as exc,
    ):
        await pr._require_production_approval(db, ws, "support", uuid.uuid4())
    assert exc.value.status_code == 409

    unused = MagicMock()
    unused.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=unused)
    approval = _approval("support")
    with patch.object(pr, "validate_approved", AsyncMock(return_value=approval)):
        got = await pr._require_production_approval(db, ws, "support", approval.id)
    assert got is approval


@pytest.mark.asyncio
async def test_score_gate_uses_experiment_score() -> None:
    from runledger_api.routers import prompts as pr

    prompt = SimpleNamespace(name="support", promotion_min_score=0.8, promotion_score_name=None)
    exp = SimpleNamespace(results={"summary": {"avg_score": 0.75, "scored_items": 12}})
    res = MagicMock()
    res.scalar_one_or_none.return_value = exp
    db = AsyncMock()
    db.execute = AsyncMock(return_value=res)
    score = await pr._version_score(db, uuid.uuid4(), prompt, 2)  # type: ignore[arg-type]
    assert score.source == "experiment"
    assert score.passes_gate is False
    prompt.promotion_min_score = 0.7
    score = await pr._version_score(db, uuid.uuid4(), prompt, 2)  # type: ignore[arg-type]
    assert score.passes_gate is True


# ── Runbooks ───────────────────────────────────────────────────────────────────


def test_runbook_markdown_export() -> None:
    from runledger_api.services.runbooks import runbook_markdown

    entry = SimpleNamespace(
        run_id=uuid.uuid4(),
        severity="warning",
        generated_at=datetime.now(UTC),
        summary={
            "run_id": "abc",
            "status": "succeeded",
            "cost_usd": 0.12,
            "cost_ratio": 2.4,
            "what_happened": "Run abc succeeded at 2.4x average cost",
            "recommendations": ["Investigate high cost"],
            "errors": [{"provider": "openai", "model": "gpt-4o", "error_type": "timeout"}],
        },
    )
    md = runbook_markdown(entry)  # type: ignore[arg-type]
    assert md.startswith("# Runbook: run abc")
    assert "Investigate high cost" in md and "openai/gpt-4o: timeout" in md


@pytest.mark.asyncio
async def test_runbook_export_and_delete_endpoints(authed_client, mock_db_session, mock_workspace):
    entry = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=mock_workspace.id,
        run_id=uuid.uuid4(),
        severity="info",
        summary={"run_id": "r1", "what_happened": "ok", "recommendations": []},
        generated_at=datetime.now(UTC),
    )
    found = MagicMock()
    found.scalar_one_or_none.return_value = entry
    mock_db_session.execute = AsyncMock(return_value=found)
    resp = await authed_client.get(f"/runbooks/{entry.id}/export?format=md")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "attachment" in resp.headers["content-disposition"]
    resp = await authed_client.get(f"/runbooks/{entry.id}/export?format=json")
    assert resp.status_code == 200 and resp.json()["severity"] == "info"
    resp = await authed_client.delete(f"/runbooks/{entry.id}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_awaited()


# ── Simulator levers from observed data (review B-20) ─────────────────────────


@pytest.mark.asyncio
async def test_observed_rates_from_workspace_data() -> None:
    from runledger_api.services.optimization import observed_rates

    cache_row = MagicMock()
    cache_row.one.return_value = (10, 4)
    comp_row = MagicMock()
    comp_row.one.return_value = (Decimal("2"), Decimal("10"), 7)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[cache_row, comp_row])
    rates = await observed_rates(db, uuid.uuid4(), datetime.now(UTC))
    assert rates["cache_hit_rate"] == 0.4 and rates["cache_sample"] == 10
    assert rates["compression_savings_pct"] == 0.2 and rates["compression_sample"] == 7


@pytest.mark.asyncio
async def test_observed_rates_none_without_data() -> None:
    from runledger_api.services.optimization import observed_rates

    empty_cache = MagicMock()
    empty_cache.one.return_value = (0, 0)
    empty_comp = MagicMock()
    empty_comp.one.return_value = (0, 0, 0)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[empty_cache, empty_comp])
    rates = await observed_rates(db, uuid.uuid4(), datetime.now(UTC))
    assert rates["cache_hit_rate"] is None
    assert rates["compression_savings_pct"] is None
