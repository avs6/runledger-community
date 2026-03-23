"""
Evaluator runner logic.

Supports two evaluator types:
  - llm_judge: calls an OpenAI-compatible endpoint to score a run
  - rule:      applies field/op/value rules against AgentRun attributes
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

import httpx
import structlog

log = structlog.get_logger()


# ── Rule evaluator ────────────────────────────────────────────────────────────

_OPS = {
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


async def run_llm_judge(
    config: dict[str, Any],
    run: dict[str, Any],
) -> tuple[Decimal, dict[str, Any]]:
    """
    Call an OpenAI-compatible API to score a run.

    config keys:
      model          — model identifier (required)
      api_key        — provider API key
      base_url       — provider base URL (default: OpenAI)
      prompt_template— jinja-style template with {{input}} / {{output}} / {{run_id}}
      criteria       — natural-language scoring criteria
      min_score      — minimum normalised score (default 0.0)
      max_score      — maximum normalised score (default 1.0)
    """
    model: str = config.get("model", "gpt-4o-mini")
    api_key: str = config.get("api_key", "")
    base_url: str = config.get("base_url", "https://api.openai.com/v1")
    criteria: str = config.get("criteria", "Rate the quality of the AI agent response from 0 to 1.")
    min_score: float = float(config.get("min_score", 0.0))
    max_score: float = float(config.get("max_score", 1.0))

    prompt_template: str = config.get(
        "prompt_template",
        "Run ID: {{run_id}}\nInput: {{input}}\nOutput: {{output}}\n\n"
        "Criteria: {{criteria}}\n\n"
        'Respond with a single JSON object: {"score": <float 0-1>, "reasoning": "<brief explanation>"}',
    )

    # Substitute template variables
    input_text = str(run.get("input_payload") or run.get("metadata") or "")[:2000]
    output_text = str(run.get("output_payload") or "")[:2000]
    prompt = (
        prompt_template.replace("{{run_id}}", str(run.get("id", "")))
        .replace("{{input}}", input_text)
        .replace("{{output}}", output_text)
        .replace("{{criteria}}", criteria)
    )

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI quality evaluator. Always respond with valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 256,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()

    # Extract JSON from the response
    import json

    try:
        # Try direct parse first
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON block in response
        match = re.search(r"\{[^}]+\}", content, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            raise ValueError(f"LLM judge returned non-JSON: {content[:200]}") from None

    raw_score = float(parsed.get("score", 0.5))
    # Clamp to [0, 1] then scale to [min_score, max_score]
    raw_score = max(0.0, min(1.0, raw_score))
    scaled = min_score + raw_score * (max_score - min_score)

    evidence = {
        "model": model,
        "raw_score": raw_score,
        "reasoning": parsed.get("reasoning", ""),
        "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
        "completion_tokens": data.get("usage", {}).get("completion_tokens"),
    }

    return Decimal(str(round(scaled, 4))), evidence


async def evaluate_run(
    evaluator_type: str,
    config: dict[str, Any],
    run: dict[str, Any],
) -> tuple[Decimal, dict[str, Any]]:
    """Dispatch to the correct evaluator type."""
    if evaluator_type == "llm_judge":
        return await run_llm_judge(config, run)
    return run_rule_evaluator(config, run)
