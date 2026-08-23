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
| Model gateway | `/gateway` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Absorb `Response cache` and `Rate limits` here rather than separate top-level items. | P2 | `RE-AUDIT REQUIRED` | `4.1`, `4.3`, `4.4`, `4.5`, `4.7`, `4.8`, `4.10`, `5.5`, `5.7` | Re-audited Friday, August 22, 2026. WU-014 added GET /analytics/gateway-control-plane-posture (org, observe, governance context) and a Control Plane Bridge card on /gateway with drill-through to Org Profile, Onboarding, Users, Access Groups, Workspace Dashboard, Outcomes & ROI, Analytics Users, Analytics User Detail, Approvals, Audit Log, Governance Pack, All Organizations, and Platform Settings. All 13 WU-014 target cells were already at STRONG from prior WUs; this WU added the consolidated posture surface and missing cross-links. Docs, Postman, and example updated. |
| Guardrails | `/guardrails` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate. | P2 | `RE-AUDIT REQUIRED` | `7.4` | Re-audited Friday, August 22, 2026. WU-015 closed 4 FinOps cohesion cells (Budgets, Budget detail, Billing periods, Chargeback all P→S). GET /analytics/guardrails-finops-posture returns enforcement context and FinOps summary. Guardrails page shows FinOps Posture card with drill-through to Budgets, Budget Detail, Budget Notifications, Billing Periods, Chargeback, Cost & Savings, and Ledger. Top-level cross-links expanded. 15 of 19 WU-015 target cells were already STRONG from prior WUs. |
| Response cache | `/response-cache` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Model gateway` route settings and cache analytics. | P2 | `OK` | `5.1`, `5.2` | Re-audited Friday, August 22, 2026. WU-016 added GET /analytics/response-cache-economics-posture returning cache profiles, FinOps context (budgets, overrides, notifications, billing periods, ledger snapshots), governance context (audit events), and org context (users). Cache Economics & Evidence card on /gateway with 4 data tiles and 16 cross-links. Closed 15 cohesion cells: Onboarding P→S, 5 observe cells N/A→P, Governance pack P→S, 3 FinOps cells N/A→P, Playground/Workflows list/Workflow detail P→S. Docs, Postman, and example updated. |
| Rate limits | `/rate-limits` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Budgets`, `Budget tiers`, and `Model gateway` controls. | P2 | `OK` | `4.9`, `6.4`, `6.5` | Re-audited Friday, August 22, 2026. WU-017 added GET /analytics/rate-limit-scope-posture returning throttle context (routes with RPM, pass-through, routing policies), scope context (access groups, monitoring alerts), and FinOps context (budgets, notifications, chargeback rules, ledger snapshots). Rate Limit Scope & Explainability card on /gateway with 4 data tiles and 14 cross-links. Closed 15 cohesion cells: 4 observe cells N/A→P, Governance pack N/A→P, 3 FinOps cells N/A→P, Evaluation studio/Experiments P→S, Optimization opportunities/simulator P→S. Docs, Postman, and example updated. |
