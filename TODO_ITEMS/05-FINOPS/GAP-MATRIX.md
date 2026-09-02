# FinOps — GAP Matrix

Last updated: 2026-09-01

## Legend

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet audited |
| `OK` | Verified working |
| `PARTIAL` | Present but partial, buggy, or unclear |
| `MISSING` | Missing, broken, or disconnected |
| `LEGACY` | Legacy/transitional surface; do not expand |

---

## Recommended User-Flow Implementation Bundles

1. Budget Control Plane
   Includes `Budgets`, `Budget detail`, and `Budget overrides`.
   This is the primary spend-control layer and should be fixed first so runtime caps, breach history, and temporary override workflows become one cohesive admin experience.
2. Billing and Reconciliation
   Includes `Billing periods` and `Billing period detail`.
   This is the accounting layer and should follow the budget pass so period close/export/adjustment flows operate on a cleaner spend-control foundation.
3. Attribution and Allocation
   Includes `Chargeback`.
   This should align to workspaces, access groups, workflows, and feature tags rather than legacy team or project concepts.
4. Compliance Closure
   Includes `Ledger`.
   This is best treated as a downstream compliance and verification surface under Platform Settings rather than a first-class FinOps workspace page.

## Recommended Execution Order

1. `Bundle A` - Budget Control Plane
2. `Bundle B` - Billing and Reconciliation
3. `Bundle C` - Attribution and Allocation
4. `Bundle D` - Compliance Closure

---

## Feature Rows

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Budget tiers | `/budget-tiers` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Model gateway` quota controls and keep only as a compatibility redirect. | P5 | `RE-AUDITED: OK` | `6.5` | Re-audited Saturday, August 15, 2026 as a deliberate collapse. The standalone route is no longer a primary FinOps owner, but the compatibility redirect, backend CRUD/assignment support, Postman coverage, docs, and scenario story are all still intact through Gateway quota-tier ownership. |
| Budgets | `/budgets` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate as the parent FinOps control. | P5 | `RE-AUDITED: PARTIAL` | `6.4` | Re-audited 2026-09-01 (WU-014). WU-014 added Budget Scope Governance Posture endpoint and emerald card to Budgets page with identity scope (users, API keys, access groups, hub models), runtime context, governance context, and spend. Budgets × Users P→S. Remaining partial: Plugins, WS dashboard, Sessions, Billing summary. Prior: WU-009/010 added Observe and Build posture. |
| Budget detail | `/budgets/{id}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Collapse into `Budgets` as breach/history detail, not a separate feature. | P5 | `RE-AUDITED: PARTIAL` | `6.4` | Re-audited 2026-09-01 (WU-015). WU-015 added Budget Detail Drillback Posture endpoint (`GET /analytics/budget-detail-drillback-posture`) and emerald Budget Detail Drillback Context card with scope owners (users, access groups, API keys), runtime (caches, rate-limited routes), evidence (runs, requests, audit events), workflow (definitions, runs), and spend. Budget detail × Users P→S. Most other WU-015 target cells already STRONG from prior WUs. Remaining partial: Optimization opportunities, Optimization simulator, Workflow run detail, Runbooks, Tool policies, Onboarding, Billing summary, Monitoring. |
| Budget overrides | `/budget-overrides` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | Collapse into `Budgets` as advanced override workflow. | P5 | `RE-AUDITED: PARTIAL` | `6.6` | WU-016 (2026-09-01): Budget Override Exception Posture endpoint (`GET /analytics/budget-override-exception-posture`) and emerald Override Exception Context card added to Budget Detail with override lifecycle (total, active, expired, limit USD), approval workflow (pending, approved, denied), runtime context (routes, rate-limited), monitoring (alert rules, audit events), and spend. All 10 WU-016 target cells already STRONG from prior WUs — no cell state changes. Prior: WU-004 added governance posture. Override lifecycle is still partial (not full CRUD), but exception-lifecycle and governance integration are now complete. |
| Model budgets | `/model-budgets` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | Collapse into `Model gateway` or `API keys` advanced quota settings and keep only as a compatibility redirect. | P5 | `RE-AUDITED: OK` | `6.7` | Re-audited Saturday, August 15, 2026 as a deliberate collapse. The standalone page is no longer the owner, but the redirect into Gateway model quotas is real, the backend lifecycle exists, and the docs/supporting scenarios still preserve the feature story under runtime quota ownership. |
| Billing periods | `/billing` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate as the parent billing area. | P5 | `RE-AUDITED: PARTIAL` | `6.9` | WU-017 (2026-09-01): Billing Reconciliation Posture endpoint (`GET /analytics/billing-reconciliation-posture`) and emerald Billing Reconciliation Context card added to Billing page with identity context (users, API keys, access groups), provider context (active providers, cache configs, cache savings, models), optimization context (billing periods, alert rules, cache savings), evidence context (audit events, alert rules), and spend. 2 cells P→S: Billing periods × Users, Billing periods × Optimization opportunities. Prior: WU-011 added Billing Cross-Feature Posture, WU-007 added Billing Org Scope Posture. Remaining partial: Observe drill-through, Build surfaces. |
| Billing period detail | `/billing/{period_id}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep as billing detail. | P5 | `RE-AUDITED: PARTIAL` | `6.9` | WU-018 (2026-09-01): Billing Detail Evidence Posture endpoint (`GET /analytics/billing-detail-evidence-posture`) and emerald Billing Detail Evidence Context card added to Billing Period Detail with identity context (users, API keys, access groups), gateway context (routes, models), observe context (sessions, requests), build context (replay experiments), and spend. 3 cells P→S: Billing period detail × Users, × Sessions list, × Replay lab. Prior: WU-011 added Billing Cross-Feature Posture, WU-007 added Billing Org Scope Posture. Remaining partial: Observe drill-through (WS dashboard, Session detail, Billing summary, Analytics users, User detail, Engineering), Build surfaces. |
| Chargeback | `/chargeback` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate, but align around workspaces/access groups/workflows. | P5 | `RE-AUDITED: PARTIAL` | `6.3`, `6.8` | WU-019 (2026-09-01): Chargeback Attribution Posture endpoint (`GET /analytics/chargeback-attribution-posture`) and emerald Chargeback Attribution Context card added to Chargeback page with identity context (users, API keys, access groups), runtime context (cache configs, cache savings, chargeback rules), monitoring context (alert rules, audit events, tags), optimization context (chargeback rules, cache savings), and spend. 3 cells P→S: Chargeback × Users, × Monitoring, × Optimization opportunities. Prior: WU-012 added Cross-Feature Posture (15 cells P→S), WU-008 added FinOps Internal Posture. Remaining partial: Observe drill-through, Build surfaces, Plugins. |
| Ledger | `/ledger` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Platform settings -> Compliance`; keep `/ledger` only as a compatibility redirect, not a separate owner. | P5 | `RE-AUDITED: OK` | `6.10` | Re-audited 2026-09-01 (WU-013). WU-013 added Ledger Cross-Feature Posture endpoint and emerald Ledger × Cross-Feature Context card to Platform Settings (Compliance tab) with org, observe, safety, platform, and ledger context. Ledger × All organizations P→S, Ledger × Billing summary P→S, Ledger × Tags P→S. Prior: compliance-closure workflow under Platform Settings. |
