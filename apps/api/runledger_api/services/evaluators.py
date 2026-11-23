"""
Evaluator runner logic.

Supports two evaluator types:
  - llm_judge: scores a run with a model called through the RunLedger gateway
  - rule:      applies field/op/value rules against AgentRun attributes
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


# ── Rule evaluator ────────────────────────────────────────────────────────────

_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: float(a) > float(b),
    "gte": lambda a, b: float(a) >= float(b),
    "lt": lambda a, b: float(a) < float(b),
    "lte": lambda a, b: float(a) <= float(b),
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
    "regex": lambda a, b: bool(re.search(str(b), str(a))),
}


def _get_field(run: dict[str, Any], field: str) -> Any:
    """Safely resolve a dot-separated field path from run dict."""
    parts = field.split(".")
    val: Any = run
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def run_rule_evaluator(
    config: dict[str, Any],
    run: dict[str, Any],
) -> tuple[Decimal, dict[str, Any]]:
    """
    Evaluate a run against a list of rules.

    Returns (score, evidence).

    config schema:
      rules: [{field, op, value, score_if_pass, score_if_fail}]
      aggregation: "min" | "max" | "avg" | "first_fail"  (default: avg)
    """
    rules: list[dict[str, Any]] = config.get("rules", [])
    aggregation: str = config.get("aggregation", "avg")

    scores: list[float] = []
    evidence: dict[str, Any] = {"rules": []}

    for rule in rules:
        field = rule.get("field", "")
        op = rule.get("op", "eq")
        expected = rule.get("value")
        score_if_pass = float(rule.get("score_if_pass", 1.0))
        score_if_fail = float(rule.get("score_if_fail", 0.0))

        actual = _get_field(run, field)
        op_fn = _OPS.get(op)

        try:
            passed = op_fn(actual, expected) if op_fn is not None else False
        except Exception:
            passed = False

        score = score_if_pass if passed else score_if_fail
        scores.append(score)
        evidence["rules"].append(
            {
                "field": field,
                "op": op,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "score": score,
            }
        )

    if not scores:
        return Decimal("0"), evidence

    if aggregation == "min":
        final = min(scores)
    elif aggregation == "max":
        final = max(scores)
    elif aggregation == "first_fail":
        # Return score of first failing rule, or last rule if all pass
        for r, s in zip(evidence["rules"], scores, strict=False):
            if not r["passed"]:
                final = s
                break
        else:
            final = scores[-1]
    else:  # avg
        final = sum(scores) / len(scores)

    return Decimal(str(round(final, 4))), evidence


# ── LLM judge evaluator ───────────────────────────────────────────────────────
#
# The judge is gateway-backed (review B-09): it names a gateway route alias and
# authenticates to gateway-rs with a RunLedger API key held as a secret ref, so
# judge spend is governed, metered and budgeted like any other traffic. Provider
# keys and free-form base URLs are rejected.

# Config keys the API never stores or returns for an llm_judge.
FORBIDDEN_JUDGE_KEYS = ("api_key", "base_url", "provider_api_key")
# Write-only input field (raw RunLedger API key) and the stored secret ref.
JUDGE_KEY_INPUT = "gateway_api_key"
JUDGE_KEY_REF = "gateway_key_ref"


def store_judge_secret(raw_key: str) -> str:
    """Encrypt a judge key for storage. W1-A's ``core/secrets.py`` replaces this seam."""
    from runledger_api.services.kafka_export import encrypt_secret_value  # noqa: PLC0415

    return encrypt_secret_value(raw_key)


def resolve_judge_secret(ref: str | None) -> str | None:
    """Resolve a stored judge key ref (``enc::`` ciphertext or ``env://VAR``)."""
    from runledger_api.services.kafka_export import resolve_secret_value  # noqa: PLC0415

    return resolve_secret_value(ref) if ref else None


def normalize_judge_config(
    config: dict[str, Any], existing: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate an llm_judge config for storage; raise ValueError on bad input.

    ``gateway_api_key`` (write-only) becomes an encrypted ``gateway_key_ref``;
    ``gateway_key_ref`` may also be passed as ``env://VAR``. An update without a key
    keeps the stored ref.
    """
    bad = [k for k in FORBIDDEN_JUDGE_KEYS if config.get(k)]
    if bad:
        raise ValueError(
            "LLM judges run through the gateway: drop "
            + ", ".join(bad)
            + " and set 'model' to a gateway route alias"
        )
    if not str(config.get("model") or "").strip():
        raise ValueError("llm_judge config needs 'model' (a gateway route alias)")
    drop = (*FORBIDDEN_JUDGE_KEYS, JUDGE_KEY_INPUT, "gateway_key_set", "gateway_key_source")
    out = {k: v for k, v in config.items() if k not in drop}
    raw = config.get(JUDGE_KEY_INPUT)
    ref = config.get(JUDGE_KEY_REF)
    if raw:
        out[JUDGE_KEY_REF] = store_judge_secret(str(raw))
    elif isinstance(ref, str) and ref.lower().startswith("env://"):
        out[JUDGE_KEY_REF] = ref
    elif existing and existing.get(JUDGE_KEY_REF):
        out[JUDGE_KEY_REF] = existing[JUDGE_KEY_REF]
    else:
        out.pop(JUDGE_KEY_REF, None)
    return out


def public_config(evaluator_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """Config as returned by the API: secrets masked, never echoed."""
    if evaluator_type != "llm_judge":
        return dict(config)
    out = {k: v for k, v in config.items() if k not in (*FORBIDDEN_JUDGE_KEYS, JUDGE_KEY_REF)}
    ref = config.get(JUDGE_KEY_REF)
    out["gateway_key_set"] = bool(ref)
    if not ref:
        out["gateway_key_source"] = None
    elif isinstance(ref, str) and ref.lower().startswith("env://"):
        out["gateway_key_source"] = "env"
    else:
        out["gateway_key_source"] = "stored"
    return out


def payload_text(value: Any) -> str:
    """Flatten a captured payload (messages, a response object, text) for a judge."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):  # chat messages
        parts = []
        for m in value:
            if isinstance(m, dict):
                parts.append(f"{m.get('role', 'user')}: {m.get('content', '')}")
            else:
                parts.append(str(m))
        return "\n".join(parts)
    if isinstance(value, dict):
        choices = value.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            return str(msg.get("content") or "")
        return json.dumps(value, default=str)
    return str(value)


async def load_run_payloads(
    db: AsyncSession, run_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, Any]]:
    """Captured input/output for runs, from span metadata (review B-13).

    Payloads exist only when the capture policy recorded them; runs without a
    capture come back with ``None`` values so the judge skips them rather than
    scoring an empty transcript.
    """
    from runledger_api.models.events import Span  # noqa: PLC0415

    out: dict[uuid.UUID, dict[str, Any]] = {
        rid: {"input_payload": None, "output_payload": None} for rid in run_ids
    }
    if not run_ids:
        return out
    rows = await db.execute(
        select(Span.run_id, Span.span_metadata)
        .where(Span.run_id.in_(run_ids), Span.span_metadata.isnot(None))
        .order_by(Span.started_at)
    )
    for run_id, meta in rows.all():
        if not isinstance(meta, dict):
            continue
        entry = out.setdefault(run_id, {"input_payload": None, "output_payload": None})
        if entry["input_payload"] is None and meta.get("messages") is not None:
            entry["input_payload"] = meta["messages"]
        if entry["output_payload"] is None and meta.get("response") is not None:
            entry["output_payload"] = meta["response"]
    return out


async def run_llm_judge(
    config: dict[str, Any],
    run: dict[str, Any],
    *,
    authorization: str | None = None,
) -> tuple[Decimal, dict[str, Any]]:
    """
    Score a run with an LLM judge sent through the gateway.

    config keys:
      model           — gateway route alias (required)
      gateway_key_ref — stored secret ref for the RunLedger key the judge uses
      prompt_template — template with {{input}} / {{output}} / {{expected}} / {{run_id}}
      criteria        — natural-language scoring criteria
      min_score       — minimum normalised score (default 0.0)
      max_score       — maximum normalised score (default 1.0)

    ``authorization`` (a caller's ``Bearer`` header) is used for interactive runs;
    background runs use the stored key ref.
    """
    from runledger_api.services import gateway_client  # noqa: PLC0415

    model: str = str(config.get("model") or "")
    if not model:
        raise ValueError("llm_judge has no gateway route alias in 'model'")
    criteria: str = config.get("criteria", "Rate the quality of the AI agent response from 0 to 1.")
    min_score: float = float(config.get("min_score", 0.0))
    max_score: float = float(config.get("max_score", 1.0))

    input_text = payload_text(run.get("input_payload"))[:4000]
    output_text = payload_text(run.get("output_payload"))[:4000]
    if not input_text and not output_text:
        raise ValueError("No captured input/output for this run; the judge has nothing to score")

    prompt_template: str = config.get(
        "prompt_template",
        "Run ID: {{run_id}}\nInput: {{input}}\nOutput: {{output}}\n"
        "Expected (may be empty): {{expected}}\n\n"
        "Criteria: {{criteria}}\n\n"
        'Respond with a single JSON object: {"score": <float 0-1>, "reasoning": "<brief explanation>"}',
    )
    prompt = (
        prompt_template.replace("{{run_id}}", str(run.get("id", "")))
        .replace("{{input}}", input_text)
        .replace("{{output}}", output_text)
        .replace("{{expected}}", str(run.get("expected_output") or ""))
        .replace("{{criteria}}", criteria)
    )

    if authorization is None:
        key = resolve_judge_secret(config.get(JUDGE_KEY_REF))
        if not key:
            raise ValueError(
                "llm_judge has no gateway key; set gateway_api_key on the evaluator "
                "(stored encrypted) or run it interactively"
            )
        authorization = f"Bearer {key}"

    result = await gateway_client.chat_completion(
        authorization,
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an AI quality evaluator. Always respond with valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        params={"temperature": 0.0, "max_tokens": 256},
        metadata={
            "feature_tag": "evaluator",
            "source": "evaluator.judge",
            "judged_run_id": str(run.get("id", "")),
        },
        tags=["evaluator"],
        timeout_s=60.0,
    )
    if not result.ok:
        raise ValueError(
            f"Judge call through the gateway failed [{result.status_code}]: {result.error}"
        )
    content = (result.text or "").strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[^}]+\}", content, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            raise ValueError(f"LLM judge returned non-JSON: {content[:200]}") from None

    raw_score = float(parsed.get("score", 0.5))
    raw_score = max(0.0, min(1.0, raw_score))
    scaled = min_score + raw_score * (max_score - min_score)

    evidence = {
        "model": model,
        "model_used": result.model,
        "raw_score": raw_score,
        "reasoning": parsed.get("reasoning", ""),
        "prompt_tokens": result.input_tokens,
        "completion_tokens": result.output_tokens,
        "via": "gateway",
        "judge_request_ref": result.request_ref,
    }

    return Decimal(str(round(scaled, 4))), evidence


async def evaluate_run(
    evaluator_type: str,
    config: dict[str, Any],
    run: dict[str, Any],
    *,
    authorization: str | None = None,
) -> tuple[Decimal, dict[str, Any]]:
    """Dispatch to the correct evaluator type."""
    if evaluator_type == "llm_judge":
        return await run_llm_judge(config, run, authorization=authorization)
    return run_rule_evaluator(config, run)
