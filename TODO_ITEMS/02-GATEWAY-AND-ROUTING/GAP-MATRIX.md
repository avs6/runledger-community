# Gateway & Routing — GAP Matrix

Last updated: 2026-08-15

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
| Provider profiles | `/provider-profiles` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P2 | `OK` | `4.2`, `6.2` | Re-audited Saturday, August 15, 2026 against the current codebase. Backend supports list/create/update/delete plus YAML import, example download, sync, and reprice flows; the dashboard exposes real admin actions with scope filters, workspace/global handling, budget posture, and scoped budget links; docs, Postman, examples, and simulation/manual lab coverage are all present. The remaining weakness is cross-feature cohesion rather than provider-profile CRUD depth. External-rubric N/A review note: provider metadata is usually relevant to cost, runtime, observability, model intelligence, and governance posture, so several current `N/A` cohesion cells should be revisited. |
| Model gateway | `/gateway` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Absorb `Response cache` and `Rate limits` here rather than separate top-level items. | P2 | `RE-AUDIT REQUIRED` | `4.1`, `4.3`, `4.4`, `4.5`, `4.7`, `4.8`, `4.10`, `5.5`, `5.7` | Re-audited Thursday, August 21, 2026. WU-003 closed all FinOps cohesion gaps: GET /analytics/gateway-finops-posture returns route spend, budget coverage, overrides, notification channels, billing periods, and chargeback rules. Gateway page shows FinOps Posture card with drill-through to all 7 FinOps sub-features plus Cost & Savings. Docs (overview.mdx), Postman, and example updated. Remaining RE-AUDIT scope is support-surface consistency and broader cross-feature cohesion beyond FinOps. |
| Guardrails | `/guardrails` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate. | P2 | `RE-AUDIT REQUIRED` | `7.4` | Re-audited Saturday, August 15, 2026 against the current codebase. `/guardrails` is a real operator surface with custom rule CRUD, built-in filter activation, template-driven creation, single and batch test flows, saved regression cases, partner guardrail CRUD and health checks, stats and event review, false-positive feedback, alert evaluation and acknowledgement, bulk status changes, and the dedicated `/guardrails/violations` log. Backend, UI, docs, Postman, scripts, and examples are all present; the remaining weakness is cross-feature cohesion in request-analysis and broader runtime posture storytelling rather than missing guardrail functionality. External-rubric N/A review note: guardrails usually have meaningful relationships to FinOps thresholds, onboarding posture, observability evidence, governance, and evaluation loops, so multiple current `N/A` cells should be revisited. |
| Response cache | `/response-cache` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Model gateway` route settings and cache analytics. | P2 | `OK` | `5.1`, `5.2` | Re-audited Thursday, August 21, 2026. WU-002 closed all FinOps cohesion gaps: GET /analytics/budget-performance-posture/{budget_id} and GET /analytics/billing-period-performance-posture surface cache hit rates and estimated savings. Budget detail shows Performance Economics with cache cards. Billing period detail shows cache economics. Gateway cache section links to Budgets, Billing Periods, Chargeback, and Cost & Savings. Docs updated for caching.mdx. Postman and example script added. |
| Rate limits | `/rate-limits` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Budgets`, `Budget tiers`, and `Model gateway` controls. | P2 | `OK` | `4.9`, `6.4`, `6.5` | Re-audited Thursday, August 21, 2026. WU-002 closed all FinOps cohesion gaps: GET /analytics/budget-performance-posture/{budget_id} and GET /analytics/billing-period-performance-posture surface rate-limited route containment. Budget detail shows Performance Economics with throttle containment cards. Billing period detail shows throttle economics. Gateway rate-limits section links to Budgets, Billing Periods, and Chargeback. Budget overrides accessible from budget detail cross-links. Docs updated for runtime-controls.mdx. Postman and example script added. |
