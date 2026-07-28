"""
Optimization Flywheel service (Phase 7).

Stateless CPU analyzer. Given per-segment observations of how RunLedger's own traffic
performed under each optimization configuration — (config fingerprint, sample size, cost
per request, quality) — it finds, for each segment, the cheapest configuration that still
holds the customer's quality SLA, and returns recommendations:

  switch    — a cheaper config with enough data already holds the SLA → move to it.
  explore   — a cheaper config looks promising but is under-sampled → canary to gather data.
  guardrail — the current (dominant) config is *below* the SLA → propose the cheapest
              config that holds it (may cost more; holding quality is the invariant).

The service owns no data and no DB. The RunLedger worker aggregates the tuples, calls
/analyze, and persists the results. Everything is observational: the analyzer only ever
proposes configurations it has actually seen (or an explore of a seen-but-thin one), and
only changes dimensions the caller's `action_space` permits.

Endpoints
---------
GET  /health
POST /analyze { segment_by, min_quality, min_sample_size, action_space, segments[] }
       → { recommendations[] }
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="RunLedger Flywheel Service", version="0.1.0")

# A minimum cost improvement worth recommending a switch/explore for (fraction).
MIN_SAVING_PCT = 0.05

# Which action-space dimension governs each fingerprint key. A candidate config is only
# proposed if every dimension in which it differs from the current config is permitted.
ACTION_FOR_KEY: dict[str, str] = {
    "model": "model",
    "tier": "routing",
    "routing": "routing",
    "stages": "stages",
    "context_compiler": "stages",
    "compression_rate": "compression_rate",
    "semantic_cache": "cache_threshold",
}


class Observation(BaseModel):
    config: dict[str, Any]
    n: int
    avg_cost_per_req: float
    quality: float | None = None
    success_rate: float | None = None


class Segment(BaseModel):
    segment_key: str
    observations: list[Observation]


class AnalyzeRequest(BaseModel):
    segment_by: str = "outcome_type"
    min_quality: float = 0.8
    min_sample_size: int = 20
    action_space: list[str] = Field(
        default_factory=lambda: ["model", "stages", "compression_rate", "cache_threshold", "routing"]
    )
    segments: list[Segment]


class Recommendation(BaseModel):
    segment_key: str
    kind: str  # switch | explore | guardrail
    current_config: dict[str, Any]
    proposed_config: dict[str, Any]
    est_cost_delta_pct: float | None
    est_cost_delta_per_req: float | None
    current_quality: float | None
    proposed_quality: float | None
    sample_size: int
    confidence: str  # high | medium | low
    rationale: str


class AnalyzeResponse(BaseModel):
    recommendations: list[Recommendation]


def _config_diff_allowed(current: dict[str, Any], proposed: dict[str, Any], action_space: list[str]) -> bool:
    """True iff every key where the two configs differ maps to a permitted action."""
    keys = set(current) | set(proposed)
    for k in keys:
        if current.get(k) == proposed.get(k):
            continue
        action = ACTION_FOR_KEY.get(k)
        if action is None or action not in action_space:
            return False
    return True


def _confidence(current_n: int, proposed_n: int, min_n: int) -> str:
    if proposed_n >= 3 * min_n and current_n >= min_n:
        return "high"
    if proposed_n >= min_n:
        return "medium"
    return "low"


def _analyze_segment(seg: Segment, req: AnalyzeRequest) -> Recommendation | None:
    obs = [o for o in seg.observations if o.n > 0]
    if not obs:
        return None

    # Current = the config most traffic actually runs on.
    current = max(obs, key=lambda o: o.n)
    min_q = req.min_quality
    min_n = req.min_sample_size

    def holds_sla(o: Observation) -> bool:
        return o.quality is not None and o.quality >= min_q

    # Candidates cheaper than current that we're allowed to switch to.
    cheaper = [
        o
        for o in obs
        if o.config != current.config
        and o.avg_cost_per_req < current.avg_cost_per_req * (1 - MIN_SAVING_PCT)
        and _config_diff_allowed(current.config, o.config, req.action_space)
    ]

    # ── Guardrail: the dominant config is below the SLA ──────────────────────
    if not holds_sla(current):
        holding = [o for o in obs if holds_sla(o) and o.n >= min_n and o.config != current.config]
        if not holding:
            return None  # nothing observed holds the SLA — no safe move to propose
        best = min(holding, key=lambda o: o.avg_cost_per_req)
        delta = best.avg_cost_per_req - current.avg_cost_per_req
        pct = (delta / current.avg_cost_per_req) if current.avg_cost_per_req else None
        return Recommendation(
            segment_key=seg.segment_key,
            kind="guardrail",
            current_config=current.config,
            proposed_config=best.config,
            est_cost_delta_pct=pct,
            est_cost_delta_per_req=delta,
            current_quality=current.quality,
            proposed_quality=best.quality,
            sample_size=best.n,
            confidence=_confidence(current.n, best.n, min_n),
            rationale=(
                f"Current config quality {current.quality:.2f} is below the SLA {min_q:.2f}. "
                f"Move to a config observed at quality {best.quality:.2f} (n={best.n})."
            ),
        )

    # ── Switch: a cheaper, well-sampled config holds the SLA ─────────────────
    switchable = [o for o in cheaper if holds_sla(o) and o.n >= min_n]
    if switchable:
        best = min(switchable, key=lambda o: o.avg_cost_per_req)
        delta = best.avg_cost_per_req - current.avg_cost_per_req
        pct = (delta / current.avg_cost_per_req) if current.avg_cost_per_req else None
        return Recommendation(
            segment_key=seg.segment_key,
            kind="switch",
            current_config=current.config,
            proposed_config=best.config,
            est_cost_delta_pct=pct,
            est_cost_delta_per_req=delta,
            current_quality=current.quality,
            proposed_quality=best.quality,
            sample_size=best.n,
            confidence=_confidence(current.n, best.n, min_n),
            rationale=(
                f"Cheaper config holds the SLA: quality {best.quality:.2f} ≥ {min_q:.2f} "
                f"at {abs(pct):.0%} lower cost (n={best.n})."
                if pct is not None
                else f"Cheaper config holds the SLA at quality {best.quality:.2f} (n={best.n})."
            ),
        )

    # ── Explore: a cheaper config looks promising but is under-sampled ───────
    promising = [
        o
        for o in cheaper
        if o.n < min_n and (o.quality is None or o.quality >= min_q)
    ]
    if promising:
        best = min(promising, key=lambda o: o.avg_cost_per_req)
        delta = best.avg_cost_per_req - current.avg_cost_per_req
        pct = (delta / current.avg_cost_per_req) if current.avg_cost_per_req else None
        q_txt = f"{best.quality:.2f}" if best.quality is not None else "unknown"
        return Recommendation(
            segment_key=seg.segment_key,
            kind="explore",
            current_config=current.config,
            proposed_config=best.config,
            est_cost_delta_pct=pct,
            est_cost_delta_per_req=delta,
            current_quality=current.quality,
            proposed_quality=best.quality,
            sample_size=best.n,
            confidence="low",
            rationale=(
                f"A cheaper config (~{abs(pct):.0%} lower cost) has early quality {q_txt} "
                f"but only n={best.n} (< {min_n}). Canary it to confirm before switching."
                if pct is not None
                else f"A cheaper config has early quality {q_txt} but only n={best.n}. Canary to confirm."
            ),
        )

    return None


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "kinds": ["switch", "explore", "guardrail"]}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    recs: list[Recommendation] = []
    for seg in req.segments:
        rec = _analyze_segment(seg, req)
        if rec is not None:
            recs.append(rec)
    # Biggest wins first (most-negative cost delta), guardrails always surfaced.
    recs.sort(key=lambda r: (r.kind != "guardrail", r.est_cost_delta_per_req or 0.0))
    return AnalyzeResponse(recommendations=recs)
