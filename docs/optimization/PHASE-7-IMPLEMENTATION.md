# Phase 7 — Optimization Flywheel (cost × quality SLA)

**Status: SHIPPED.** Closes the cost×quality loop — the capstone of Lane A (the enterprise
cost path). The data already existed; Phase 7 adds the loop that learns from it.

## Goal

> Minimize cost **subject to** a customer-defined quality floor.

RunLedger records `(config, cost, quality, outcome)` on every call. The flywheel reads those
tuples and, per traffic segment, finds the **cheapest optimization configuration that still holds
the quality SLA**, then recommends it — or, in `auto` mode, applies it (guardrailed, with
auto-rollback).

## Locked decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Apply mode | Per-workspace: `approval` (default) · `auto` (guardrailed + auto-rollback) · `off` |
| 2 | Action space | **Full config surface** — model/tier, compiler `stages`, `compression_rate`, cache threshold, routing |
| 3 | Quality metric | **User-configurable**: `outcome_success` · `eval_score` · `blend` (weighted) |
| 4 | Segmentation | Configurable; default `outcome_type` (also `task_class` = complexity×risk, or `alias`) |

## Architecture

```
gateway_requests (config_fingerprint + cost) ─┐
outcomes / score_events (quality by model) ───┴─► services/flywheel.py  (aggregate)
                                                       │
                                                       ▼
                                            runledger-flywheel (:8215)   ← stateless analyzer
                                                       │  /analyze
                                                       ▼
                                            flywheel_recommendations  (persisted)
                                                       │
                              approval → dashboard Apply/Dismiss   auto → apply + monitor → rollback
                                                       ▼
                                            GatewayRoute config (patched, snapshot for rollback)
```

- **Analyzer is stateless** (`apps/flywheel-svc`, internal :8109 / host :8215) — no DB, no auth.
  It ranks observed configs per segment: `switch` (cheaper config holds SLA), `explore` (cheaper
  but under-sampled → canary), `guardrail` (current config is below SLA → move to one that holds).
- **Orchestration** (`services/flywheel.py`) aggregates the tuples, calls the analyzer, persists
  recommendations, and applies/rolls-back.
- **Beat job** (`workers/flywheel.py`, `flywheel.analyze`, nightly) runs it per active workspace
  and checks guardrails on applied recommendations.

## What shipped

**Data layer**
- Migration `047` — `gateway_requests.config_fingerprint` (JSONB) + `segment_key` (text). The
  gateway stamps each inference with the model/tier + which stages were on + compression rate +
  cache/routing it ran under (`routers/gateway.py::_config_fingerprint`).
- Migration `048` — `flywheel_settings` (per-workspace SLA + behaviour) and
  `flywheel_recommendations` (the loop's output, with status tracking).
- Models: `models/flywheel.py`.

**Analyzer** — `apps/flywheel-svc` (`/health`, `/analyze`). Honours `action_space` (only proposes
changes to permitted dimensions), `min_quality`, `min_sample_size`; confidence from sample size.

**API** — `routers/flywheel.py` under `/gateway/flywheel`: `GET/PUT settings`,
`GET recommendations`, `POST recommendations/{id}/apply|dismiss`, `POST run`. Service in
`services/flywheel.py`.

**Wiring** — `runledger-flywheel` in `docker-compose.yml`; `FLYWHEEL_SVC_URL` on api/worker/mcp;
`FLYWHEEL_PORT=8215` in `.env.example`; beat schedule + celery include.

**MCP** — `flywheel_analyze(segments, …)` tool (proxies the stateless analyzer).

**Dashboard** — Gateway page "Optimization Flywheel" panel: enable, apply-mode, segment-by,
quality-metric, SLA, min-sample settings + recommendations list with Apply/Dismiss.

**Docs / examples** — `docs/optimization/flywheel.mdx` (+ nav + overview card + ports table),
`examples/39_flywheel.py`, Postman "Optimization Flywheel" + "Flywheel Service" folders + `flywheel_url`.

## Honest limits (documented, by design)

- **Observational, not experimental.** The flywheel only proposes configurations it has actually
  observed (or an `explore` of a thin one). It never blindly extrapolates.
- **Quality attaches at the model grain.** Outcomes/scores link to a model via `provider_calls`,
  matching the existing `outcome_optimized` / `cost_optimized` policies. Config-stage changes that
  don't change the model are evaluated on cost with quality monitored via the same model's trend.
- **Apply is scoped for safety.** Only `alias`-segmented recommendations patch a route directly
  (with a snapshot for rollback); `outcome_type` / `task_class` segments are advisory. Auto-apply
  only ever touches `alias`-segmented, high/medium-confidence `switch`/`guardrail` recommendations.

## Verification (on the running stack)

- Analyzer: `switch` (79% cheaper, SLA held, high confidence), `guardrail` (dominant config below
  SLA → proposes SLA-holder), and `action_space` gating (disallowed dimension → no recommendation).
- API: settings GET (creates defaults) / PUT (persists) / 422 on bad enum; `/run` executes the full
  aggregation and returns `no-data` on an empty window.
- **Full loop, organic:** seeded real `gateway_requests` (two configs of alias `chat`) + `score_events`,
  ran `/run` → persisted a `switch chat: gpt-4o → gpt-4o-mini` (−99% cost, quality 0.95→0.90 ≥ 0.85 SLA);
  listed it; applied it → the `chat` route's `target_model` flipped to `gpt-4o-mini` with a rollback
  snapshot stored. Seed data cleaned up afterward.

## Incidental fix

Pinned `mcp>=1.9.0,<2` (api `pyproject.toml` + mcp-gateway `requirements.txt`): `mcp 2.0.0` is a
breaking release that removed `mcp.server.fastmcp`, which broke the API image on rebuild. Regenerated
`uv.lock`.
