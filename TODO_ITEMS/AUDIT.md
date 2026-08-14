# RunLedger — Feature Audit Matrix

**Purpose:** Track audit status of every feature across all delivery surfaces.
**How to use:** Mark each cell as you audit: `✅` = verified working, `⚠️` = partial/buggy, `❌` = missing/broken, `—` = N/A, `🔲` = not yet audited.

**Last updated:** 2026-08-14

## Audited Status Overrides (2026-08-14)

Use this section as the current source of truth for rows that have already been reviewed against the real codebase and UI. The large matrix below still contains legacy symbol-encoding issues, so these overrides bridge the current completed work until that table is normalized.

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 1.2 | Organizations and tenants | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Reflects `/organizations` plus the completed Organization Console flow at `/organization`. |
| 1.3 | Workspaces | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `OK` | `N/A` | `N/A` | End-to-end CRUD is complete; examples are indirect rather than a dedicated workspace-only sample. |
| 1.4 | Users and memberships | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Backed by the completed org/access audit and the shared access-foundation smoke coverage. |
| 1.5 | API keys | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Create/list/detail/update/revoke flows are covered across UI, docs, Postman, and scripts. |
| 1.6 | RBAC and role-aware access | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Docs and UI behavior are aligned; examples remain indirect. |
| 1.7 | Platform settings | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Strong sub-surfaces exist, but `/settings` remains an umbrella route rather than one finished feature. |
| 1.8 | Onboarding and product tour | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `N/A` | `N/A` | Onboarding now owns the primary setup/discovery story for Claude, Codex, MCP, telemetry, and existing-stack guidance, but it remains a guide surface rather than a managed CRUD domain. |
| 2.3 | OTLP ingest | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | OTLP is now owned by Observability via `/monitoring/telemetry`, with `/otlp` retained as a compatibility redirect. |
| 2.6 | MCP ingest and control plane | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | MCP is now fully consolidated under `/mcp-registry`, which owns setup guidance, server CRUD, permission policies, tool testing, and call history. The legacy `/mcp` route remains only as a compatibility redirect into the setup tab. |
| 4.1 | Gateway routes | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `/gateway` now supports real route-management lifecycle depth in the shipped UI: routes, routing groups, policies, and pass-through endpoints all expose edit/update flows in addition to create/list/toggle/delete. The Rust runtime split remains reflected correctly across docs, Postman, examples, labs, and scripts; the remaining broader TypeScript issues observed during verification were pre-existing chart formatter errors outside the gateway surface. |
| 4.2 | Provider profiles | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | `/provider-profiles` is a finished workspace pricing surface with list/create/update/delete, YAML import, example download, sync/reprice actions, Postman coverage, a runnable example, and both manual-lab and automated simulation support. README coverage is still indirect rather than a dedicated product callout. |
| 4.9 | Rate limits | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | Rate limits are no longer treated as a standalone product surface. As of Friday, August 14, 2026, `/rate-limits` is only a compatibility redirect to `/gateway`; Gateway now owns the real runtime overview through `/gateway/rate-limits/overview`, route/pass-through throttles, and embedded quota-management panels for API-key tiers and per-model quotas, while Budget Tiers and Model Budgets remain the compatibility home for those same quota controls. |
| 5.1 | Exact cache | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Cache is now treated as part of Gateway rather than a separate product area. Exact cache behavior is reflected through gateway runtime execution, `/gateway` route controls, gateway stats, docs, Postman, examples, and scripts; `/response-cache` remains only as a compatibility redirect while cache profile lifecycle now lives directly inside the Gateway UI and backend CRUD. |
| 5.2 | Semantic cache | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Semantic cache ownership has been collapsed into Gateway. Persistent control now spans both route-level `semantic_cache_enabled` toggles and in-Gateway cache-profile lifecycle management with detail drill-in, while the surrounding docs/examples/scripts/Postman flow remains centered on Gateway rather than a standalone response-cache surface. |
| 6.5 | Budget tiers | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | As of Friday, August 14, 2026, budget-tier management is still fully implemented, but the primary UI ownership has been collapsed into Gateway. `/budget-tiers` now exists only as a compatibility redirect to `/gateway#gateway-quota-tiers`, while backend CRUD, tier assignment, Postman coverage, and automation support remain intact. |
| 6.7 | Model budgets | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `NO` | `OK` | `N/A` | `N/A` | As of Friday, August 14, 2026, model-budget management is now primarily owned by Gateway. `/model-budgets` is only a compatibility redirect to `/gateway#gateway-model-quotas`, the backend lifecycle now includes create/list/update/delete, and operators no longer need to use a separate manual UUID-entry page to manage per-key model quotas. |
| 7.15 | Access groups | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Full CRUD is complete; example coverage is present mainly through shared access-foundation flows. |
| 8.7 | Projects | `LEGACY` | `LEGACY` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `N/A` | `N/A` | The active Org & Access surface has been removed, the route now redirects to Workspaces, and the public backend compatibility router is no longer mounted. Remaining dependencies are now internal legacy cleanup instead of active product surface debt. |
| 8.8 | AI hub | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | `/ai-hub` now behaves like a finished workspace model catalog with real CRUD, provider sync, access-request tracking, deprecation controls, docs/navigation coverage, Postman requests, a manual lab, an automated smoke script, and a runnable example. |
| 8.6 | Plugins | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Plugin visibility is now treated as part of onboarding/setup discovery rather than a standalone integrations destination, but the underlying management surface is still partial. |
| 9.6 | Kafka export configs | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | CRUD is now exposed from Organization Console -> Destinations, with docs/Postman/script coverage updated. |
| 9.9 | OTEL collector | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collector docs, telemetry UI, ingest endpoints, labs, scripts, and compose profile are aligned. |

---

## Legend

| Column | What to check |
|--------|---------------|
| **Backend** | API endpoint exists, returns correct data, handles errors, has auth |
| **UI Surface** | Dashboard page renders, data loads, actions work, responsive |
| **Docs** | `docs/*.md` coverage — setup, usage, architecture, troubleshooting |
| **README** | Feature mentioned in top-level README.md with accurate description |
| **Examples** | `examples/*.py` or `examples/ts/*.ts` — working code sample |
| **Postman** | Request exists in `postman/RunLedger.postman_collection.json` |
| **Manual Lab** | Step-by-step lab doc (was `labs/*.md`, now `docs/labs/*.md` or scenarios) |
| **Automated Script** | `scripts/**/*.py` — seed, simulate, or integration script that exercises the feature |
| **Infra** | `docker-compose.yml` service/config — container, volume, healthcheck |
| **Supporting Infra** | External dependencies (Qdrant, Redis, Kafka, OTEL, MinIO, Ollama, etc.) |

---

## 1. Platform Core

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 1.1 | Platform bootstrap | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 1.2 | Organizations and tenants | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 1.3 | Workspaces | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 1.4 | Users and memberships | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 1.5 | API keys | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 1.6 | RBAC and role-aware access | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 1.7 | Platform settings | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 1.8 | Onboarding and product tour | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 2. Instrumentation & Ingest

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 2.1 | Python SDK | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 2.2 | TypeScript SDK | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 2.3 | OTLP ingest | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 2.4 | OpenInference ingest | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 2.5 | Webhook ingest | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 2.6 | MCP ingest and control plane | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 2.7 | Session and end-user attribution | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 2.8 | Trace/run correlation | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 3. Observability

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 3.1 | Dashboard | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.2 | Runs | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.3 | Run detail | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.4 | Sessions | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.5 | Session detail | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.6 | Request flow | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.7 | Request explorer | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.8 | Analytics | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.9 | Economics | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.10 | Users analytics | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.11 | Engineering | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.12 | Model usage | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.13 | Monitoring | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.14 | Model scorecards | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.15 | Replay lab | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.16 | Runbooks | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.17 | Optimization simulator | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.18 | Cost and savings views | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.19 | Outcomes and ROI | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 3.20 | Evaluations (score submit) | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 4. Gateway & Runtime Controls

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 4.1 | Gateway routes | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.2 | Provider profiles | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.3 | Routing policies | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.4 | Routing groups | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.5 | Fallback chains | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.6 | Deployment health | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.7 | Pass-through endpoints | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.8 | Runtime controls | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.9 | Rate limits | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 4.10 | Benchmarking | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 5. Optimization

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 5.1 | Exact cache | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 5.2 | Semantic cache | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 5.3 | Context compiler | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 5.4 | Prompt compression | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 5.5 | Intelligent routing | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 5.6 | Tool filtering | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 5.7 | Optimization flywheel | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 6. FinOps

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 6.1 | Metering | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.2 | Pricing and provider pricing import | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.3 | Cost attribution | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.4 | Budgets | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.5 | Budget tiers | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.6 | Budget overrides | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.7 | Model budgets | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.8 | Chargeback | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.9 | Billing summary and periods | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 6.10 | Ledger | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 7. Governance

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 7.1 | Prompt registry and versions | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.2 | Evaluation studio | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.3 | Datasets and experiments | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.4 | Guardrails and content safety | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.5 | Approvals | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.6 | Alerts | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.7 | Retention | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.8 | Policy dry-run | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.9 | Governance pack and audit | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.10 | Data capture studio | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.11 | Tag management | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.12 | Search tools | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.13 | Tool registry | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.14 | Tool policies | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.15 | Access groups | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 7.16 | Security settings | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 8. Agentic & Admin Surfaces

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 8.1 | Agents | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.2 | Workflows | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.3 | Vector stores | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.4 | API playground | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.5 | MCP registry | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.6 | Plugins | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.7 | Projects | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.8 | AI hub | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 8.9 | Optimization opportunities | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 9. Operations & Integrations

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 9.1 | SMTP settings and email delivery | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.2 | Email delivery history and reports | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.3 | Backup target config | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.4 | Backup runs and snapshots | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.5 | Restore drill | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.6 | Kafka export configs | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.7 | Kafka delivery history, retry, DLQ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.8 | Redpanda live streaming demo | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.9 | OTEL collector | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.10 | Queue visibility | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.11 | Feature flags | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.12 | Storage posture and infra policy | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.13 | Local TLS and demo proxy | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 9.14 | Deployment profiles | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## 10. Local Models & External Stacks

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra |
|---|---------|---------|-----|------|--------|----------|---------|------------|-------------|-------|------------------|
| 10.1 | Ollama model discovery | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 10.2 | Local model pricing import | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 10.3 | HomeLab AgentTest traffic | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 10.4 | LocalAIAgentStack bootstrap | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 10.5 | LocalAIAgentStack Python agents | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 10.6 | Codex workspace traffic | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 10.7 | OpenWebUI workspace traffic | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| 10.8 | Hermes/OpenHands/Desktop agent traffic | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

---

## Quick Reference: What Exists Today

### Docs (`docs/`)
| File | Covers |
|------|--------|
| `architecture.md` | System architecture overview |
| `deployment.md` | Production deployment guide |
| `backup-restore.md` | Backup and restore procedures |
| `collector.md` | OTEL collector setup |
| `otlp.md` | OTLP ingest guide |
| `openinference.md` | OpenInference integration |
| `litellm.md` | LiteLLM integration |
| `helm.md` | Helm chart deployment |
| `ha.md` | High availability setup |
| `infra-hardening.md` | Infrastructure hardening |
| `upgrade.md` | Version upgrade guide |
| `versioning-policy.md` | Versioning policy |
| `release-checklist.md` | Release checklist |
| `integration-options-mcp.md` | MCP integration options |
| `product-data-alignment.md` | Product/data alignment |
| `demo-script.md` | Demo script |
| `demo-runbook.md` | Demo runbook |
| `demo-asset-bundle.md` | Demo assets |
| `demo-visual-regression.md` | Visual regression testing |
| `administration/email-delivery.md` | Email delivery admin guide |
| `integrations/desktop-agent-setup.md` | Desktop agent integration |

### Examples (`examples/`)
| File | Covers |
|------|--------|
| `01_openai_basic.py` | Basic OpenAI SDK integration |
| `02_openai_multi_turn.py` | Multi-turn conversations |
| `03_langchain_chain.py` | LangChain integration |
| `04_langgraph_agent.py` | LangGraph agent |
| `05_fastapi_service.py` | FastAPI service integration |
| `06_ollama_local.py` | Local Ollama usage |
| `07_analytics_query.py` | Analytics API queries |
| `08_budget_enforcement.py` | Budget enforcement demo |
| `09_economics_query.py` | Economics API queries |
| `10_replay_experiment.py` | Replay experiments |
| `11_ledger_verify.py` | Ledger verification |
| `12_settings.py` | Settings API |
| `13_integrations.py` | Integration examples |
| `14_evaluations.py` | Evaluation API |
| `15_prompts.py` | Prompt management |
| `16_sessions.py` | Session tracking |
| `17_alerts.py` | Alert rules |
| `18_gateway.py` | Gateway usage |
| `19_policy_check.py` | Policy checking |
| `20_anthropic_basic.py` | Anthropic SDK integration |
| `20_tool_registry_ollama.py` | Tool registry with Ollama |
| `21_mcp_example.py` | MCP usage |
| `22_otlp_ingest.py` | OTLP ingest |
| `24_openinference_otel.py` | OpenInference + OTEL |
| `25_outcomes_roi.py` | Outcomes and ROI |
| `27_approvals_workflow.py` | Approval workflows |
| `30_langchain_gateway_otel.py` | LangChain + Gateway + OTEL |
| `31_litellm_basic.py` | LiteLLM basic |
| `32_litellm_proxy.py` | LiteLLM proxy |
| `33_semantic_cache.py` | Semantic cache |
| `34_context_compiler.py` | Context compiler |
| `35_prompt_compression.py` | Prompt compression |
| `36_intelligent_routing.py` | Intelligent routing |
| `37_cognitive_layer.py` | Cognitive layer |
| `38_tool_filtering_skills.py` | Tool filtering |
| `39_flywheel.py` | Optimization flywheel |
| `ts/01_openai_basic.ts` | TypeScript OpenAI |
| `ts/02_multi_turn.ts` | TypeScript multi-turn |
| `ts/03_vercel_ai.ts` | TypeScript Vercel AI |

### Postman (`postman/`)
| File | Notes |
|------|-------|
| `RunLedger.postman_collection.json` | Full API collection — audit individual requests against features |
| `RunLedger.postman_environment.json` | Environment variables |

### Scripts (`scripts/`)
| Path | Covers |
|------|--------|
| `full_simulate.py` | Full platform simulation |
| `generate_postman.py` | Postman collection generator |
| `cleanup.py` | Data cleanup |
| `bench/run_benchmark.py` | Gateway benchmarking |
| `bench/report.py` | Benchmark reporting |
| `streaming/kafka_consumer.py` | Kafka consumer demo |
| `scenarios/hosted/01_saas_support.py` | SaaS support scenario |
| `scenarios/hosted/02_ml_research.py` | ML research scenario |
| `scenarios/hosted/03_ecommerce_agents.py` | E-commerce agents scenario |
| `scenarios/ollama/01-07_*.py` | 7 Ollama-based scenarios |
| `scenarios/labs/agents/lab_01-05_*.py` | 5 agent lab scenarios |
| `localai/bootstrap_runledger_org.py` | LocalAI org bootstrap |
| `localai/generate_agent_traffic.py` | Agent traffic generation |
| `localai/generate_otlp_traffic.py` | OTLP traffic generation |
| `localai/register_all_gateway_routes.py` | Gateway route registration |
| `localai/seed_gateway_routes_all_workspaces.py` | Multi-workspace gateway seed |
| `localai/inject_mcp_configs.py` | MCP config injection |
| `localai/localai_s3_backup.py` | S3 backup script |
| `localai/runledger_auto_init.py` | Auto-initialization |
| `runledger/validate_mcp_connection.py` | MCP connection validation |
| `runledger/mcp_stdio_bridge.py` | MCP stdio bridge |

### Infra (docker-compose.yml services)
| Service | Profile | Purpose |
|---------|---------|---------|
| `runledger-postgres` | core | Primary database |
| `runledger-redis` | core | Cache, rate limits, budget counters |
| `runledger-api` | core | FastAPI application |
| `runledger-worker` | core | Celery worker |
| `runledger-beat` | core | Celery beat scheduler |
| `runledger-web` | core | Next.js dashboard |
| `runledger-qdrant` | infra | Vector store |
| `runledger-minio` | backup | S3-compatible object storage |
| `runledger-redpanda` | streaming | Kafka-compatible event streaming |
| `runledger-redpanda-console` | streaming | Redpanda management UI |
| `runledger-otel-collector` | observability | OpenTelemetry collector |
| `runledger-embedding-svc` | aux | Text embedding service |
| `runledger-semantic-cache-svc` | aux | Semantic cache service |
| `runledger-mcp-gateway` | aux | MCP gateway |
| `runledger-memory-db` | infra | Letta memory database (pgvector) |
| `runledger-letta` | infra | Letta memory service |
| `runledger-memory-svc` | aux | Memory abstraction layer |
| `runledger-kg-svc` | aux | Knowledge graph (Kuzu) |
| `runledger-skill-registry` | aux | Skill registry |
| `runledger-reranker` | aux | Reranker service |
| `runledger-compression` | aux | Prompt compression |
| `runledger-router` | aux | Intelligent routing |
| `runledger-context-compiler` | aux | Context compilation |
| `runledger-flywheel` | aux | Optimization flywheel |
| `runledger-caddy` | tls-demo | TLS termination proxy |

---

## Audit Progress Summary

| Section | Features | Audited | Verified | Partial | Missing | N/A |
|---------|----------|---------|----------|---------|---------|-----|
| 1. Platform Core | 8 | 0 | 0 | 0 | 0 | 0 |
| 2. Instrumentation & Ingest | 8 | 0 | 0 | 0 | 0 | 0 |
| 3. Observability | 20 | 0 | 0 | 0 | 0 | 0 |
| 4. Gateway & Runtime | 10 | 0 | 0 | 0 | 0 | 0 |
| 5. Optimization | 7 | 0 | 0 | 0 | 0 | 0 |
| 6. FinOps | 10 | 0 | 0 | 0 | 0 | 0 |
| 7. Governance | 16 | 0 | 0 | 0 | 0 | 0 |
| 8. Agentic & Admin | 9 | 0 | 0 | 0 | 0 | 0 |
| 9. Operations & Integrations | 14 | 0 | 0 | 0 | 0 | 0 |
| 10. Local Models & Stacks | 8 | 0 | 0 | 0 | 0 | 0 |
| **TOTAL** | **110** | **0** | **0** | **0** | **0** | **0** |
