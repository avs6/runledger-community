"""
Intelligent Router service (Phase 4).

Classifies a request along complexity × risk (+ reasoning effort) and maps it to a model tier,
so simple/low-risk work goes to a cheap model and only hard/high-risk work reaches a frontier model.

Classifier is user-configurable per route:
  classifier_mode: "heuristic" | "llm" | "hybrid"
    heuristic → token estimate (complexity) + risk-keyword scan (risk)
    llm       → a local Ollama model zero-shot labels {complexity, risk, reasoning_effort}
    hybrid    → heuristic first, LLM refine merged on top (falls back to heuristic if LLM fails)

Tiers are an arbitrary map {name → alias}; the matrix maps complexity × risk → a tier name.
Everything runs on CPU; the LLM pass calls an external Ollama endpoint (OpenAI-compatible).

Endpoints
---------
GET  /health
POST /classify { messages, config? } → { complexity, risk, reasoning_effort, tier, alias, reason, method }
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1").rstrip("/")
DEFAULT_LLM_MODEL = os.getenv("ROUTER_LLM_MODEL", "llama3.1:8b")
TIMEOUT = float(os.getenv("ROUTER_TIMEOUT_SECONDS", "20"))

DEFAULT_RISK_KEYWORDS = [
    "regulatory", "regulation", "compliance", "contract", "legal", "lawsuit", "liability",
    "financial", "invoice", "tax", "audit", "medical", "diagnosis", "patient", "security",
    "vulnerability", "credential", "password", "pii", "gdpr", "hipaa", "breach",
]
DEFAULT_MATRIX = {
    "simple": {"low": "cheap", "high": "mid"},
    "medium": {"low": "mid", "high": "frontier"},
    "complex": {"low": "frontier", "high": "frontier"},
}
DEFAULT_TIERS = {"cheap": "gpt-4o-mini", "mid": "gpt-4o", "frontier": "o1"}
EFFORT_BY_COMPLEXITY = {"simple": "low", "medium": "medium", "complex": "high"}

app = FastAPI(title="RunLedger Router Service", version="0.1.0")


def est(text: str) -> int:
    return max(1, len(text) // 4)


class RouterConfig(BaseModel):
    classifier_mode: str = "hybrid"  # heuristic | llm | hybrid
    llm_model: str = DEFAULT_LLM_MODEL
    risk_keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_RISK_KEYWORDS))
    complexity_thresholds: dict[str, int] = Field(
        default_factory=lambda: {"medium": 500, "complex": 2000}
    )
    tiers: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_TIERS))
    matrix: dict[str, dict[str, str]] = Field(default_factory=lambda: dict(DEFAULT_MATRIX))
    reasoning_effort: bool = True
    on_failure: str = "passthrough"  # passthrough | <tier name>


class ClassifyRequest(BaseModel):
    messages: list[dict[str, Any]]
    config: RouterConfig = Field(default_factory=RouterConfig)


class ClassifyResponse(BaseModel):
    complexity: str
    risk: str
    reasoning_effort: str
    tier: str
    alias: str | None
    reason: str
    method: str


def _text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(str(m.get("content", "")) for m in messages)


def _heuristic(text: str, cfg: RouterConfig) -> tuple[str, str]:
    tokens = est(text)
    if tokens >= cfg.complexity_thresholds.get("complex", 2000):
        complexity = "complex"
    elif tokens >= cfg.complexity_thresholds.get("medium", 500):
        complexity = "medium"
    else:
        complexity = "simple"
    low = text.lower()
    risk = "high" if any(k.lower() in low for k in cfg.risk_keywords) else "low"
    return complexity, risk


async def _llm_classify(text: str, cfg: RouterConfig) -> dict[str, str] | None:
    prompt = (
        "Classify the user's task. Respond with ONLY a compact JSON object with keys "
        '"complexity" (simple|medium|complex), "risk" (low|high), '
        '"reasoning_effort" (low|medium|high). No prose.'
    )
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{OLLAMA_BASE_URL}/chat/completions",
                json={
                    "model": cfg.llm_model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text[:6000]},
                    ],
                    "max_tokens": 60,
                    "temperature": 0.0,
                    "stream": False,
                },
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except Exception:
        return None


def _tier_and_alias(complexity: str, risk: str, cfg: RouterConfig) -> tuple[str, str | None]:
    tier = cfg.matrix.get(complexity, {}).get(risk) or next(iter(cfg.tiers), "")
    return tier, cfg.tiers.get(tier)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "llm": OLLAMA_BASE_URL, "modes": ["heuristic", "llm", "hybrid"]}


@app.post("/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest) -> ClassifyResponse:
    cfg = req.config
    text = _text(req.messages)
    method = cfg.classifier_mode
    complexity, risk = _heuristic(text, cfg)
    effort = EFFORT_BY_COMPLEXITY[complexity]

    if cfg.classifier_mode in ("llm", "hybrid"):
        labels = await _llm_classify(text, cfg)
        if labels:
            complexity = labels.get("complexity", complexity)
            risk = labels.get("risk", risk)
            effort = labels.get("reasoning_effort", EFFORT_BY_COMPLEXITY.get(complexity, effort))
        elif cfg.classifier_mode == "llm":
            method = "heuristic"  # llm-only requested but LLM failed → heuristic fallback

    if not cfg.reasoning_effort:
        effort = "medium"

    tier, alias = _tier_and_alias(complexity, risk, cfg)
    reason = f"complexity={complexity} risk={risk} → tier={tier} ({method})"
    return ClassifyResponse(
        complexity=complexity,
        risk=risk,
        reasoning_effort=effort,
        tier=tier,
        alias=alias,
        reason=reason,
        method=method,
    )
