"""
Optimization flywheel orchestration (Phase 7).

The flywheel closes the cost x quality loop. RunLedger already records the tuples it needs —
`gateway_requests` carries the config each call ran under (Phase 7 `config_fingerprint`) plus
tokens; `outcomes` and `score_events` carry quality. This module:

  1. Aggregates those tuples into per-segment observations of (config → cost, quality).
  2. Sends them to the stateless `flywheel-svc` analyzer, which returns per-segment
     recommendations (switch / explore / guardrail) honouring the SLA and action space.
  3. Persists the recommendations and, in `auto` mode, applies the safe ones and monitors
     applied ones for SLA breach (auto-rollback).

Design notes / honest limits:
  * Cost + config come from the gateway's own traffic (`gateway_requests`).
  * Quality attaches at the **model** grain (outcomes/scores link to a model via
    `provider_calls`), matching the existing `outcome_optimized` / `cost_optimized` policies.
  * Auto-apply only mutates routes for **alias**-segmented recommendations (segment == route);
    for `outcome_type` / `task_class` segments the recommendation is advisory (approval-only).

Fail-open: any error aborts the run without touching production config.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.flywheel import FlywheelRecommendation, FlywheelSettings
from runledger_api.models.gateway import GatewayRoute
from runledger_api.services.pricing import calculate_cost

log = logging.getLogger(__name__)

_SVC_URL = os.getenv("FLYWHEEL_SVC_URL", "").rstrip("/")
_TIMEOUT = float(os.getenv("FLYWHEEL_TIMEOUT_SECONDS", "30"))
# Neutral token-proportional fallback ($/token) when a model has no pricing row, so
# cost comparisons remain orderable in dev/local setups.
_FALLBACK_RATE = Decimal("0.000001")


def enabled() -> bool:
    return bool(_SVC_URL)


def _uuid(workspace_id: Any) -> uuid.UUID:
    """Bind workspace ids as real UUIDs so asyncpg types them as uuid (not varchar)."""
    return workspace_id if isinstance(workspace_id, uuid.UUID) else uuid.UUID(str(workspace_id))


# ── Settings ────────────────────────────────────────────────────────────────────


async def get_settings(db: AsyncSession, workspace_id: Any) -> FlywheelSettings:
    """Fetch the workspace flywheel settings, creating defaults on first access."""
    row = await db.get(FlywheelSettings, workspace_id)
    if row is None:
        row = FlywheelSettings(workspace_id=workspace_id)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


# ── Aggregation: (segment, config) → cost, quality ───────────────────────────────


async def _provider_by_model(db: AsyncSession, workspace_id: Any) -> dict[str, str]:
    rows = await db.execute(
        select(GatewayRoute.target_model, GatewayRoute.provider).where(
            GatewayRoute.workspace_id == workspace_id
        )
    )
    return {m: p for m, p in rows.all()}


async def _quality_by_model(
    db: AsyncSession,
    workspace_id: Any,
    cutoff: datetime,
    metric: dict[str, Any],
    *,
    by_outcome_type: bool = False,
) -> dict[Any, float]:
    """
    Per-model quality over the window, per the chosen metric. Keyed by ``model`` normally,
    or by ``(outcome_type, model)`` when ``by_outcome_type`` is set.

    metric = {"type": "outcome_success" | "eval_score" | "blend", "weight": w, "evaluator": name?}
    """
    mtype = metric.get("type", "blend")
    weight = float(metric.get("weight", 0.5))
    evaluator = metric.get("evaluator")

    outcome_q: dict[Any, float] = {}
    eval_q: dict[Any, float] = {}

    if mtype in ("outcome_success", "blend"):
        grp = "o.outcome_type, pc_first.model" if by_outcome_type else "pc_first.model"
        rows = await db.execute(
            text(f"""
                SELECT {grp},
                       AVG(CASE WHEN o.success THEN 1.0 ELSE 0.0 END) AS q
                FROM outcomes o
                JOIN agent_runs ar ON ar.id = o.run_id
                JOIN (
                    SELECT DISTINCT ON (run_id) run_id, model
                    FROM provider_calls ORDER BY run_id, created_at ASC
                ) pc_first ON pc_first.run_id = o.run_id
                WHERE o.workspace_id = :ws AND o.created_at >= :cutoff
                GROUP BY {grp}
            """).bindparams(ws=_uuid(workspace_id), cutoff=cutoff)
        )
        for r in rows.all():
            key = (r[0], r[1]) if by_outcome_type else r[0]
            outcome_q[key] = float(r.q)

    if mtype in ("eval_score", "blend"):
        name_clause = "AND se.name = :ev" if evaluator else ""
        grp = "o.outcome_type, pc.model" if by_outcome_type else "pc.model"
        join_outcome = (
            "JOIN outcomes o ON o.run_id = ar.id" if by_outcome_type else ""
        )
        bind: dict[str, Any] = {"ws": _uuid(workspace_id), "cutoff": cutoff}
        if evaluator:
            bind["ev"] = evaluator
        rows = await db.execute(
            text(f"""
                SELECT {grp}, AVG(se.value) AS q
                FROM score_events se
                JOIN agent_runs ar ON ar.id = se.run_id
                JOIN provider_calls pc ON pc.run_id = ar.id
                {join_outcome}
                WHERE se.workspace_id = :ws AND se.created_at >= :cutoff {name_clause}
                GROUP BY {grp}
            """).bindparams(**bind)
        )
        for r in rows.all():
            key = (r[0], r[1]) if by_outcome_type else r[0]
            # score_events.value is assumed normalised to 0..1; clamp defensively.
            eval_q[key] = max(0.0, min(1.0, float(r.q)))

    # Combine
    if mtype == "outcome_success":
        return outcome_q
    if mtype == "eval_score":
        return eval_q
    keys = set(outcome_q) | set(eval_q)
    blended: dict[Any, float] = {}
    for k in keys:
        o = outcome_q.get(k)
        e = eval_q.get(k)
        if o is not None and e is not None:
            blended[k] = weight * o + (1 - weight) * e
        else:
            blended[k] = o if o is not None else e  # type: ignore[assignment]
    return blended


async def _aggregate(db: AsyncSession, workspace_id: Any, s: FlywheelSettings) -> list[dict[str, Any]]:
    """Build the analyzer's per-segment observations from recorded traffic."""
    cutoff = datetime.now(UTC) - timedelta(days=int(s.lookback_days))
    seg_by = s.segment_by
    by_otype = seg_by == "outcome_type"

    if seg_by == "alias":
        seg_expr = "model_requested"
    elif seg_by == "task_class":
        seg_expr = "COALESCE(segment_key, model_requested)"
    else:  # outcome_type — cost/config not segmentable in gateway_requests; segment via quality
        seg_expr = "'all'"

    rows = await db.execute(
        text(f"""
            SELECT {seg_expr} AS seg,
                   config_fingerprint AS fp,
                   model_used AS model,
                   COUNT(*) AS n,
                   COALESCE(SUM(input_tokens), 0) AS in_tok,
                   COALESCE(SUM(output_tokens), 0) AS out_tok
            FROM gateway_requests
            WHERE workspace_id = :ws AND created_at >= :cutoff
              AND status = 'success' AND cache_hit = false
              AND config_fingerprint IS NOT NULL
            GROUP BY seg, config_fingerprint, model_used
        """).bindparams(ws=_uuid(workspace_id), cutoff=cutoff)
    )
    groups = rows.all()
    if not groups:
        return []

    provider_map = await _provider_by_model(db, workspace_id)
    quality = await _quality_by_model(db, workspace_id, cutoff, s.quality_metric, by_outcome_type=by_otype)

    async def _avg_cost(model: str | None, in_tok: int, out_tok: int, n: int) -> float:
        if n <= 0:
            return 0.0
        cost: Decimal | None = None
        if model and model in provider_map:
            cost = await calculate_cost(
                db, provider=provider_map[model], model=model,
                input_tokens=int(in_tok), output_tokens=int(out_tok),
            )
        if cost is None:
            cost = Decimal(int(in_tok) + int(out_tok)) * _FALLBACK_RATE
        return float(cost) / n

    if by_otype:
        # One segment per outcome_type; observations = fingerprint/model groups scored by
        # that outcome_type's per-model quality.
        otypes = sorted({k[0] for k in quality})
        segments: list[dict[str, Any]] = []
        for ot in otypes:
            observations = []
            for g in groups:
                q = quality.get((ot, g.model))
                observations.append({
                    "config": g.fp,
                    "n": int(g.n),
                    "avg_cost_per_req": await _avg_cost(g.model, g.in_tok, g.out_tok, int(g.n)),
                    "quality": q,
                    "success_rate": q,
                })
            if observations:
                segments.append({"segment_key": ot, "observations": observations})
        return segments

    # alias / task_class: segment_key from the query, quality by model (global)
    by_seg: dict[str, list[dict[str, Any]]] = {}
    for g in groups:
        q = quality.get(g.model)
        by_seg.setdefault(g.seg, []).append({
            "config": g.fp,
            "n": int(g.n),
            "avg_cost_per_req": await _avg_cost(g.model, g.in_tok, g.out_tok, int(g.n)),
            "quality": q,
            "success_rate": q,
        })
    return [{"segment_key": k, "observations": v} for k, v in by_seg.items()]


# ── Run the loop ─────────────────────────────────────────────────────────────────


async def run_analysis(db: AsyncSession, workspace_id: Any) -> dict[str, Any]:
    """Aggregate → analyze → persist recommendations. In auto mode, apply the safe ones."""
    if not enabled():
        return {"status": "disabled", "recommendations": 0}
    s = await get_settings(db, workspace_id)
    if not s.enabled:
        return {"status": "off", "recommendations": 0}

    segments = await _aggregate(db, workspace_id, s)
    if not segments:
        return {"status": "no-data", "recommendations": 0}

    payload = {
        "segment_by": s.segment_by,
        "min_quality": float(s.min_quality),
        "min_sample_size": int(s.min_sample_size),
        "action_space": list(s.action_space or []),
        "segments": segments,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{_SVC_URL}/analyze", json=payload)
            resp.raise_for_status()
            recs = resp.json().get("recommendations", [])
    except Exception as exc:  # noqa: BLE001 — fail-open
        log.warning("flywheel_analyze_skipped ws=%s error=%s", workspace_id, str(exc))
        return {"status": "error", "recommendations": 0}

    # Supersede prior pending recs for this workspace; write the fresh set.
    await db.execute(
        update(FlywheelRecommendation)
        .where(
            FlywheelRecommendation.workspace_id == workspace_id,
            FlywheelRecommendation.status == "pending",
        )
        .values(status="superseded", updated_at=datetime.now(UTC))
    )
    created: list[FlywheelRecommendation] = []
    for r in recs:
        rec = FlywheelRecommendation(
            workspace_id=workspace_id,
            segment_by=s.segment_by,
            segment_key=r["segment_key"],
            kind=r["kind"],
            current_config=r.get("current_config") or {},
            proposed_config=r.get("proposed_config") or {},
            est_cost_delta_pct=_dec(r.get("est_cost_delta_pct")),
            est_cost_delta_per_req=_dec(r.get("est_cost_delta_per_req")),
            current_quality=_dec(r.get("current_quality")),
            proposed_quality=_dec(r.get("proposed_quality")),
            min_quality=s.min_quality,
            sample_size=int(r.get("sample_size") or 0),
            confidence=r.get("confidence", "low"),
            rationale=r.get("rationale"),
            status="pending",
            apply_mode=s.apply_mode,
        )
        db.add(rec)
        created.append(rec)
    await db.commit()

    applied = 0
    if s.apply_mode == "auto":
        for rec in created:
            await db.refresh(rec)
            # Auto-apply only well-supported, alias-scoped, non-explore proposals.
            auto_ok = (
                rec.segment_by == "alias"
                and rec.confidence in ("high", "medium")
                and rec.kind in ("switch", "guardrail")
            )
            if auto_ok and await apply_recommendation(db, workspace_id, rec.id, mode="auto"):
                applied += 1

    return {"status": "ok", "recommendations": len(created), "auto_applied": applied}


# ── Apply / dismiss / rollback ──────────────────────────────────────────────────


async def _primary_route(db: AsyncSession, workspace_id: Any, alias: str) -> GatewayRoute | None:
    rows = await db.execute(
        select(GatewayRoute)
        .where(
            GatewayRoute.workspace_id == workspace_id,
            GatewayRoute.alias == alias,
            GatewayRoute.is_active == True,  # noqa: E712
        )
        .order_by(GatewayRoute.priority.asc())
        .limit(1)
    )
    return rows.scalar_one_or_none()


def _apply_config_to_route(route: GatewayRoute, proposed: dict[str, Any]) -> None:
    """Patch a route's optimization config from a proposed fingerprint (in place)."""
    if "semantic_cache" in proposed:
        route.semantic_cache_enabled = bool(proposed["semantic_cache"])
    if "context_compiler" in proposed:
        route.context_compiler_enabled = bool(proposed["context_compiler"])
        cfg = dict(route.context_compiler_config or {})
        if "stages" in proposed and isinstance(proposed["stages"], list):
            stages = dict(cfg.get("stages") or {})
            for st in proposed["stages"]:
                stages[st] = True
            cfg["stages"] = stages
        if "compression_rate" in proposed:
            cfg["compression_rate"] = proposed["compression_rate"]
        route.context_compiler_config = cfg
    # Model swap: only when the proposed model is a concrete, different target.
    if proposed.get("model") and proposed["model"] != route.target_model:
        route.target_model = proposed["model"]


async def apply_recommendation(
    db: AsyncSession, workspace_id: Any, rec_id: Any, *, mode: str = "approval"
) -> bool:
    """
    Apply a recommendation. For alias-segmented recs this patches the alias's primary route
    (and snapshots the prior route config into current_config for rollback). Non-alias
    segments are advisory: the rec is marked applied (acknowledged) without mutating routes.
    Returns True if a route was actually mutated.
    """
    rec = await db.get(FlywheelRecommendation, rec_id)
    if rec is None or rec.workspace_id != workspace_id or rec.status != "pending":
        return False

    mutated = False
    if rec.segment_by == "alias":
        route = await _primary_route(db, workspace_id, rec.segment_key)
        if route is not None:
            # Snapshot the current route config so a rollback can restore it.
            rec.current_config = {
                **(rec.current_config or {}),
                "_route_snapshot": {
                    "target_model": route.target_model,
                    "semantic_cache_enabled": route.semantic_cache_enabled,
                    "context_compiler_enabled": route.context_compiler_enabled,
                    "context_compiler_config": route.context_compiler_config,
                },
            }
            _apply_config_to_route(route, rec.proposed_config or {})
            rec.applied_route_id = route.id
            mutated = True

    rec.status = "applied"
    rec.apply_mode = mode
    rec.applied_at = datetime.now(UTC)
    rec.updated_at = datetime.now(UTC)
    await db.commit()
    return mutated


async def dismiss_recommendation(db: AsyncSession, workspace_id: Any, rec_id: Any) -> bool:
    rec = await db.get(FlywheelRecommendation, rec_id)
    if rec is None or rec.workspace_id != workspace_id or rec.status != "pending":
        return False
    rec.status = "dismissed"
    rec.updated_at = datetime.now(UTC)
    await db.commit()
    return True


async def check_guardrails(db: AsyncSession, workspace_id: Any) -> int:
    """
    Re-evaluate applied, route-mutating recommendations: if the segment's current quality has
    dropped below the SLA, roll the route back to its snapshot. Returns rollback count.
    """
    s = await get_settings(db, workspace_id)
    cutoff = datetime.now(UTC) - timedelta(days=int(s.lookback_days))
    quality = await _quality_by_model(
        db, workspace_id, cutoff, s.quality_metric, by_outcome_type=(s.segment_by == "outcome_type")
    )
    rows = await db.execute(
        select(FlywheelRecommendation).where(
            FlywheelRecommendation.workspace_id == workspace_id,
            FlywheelRecommendation.status == "applied",
            FlywheelRecommendation.applied_route_id.is_not(None),
        )
    )
    rolled = 0
    for rec in rows.scalars().all():
        model = (rec.proposed_config or {}).get("model")
        q = quality.get(model) if s.segment_by != "outcome_type" else quality.get((rec.segment_key, model))
        if q is not None and q < float(rec.min_quality):
            route = await db.get(GatewayRoute, rec.applied_route_id)
            snap = (rec.current_config or {}).get("_route_snapshot")
            if route is not None and snap:
                route.target_model = snap.get("target_model", route.target_model)
                route.semantic_cache_enabled = snap.get("semantic_cache_enabled", route.semantic_cache_enabled)
                route.context_compiler_enabled = snap.get("context_compiler_enabled", route.context_compiler_enabled)
                route.context_compiler_config = snap.get("context_compiler_config")
            rec.status = "rolled_back"
            rec.rationale = (rec.rationale or "") + f" [rolled back: quality {q:.2f} < SLA {float(rec.min_quality):.2f}]"
            rec.updated_at = datetime.now(UTC)
            rolled += 1
    if rolled:
        await db.commit()
    return rolled


def _dec(v: Any) -> Decimal | None:
    return None if v is None else Decimal(str(v))
