"""Intelligent routing classifier (review G-04).

Classifies a request by **complexity** (simple / medium / complex) and **business risk**
(low / high), maps the pair to a tier through ``matrix`` and the tier to an alias
through ``tiers``, and picks a ``reasoning_effort``.

The gateway used to call a ``/classify`` endpoint on gateway-rs that doesn't exist,
waiting up to 25 s on every routed request before failing open. The classifier now
runs in-process:

- ``heuristic`` — token estimate (thresholds ``complexity_thresholds``), code and
  multi-step signals → complexity; ``risk_keywords`` scan → risk. Deterministic.
- ``llm`` — a local OpenAI-compatible model (``llm_model`` on ``OLLAMA_BASE_URL``)
  labels ``{complexity, risk, reasoning_effort}``; falls back to the heuristic on any
  error or after ``ROUTER_LLM_TIMEOUT_SECONDS`` (default 3).
- ``hybrid`` (default) — heuristic, refined by the LLM when one is configured.

An external classifier is used only when ``ROUTER_SVC_URL`` is set explicitly
(timeout ``ROUTER_TIMEOUT_SECONDS``, default 3); on failure the built-in heuristic
answers. ``classify`` never raises.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

from runledger_api.core.config import settings

log = logging.getLogger(__name__)

_SVC_URL = os.getenv("ROUTER_SVC_URL", "").rstrip("/")
_SVC_TIMEOUT = float(os.getenv("ROUTER_TIMEOUT_SECONDS", "3"))
_LLM_TIMEOUT = float(os.getenv("ROUTER_LLM_TIMEOUT_SECONDS", "3"))

DEFAULT_RISK_KEYWORDS = [
    "regulatory",
    "compliance",
    "contract",
    "legal",
    "lawsuit",
    "liability",
    "gdpr",
    "hipaa",
    "medical",
    "diagnosis",
    "prescription",
    "financial advice",
    "investment",
    "tax",
    "security vulnerability",
    "exploit",
    "breach",
    "terminate",
    "fraud",
    "audit",
]
DEFAULT_THRESHOLDS = {"medium": 500, "complex": 2000}
DEFAULT_MATRIX = {
    "simple": {"low": "cheap", "high": "mid"},
    "medium": {"low": "mid", "high": "frontier"},
    "complex": {"low": "frontier", "high": "frontier"},
}
_EFFORT = {"simple": "low", "medium": "medium", "complex": "high"}
_LEVELS = ("simple", "medium", "complex")
_MULTI_STEP = re.compile(
    r"\b(step[- ]by[- ]step|prove|derive|analy[sz]e|compare|trade-?offs?|design|architect|"
    r"plan|debug|refactor|optimi[sz]e)\b",
    re.I,
)


def enabled() -> bool:
    """The built-in classifier is always available."""
    return True


def _text(messages: list[dict[str, Any]]) -> str:
    parts = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.extend(p.get("text", "") for p in content if isinstance(p, dict))
    return "\n".join(parts)


def heuristic(messages: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, str]:
    text = _text(messages)
    tokens = len(text) // 4
    thresholds = {**DEFAULT_THRESHOLDS, **(config.get("complexity_thresholds") or {})}
    level = 0
    if tokens >= int(thresholds["complex"]):
        level = 2
    elif tokens >= int(thresholds["medium"]):
        level = 1
    signals = []
    if "```" in text or re.search(r"\b(def|class|function|SELECT|import)\b", text):
        signals.append("code")
    if _MULTI_STEP.search(text):
        signals.append("multi-step")
    level = min(2, level + (1 if signals else 0))
    keywords = [k.lower() for k in (config.get("risk_keywords") or DEFAULT_RISK_KEYWORDS)]
    lowered = text.lower()
    hits = [k for k in keywords if k in lowered]
    complexity = _LEVELS[level]
    reason = f"heuristic ~{tokens} tokens" + (f", {'/'.join(signals)}" if signals else "")
    if hits:
        reason += f", risk: {', '.join(hits[:3])}"
    return {
        "complexity": complexity,
        "risk": "high" if hits else "low",
        "reasoning_effort": _EFFORT[complexity],
        "reason": reason,
    }


async def _llm_label(
    messages: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, str] | None:
    model = config.get("llm_model")
    base = os.getenv("OLLAMA_BASE_URL", "")
    if not model or not base:
        return None
    prompt = (
        "Classify this request. Reply with JSON only: "
        '{"complexity":"simple|medium|complex","risk":"low|high","reasoning_effort":"low|medium|high"}.\n\n'
        + _text(messages)[:4000]
    )
    try:
        async with httpx.AsyncClient(timeout=_LLM_TIMEOUT) as client:
            resp = await client.post(
                f"{base.rstrip('/')}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 60,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", content, re.S)
            data = json.loads(match.group(0)) if match else {}
    except Exception as exc:  # noqa: BLE001 - fall back to the heuristic
        log.info("intelligent_router_llm_skipped error=%s", exc)
        return None
    out = {}
    if data.get("complexity") in _LEVELS:
        out["complexity"] = data["complexity"]
    if data.get("risk") in ("low", "high"):
        out["risk"] = data["risk"]
    if data.get("reasoning_effort") in ("low", "medium", "high"):
        out["reasoning_effort"] = data["reasoning_effort"]
    return out or None


async def _remote(messages: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(
            timeout=_SVC_TIMEOUT, headers=settings.internal_service_headers
        ) as client:
            resp = await client.post(
                f"{_SVC_URL}/classify", json={"messages": messages, "config": config}
            )
            resp.raise_for_status()
            decision: dict[str, Any] = resp.json()
            return decision
    except Exception as exc:  # noqa: BLE001
        log.warning("intelligent_router_remote_failed error=%s", exc)
        return None


async def classify(
    messages: list[dict[str, Any]], config: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Return ``{complexity, risk, reasoning_effort, tier, alias, reason}``.

    ``alias`` is None when ``tiers`` has no entry for the chosen tier (the request
    keeps its alias). Never raises."""
    cfg = config or {}
    try:
        if _SVC_URL:
            remote = await _remote(messages, cfg)
            if remote:
                return remote
        mode = str(cfg.get("classifier_mode", "hybrid"))
        label = heuristic(messages, cfg)
        if mode in ("llm", "hybrid"):
            refined = await _llm_label(messages, cfg)
            if refined:
                label = {**label, **refined, "reason": f"{label['reason']}; llm refined"}
            elif mode == "llm":
                label["reason"] += "; llm unavailable"
        matrix = {**DEFAULT_MATRIX, **(cfg.get("matrix") or {})}
        tier = (matrix.get(label["complexity"]) or {}).get(label["risk"]) or "mid"
        alias = (cfg.get("tiers") or {}).get(tier)
        effort = label["reasoning_effort"] if cfg.get("reasoning_effort", True) else None
        return {
            "complexity": label["complexity"],
            "risk": label["risk"],
            "reasoning_effort": effort,
            "tier": tier,
            "alias": alias,
            "reason": f"intelligent:{label['complexity']}/{label['risk']}→{tier} ({label['reason']})",
        }
    except Exception as exc:  # noqa: BLE001 - fail open
        log.warning("intelligent_router_failed error=%s", exc)
        return None
