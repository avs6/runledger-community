# Gateway & Routing — GAP Matrix

Last updated: PENDING AUDIT

## Legend

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet audited |
| `OK` | Verified working |
| `PARTIAL` | Present but partial, buggy, or unclear |
| `MISSING` | Missing, broken, or disconnected |
| `LEGACY` | Legacy/transitional surface; do not expand |

---

## Feature Rows

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Provider profiles | `/provider-profiles` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P2 | `PENDING` | `4.2`, `6.2` | Verified against the current codebase and UI: backend supports list/create/update/delete plus import, example download, reprice flows, and now provider-profile budget counts; the dashboard exposes real admin actions with filters, workspace/global scope handling, and direct scoped budget links; docs, Postman, examples, and simulation/manual lab coverage are all present. Bundle A started a deeper cohesion pass on Friday, August 14, 2026 by tightening the provider-profile to budget-policy bridge. |
| Model gateway | `/gateway` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Absorb `Response cache` and `Rate limits` here rather than separate top-level items. | P2 | `PENDING` | `4.1`, `4.3`, `4.4`, `4.5`, `4.7`, `4.8`, `4.10`, `5.5`, `5.7` | The gateway control plane now clears the completion bar: routes, routing groups, routing policies, pass-through endpoints, response-cache profiles, runtime rate-limit overview, API-key quota tiers, and per-model quota controls all have real backend/UI ownership on the Gateway surface, while benchmarking, routing log, flywheel, docs, Postman, examples, and scripts remain aligned with the Rust data-plane split. Bundle A started a deeper cohesion pass on Friday, August 14, 2026 by clarifying Gateway-to-Budgets ownership and linking operators directly into the spend-policy surface. |
| Guardrails | `/guardrails` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P2 | `PENDING` | `7.4` | Completed on Friday, August 14, 2026. The `/guardrails` page now acts as a cohesive operator surface instead of a partial dashboard: it covers custom rule CRUD, built-in content filter management, template-driven rule creation, test playground execution, test-case creation/deletion, regression runs with visible reports, partner guardrail create/edit/delete/health flows, event false-positive feedback, alert evaluate/acknowledge actions, bulk enable/disable for selected rules, and a dedicated filterable/paginated violations log at `/guardrails/violations`. Backend, UI, docs, Postman, scripts, and examples are now aligned closely enough to treat Guardrails as feature-complete in this phase while keeping the runtime enforcement path Python-based as intended. |
| Response cache | `/response-cache` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Model gateway` route settings and cache analytics. | P2 | `PENDING` | `5.1`, `5.2` | Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/response-cache` page is no longer treated as a first-class product area and now exists only as a compatibility redirect into `/gateway`. The collapsed ownership is now complete rather than redirect-only: backend cache profile lifecycle includes create/list/get/update/delete plus stats, and the Gateway UI now exposes cache-profile create/edit/delete and detail drill-in alongside the existing route-level `semantic_cache_enabled` controls and cache analytics. |
| Rate limits | `/rate-limits` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Budgets`, `Budget tiers`, and `Model gateway` controls. | P2 | `PENDING` | `4.9`, `6.4`, `6.5` | Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/rate-limits` page now exists only as a compatibility redirect into `/gateway`, and the real ownership has been moved back into the primary features: Gateway now exposes a backend-driven runtime rate-limit overview for ingest/analytics/management/system tiers plus route/pass-through throttles and embedded API-key/model quota management, while Budget Tiers and Model Budgets remain the compatibility home for those same quota controls. |
