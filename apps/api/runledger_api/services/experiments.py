"""
Experiment runner: one experiment system for evals and replays (review B-07, B-08).

An experiment runs a dataset through the gateway once per model config:

* ``mode="eval"``   — each item's ``input`` becomes the user message, with the
  linked prompt version (if any) as the system prompt. ``{{var}}`` placeholders in
  the prompt are filled from ``item.metadata.variables``.
* ``mode="replay"`` — each item carries captured ``messages`` from a recorded run
  (datasets built with ``POST /datasets/from-runs``); the conversation is replayed
  as-is against each model.

Every call goes through gateway-rs with the caller's key, so it is governed,
metered and recorded as a run (``feature_tag=experiment``). Outputs are scored by
the experiment's evaluators, plus an expected-output match when the item has one.
Each score is stored as a ScoreEvent on the recorded run, so experiment results
feed scorecards and the prompt promotion gate.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.eval_experiments import EvalDataset, EvalExperiment
from runledger_api.models.evaluators import Evaluator
from runledger_api.models.prompts import Prompt, PromptVersion
from runledger_api.models.scores import ScoreEvent
from runledger_api.services import gateway_client
from runledger_api.services.evaluators import evaluate_run, payload_text

log = structlog.get_logger()

# Upper bound on gateway calls per experiment run (items × models).
MAX_CALLS = 500
# Items kept in the stored result for the detail view.
MAX_STORED_ITEMS = 200
CONCURRENCY = 4

_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


def render_template(template: str, variables: dict[str, Any]) -> str:
    """Fill ``{{name}}`` placeholders; unknown names are left in place."""
    return _VAR_RE.sub(lambda m: str(variables.get(m.group(1), m.group(0))), template)


def expected_match(output: str, expected: str | None) -> float | None:
    """1.0 when the expected output appears in the response (case-insensitive)."""
    if not expected:
        return None
    return 1.0 if expected.strip().lower() in (output or "").strip().lower() else 0.0


def item_messages(
    item: dict[str, Any], mode: str, system_prompt: str | None
) -> list[dict[str, Any]] | None:
    """Messages to send for one dataset item, or None when the item can't be run."""
    if mode == "replay":
        messages = item.get("messages")
        if isinstance(messages, list) and messages:
            return [dict(m) for m in messages if isinstance(m, dict)]
        return None
    text = item.get("input")
    if not text:
        return None
    messages: list[dict[str, Any]] = []
    if system_prompt:
        variables = (item.get("metadata") or {}).get("variables") or {}
        messages.append({"role": "system", "content": render_template(system_prompt, variables)})
    messages.append({"role": "user", "content": str(text)})
    return messages


async def resolve_prompt(
    db: AsyncSession, workspace_id: uuid.UUID, name: str | None, version: int | None
) -> PromptVersion | None:
    if not name:
        return None
    stmt = (
        select(PromptVersion)
        .join(Prompt, Prompt.id == PromptVersion.prompt_id)
        .where(Prompt.workspace_id == workspace_id, Prompt.name == name)
    )
    if version:
        stmt = stmt.where(PromptVersion.version == version)
    else:
        stmt = stmt.order_by(PromptVersion.version.desc())
    return (await db.execute(stmt.limit(1))).scalar_one_or_none()


def _model_name(cfg: Any) -> str:
    return str(cfg.get("model") if isinstance(cfg, dict) else cfg)


def _label(cfg: Any) -> str:
    if isinstance(cfg, dict):
        return str(cfg.get("label") or cfg.get("model"))
    return str(cfg)


async def execute_experiment(
    db: AsyncSession,
    experiment: EvalExperiment,
    authorization: str,
) -> EvalExperiment:
    """Run the experiment synchronously and store real results on it."""
    workspace_id = experiment.workspace_id
    experiment.status = "running"
    experiment.started_at = datetime.now(UTC)
    experiment.completed_at = None
    await db.commit()

    try:
        results = await _run(db, experiment, authorization)
    except Exception as exc:  # noqa: BLE001 - stored for the UI
        log.error("experiment.failed", experiment_id=str(experiment.id), error=str(exc))
        experiment.status = "failed"
        experiment.results = {"error": str(exc)}
        experiment.completed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(experiment)
        return experiment

    experiment.status = "completed"
    experiment.results = results
    experiment.run_count = int(results["summary"]["calls"])
    experiment.scores_created = int(results["summary"]["scores_created"])
    experiment.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(experiment)
    log.info(
        "experiment.completed",
        experiment_id=str(experiment.id),
        workspace_id=str(workspace_id),
        calls=experiment.run_count,
    )
    return experiment


async def _run(db: AsyncSession, experiment: EvalExperiment, authorization: str) -> dict[str, Any]:
    workspace_id = experiment.workspace_id
    mode = experiment.mode or "eval"
    if experiment.dataset_id is None:
        raise ValueError("Experiment has no dataset")
    dataset = await db.get(EvalDataset, experiment.dataset_id)
    if dataset is None or dataset.workspace_id != workspace_id:
        raise ValueError("Dataset not found")
    models = list(experiment.models or [])
    if not models:
        raise ValueError("Experiment has no models to run")
    items: list[dict[str, Any]] = [i for i in (dataset.items or []) if isinstance(i, dict)]
    if len(items) * len(models) > MAX_CALLS:
        raise ValueError(
            f"{len(items)} items × {len(models)} models exceeds {MAX_CALLS} gateway calls; "
            "split the dataset"
        )

    prompt_version = await resolve_prompt(
        db, workspace_id, experiment.prompt_name, experiment.prompt_version
    )
    if experiment.prompt_name and prompt_version is None:
        raise ValueError(f"Prompt '{experiment.prompt_name}' version not found")
    system_prompt = prompt_version.content if prompt_version else None
    deployment_version = (
        f"{experiment.prompt_name}:{prompt_version.version}" if prompt_version else None
    )

    evaluators: list[Evaluator] = []
    for eid in experiment.evaluator_ids or []:
        ev = await db.get(Evaluator, uuid.UUID(str(eid)))
        if ev is not None and ev.workspace_id == workspace_id and ev.status == "active":
            evaluators.append(ev)

    sem = asyncio.Semaphore(CONCURRENCY)

    async def call(
        idx: int, item: dict[str, Any], cfg: Any
    ) -> tuple[int, Any, gateway_client.GatewayCallResult | None]:
        messages = item_messages(item, mode, system_prompt)
        if messages is None:
            return idx, cfg, None
        metadata: dict[str, Any] = {
            "feature_tag": "experiment",
            "source": f"experiment.{mode}",
            "experiment_id": str(experiment.id),
        }
        if deployment_version:
            metadata["deployment_version"] = deployment_version
        if item.get("run_id"):
            metadata["replay_of_run_id"] = str(item["run_id"])
        params = cfg.get("params") if isinstance(cfg, dict) else None
        async with sem:
            result = await gateway_client.chat_completion(
                authorization,
                model=_model_name(cfg),
                messages=messages,
                params=params if isinstance(params, dict) else None,
                metadata=metadata,
                tags=["experiment"],
            )
        return idx, cfg, result

    outcomes = await asyncio.gather(
        *[call(idx, item, cfg) for idx, item in enumerate(items) for cfg in models]
    )

    per_model: dict[str, dict[str, Any]] = {
        _label(cfg): {
            "model": _model_name(cfg),
            "label": _label(cfg),
            "items_run": 0,
            "errors": 0,
            "scores": [],
            "latencies": [],
            "cost": Decimal("0"),
            "cost_known": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "matches": [],
        }
        for cfg in models
    }
    stored_items: list[dict[str, Any]] = [
        {
            "index": idx,
            "input": item.get("input") or payload_text(item.get("messages"))[:500],
            "expected_output": item.get("expected_output"),
            "run_id": item.get("run_id"),
            "outputs": [],
        }
        for idx, item in enumerate(items[:MAX_STORED_ITEMS])
    ]
    skipped = 0
    scores_created = 0

    for idx, cfg, result in outcomes:
        stats = per_model[_label(cfg)]
        item = items[idx]
        if result is None:
            skipped += 1
            continue
        result = await gateway_client.attach_run(db, workspace_id, result)
        output: dict[str, Any] = {
            "model": stats["model"],
            "label": stats["label"],
            "ok": result.ok,
            "text": (result.text or "")[:4000] if result.ok else None,
            "error": None if result.ok else f"[{result.status_code}] {result.error}",
            "latency_ms": result.latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None,
            "run_id": str(result.run_id) if result.run_id else None,
            "scores": {},
        }
        if not result.ok:
            stats["errors"] += 1
        else:
            stats["items_run"] += 1
            stats["latencies"].append(result.latency_ms)
            stats["input_tokens"] += result.input_tokens
            stats["output_tokens"] += result.output_tokens
            if result.cost_usd is not None:
                stats["cost"] += result.cost_usd
                stats["cost_known"] += 1
            item_scores: list[float] = []
            match = expected_match(result.text or "", item.get("expected_output"))
            if match is not None:
                stats["matches"].append(match)
                output["scores"]["expected_match"] = match
                item_scores.append(match)
            run_view = {
                "id": str(result.run_id or ""),
                "status": "succeeded",
                "input_payload": item.get("messages") or item.get("input"),
                "output_payload": result.text,
                "output": result.text,
                "expected_output": item.get("expected_output"),
                "latency_ms": result.latency_ms,
                "total_cost_usd": output["cost_usd"],
                "total_input_tokens": result.input_tokens,
                "total_output_tokens": result.output_tokens,
            }
            for ev in evaluators:
                try:
                    value, evidence = await evaluate_run(
                        ev.type, ev.config or {}, run_view, authorization=authorization
                    )
                except Exception as exc:  # noqa: BLE001 - recorded per item
                    output["scores"][ev.name] = None
                    output.setdefault("score_errors", {})[ev.name] = str(exc)[:300]
                    continue
                output["scores"][ev.name] = float(value)
                item_scores.append(float(value))
                if result.run_id is not None:
                    db.add(
                        ScoreEvent(
                            workspace_id=workspace_id,
                            run_id=result.run_id,
                            name=ev.name,
                            value=value,
                            source="llm" if ev.type == "llm_judge" else "rule",
                            confidence=Decimal("0.9") if ev.type == "llm_judge" else Decimal("1.0"),
                            evidence={**evidence, "experiment_id": str(experiment.id)},
                            evaluator_id=ev.id,
                        )
                    )
                    scores_created += 1
            if item_scores:
                item_score = sum(item_scores) / len(item_scores)
                output["score"] = round(item_score, 4)
                stats["scores"].append(item_score)
        if idx < MAX_STORED_ITEMS:
            stored_items[idx]["outputs"].append(output)

    await db.commit()

    model_rows: list[dict[str, Any]] = []
    for stats in per_model.values():
        scores = stats["scores"]
        lat = stats["latencies"]
        model_rows.append(
            {
                "model": stats["model"],
                "label": stats["label"],
                "items_run": stats["items_run"],
                "errors": stats["errors"],
                "avg_score": round(sum(scores) / len(scores), 4) if scores else None,
                "scored_items": len(scores),
                "expected_match_rate": round(sum(stats["matches"]) / len(stats["matches"]), 4)
                if stats["matches"]
                else None,
                "avg_latency_ms": round(sum(lat) / len(lat)) if lat else None,
                "total_cost_usd": str(stats["cost"]) if stats["cost_known"] else None,
                "avg_cost_usd": str(stats["cost"] / stats["cost_known"])
                if stats["cost_known"]
                else None,
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
            }
        )

    baseline = model_rows[0]
    deltas = []
    for row in model_rows[1:]:
        deltas.append(
            {
                "baseline": baseline["label"],
                "candidate": row["label"],
                "score_delta": _delta(row["avg_score"], baseline["avg_score"]),
                "cost_delta_pct": _pct(row["avg_cost_usd"], baseline["avg_cost_usd"]),
                "latency_delta_pct": _pct(row["avg_latency_ms"], baseline["avg_latency_ms"]),
            }
        )

    all_scores = [s for st in per_model.values() for s in st["scores"]]
    total_cost = sum((st["cost"] for st in per_model.values()), Decimal("0"))
    return {
        "mode": mode,
        "prompt_name": experiment.prompt_name,
        "prompt_version": prompt_version.version if prompt_version else None,
        "evaluators": [ev.name for ev in evaluators],
        "summary": {
            "items": len(items),
            "calls": sum(st["items_run"] + st["errors"] for st in per_model.values()),
            "errors": sum(st["errors"] for st in per_model.values()),
            "skipped": skipped,
            "scored_items": len(all_scores),
            "avg_score": round(sum(all_scores) / len(all_scores), 4) if all_scores else None,
            "total_cost_usd": str(total_cost),
            "scores_created": scores_created,
            "via": "gateway",
        },
        "models": model_rows,
        "deltas": deltas,
        "items": stored_items,
    }


def _delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(a - b, 4)


def _pct(a: Any, b: Any) -> float | None:
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if fb == 0:
        return None
    return round((fa - fb) / fb * 100, 2)


def pick_recommendation(
    results: dict[str, Any], max_score_drop: float = 0.02
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Baseline row and the candidate worth switching to, or None.

    The candidate is the cheapest model whose score is within ``max_score_drop`` of
    the baseline; failing that, the best-scoring model if it beats the baseline.
    """
    rows = [r for r in results.get("models") or [] if r.get("items_run")]
    if len(rows) < 2:
        return None
    baseline, others = rows[0], rows[1:]

    def cost(r: dict[str, Any]) -> float:
        try:
            return float(r.get("avg_cost_usd"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return float("inf")

    base_score = baseline.get("avg_score")
    if base_score is not None:
        holding = [
            r
            for r in others
            if r.get("avg_score") is not None and r["avg_score"] >= base_score - max_score_drop
        ]
        cheaper = [r for r in holding if cost(r) < cost(baseline)]
        if cheaper:
            return baseline, min(cheaper, key=cost)
        better = [
            r for r in others if r.get("avg_score") is not None and r["avg_score"] > base_score
        ]
        if better:
            return baseline, max(better, key=lambda r: r["avg_score"])
        return None
    cheaper = [r for r in others if cost(r) < cost(baseline)]
    return (baseline, min(cheaper, key=cost)) if cheaper else None
