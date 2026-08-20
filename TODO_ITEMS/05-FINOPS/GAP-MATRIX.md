# FinOps — GAP Matrix

Last updated: 2026-08-16

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
| Budgets | `/budgets` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate as the parent FinOps control. | P5 | `RE-AUDITED: PARTIAL` | `6.4` | Re-audited Sunday, August 16, 2026. `/budgets` remains a real spend-control plane and now explicitly teaches the shipped scope model, including access groups, API keys, and provider profiles. Access-group scope is not just validated at create time anymore; the list flow, UI drill-through, and supporting docs/Postman/example surfaces all reflect it. The remaining weakness is broader cohesion rather than missing scope support. |
| Budget detail | `/budgets/{id}` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `PARTIAL` | Collapse into `Budgets` as breach/history detail, not a separate feature. | P5 | `RE-AUDIT REQUIRED` | `6.4` | Re-audited Saturday, August 15, 2026. The detail route is a real sub-surface of Budgets rather than a fake placeholder: it loads the budget record, breach history, and overrides together, supports edit-in-place policy changes, and links operators back to related access-group/API-key/provider-profile ownership when relevant. It remains partial because the docs do not explicitly teach the detail workflow, and the broader Bundle A cohesion work around deeper approvals and investigation handoff is still not fully closed. External-rubric N/A review note: a budget-detail drilldown should rarely be structurally unrelated to scope, runtime, evidence, or optimization surfaces, so current `N/A` usage looks too strong. |
| Budget overrides | `/budget-overrides` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | Collapse into `Budgets` as advanced override workflow. | P5 | `RE-AUDIT REQUIRED` | `6.6` | Re-audited Saturday, August 15, 2026 as a deliberate collapse. `/budget-overrides` now correctly redirects into `/budgets?tab=overrides`, and the integrated budgets experience owns create/list/revoke flows with optional approval linkage. The lifecycle is still only partial, though, because overrides are not full CRUD, approval handling is linked rather than deeply embedded, and the docs/examples still describe the capability more broadly than the currently shipped workflow deserves. External-rubric N/A review note: override mechanisms are normally cross-cutting by design and should usually connect to approval, runtime, observability, and governance flows rather than being marked broadly `N/A`. |
| Model budgets | `/model-budgets` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | Collapse into `Model gateway` or `API keys` advanced quota settings and keep only as a compatibility redirect. | P5 | `RE-AUDITED: OK` | `6.7` | Re-audited Saturday, August 15, 2026 as a deliberate collapse. The standalone page is no longer the owner, but the redirect into Gateway model quotas is real, the backend lifecycle exists, and the docs/supporting scenarios still preserve the feature story under runtime quota ownership. |
| Billing periods | `/billing` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate as the parent billing area. | P5 | `RE-AUDITED: OK` | `6.9` | Re-audited Sunday, August 16, 2026. `/billing` remains the real Bundle B operations shell and now includes genuine access-group-scoped and API-key-scoped period list flows. The backend filters periods by attributable owner traffic, the UI preserves that scope across detail navigation, and the docs/Postman coverage now reflect the entry paths. |
| Billing period detail | `/billing/{period_id}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep as billing detail. | P5 | `RE-AUDITED: OK` | `6.9` | Re-audited Sunday, August 16, 2026. The detail page remains a true period workspace and now preserves both access-group scope and API-key scope across reconciliation, breakdown, and export flows. That closes the previous gap where identity-scope-aware billing review existed conceptually but not as a real operator path. |
| Chargeback | `/chargeback` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate, but align around workspaces/access groups/workflows. | P5 | `RE-AUDITED: PARTIAL` | `6.3`, `6.8` | Re-audited Sunday, August 16, 2026. `/chargeback` now supports both the `access_group` and `api_key` dimensions as real shipped attribution paths rather than only future-facing cohesion language. The backend, UI, docs, Postman, smoke script, and example all reflect that support. It remains partial because richer evidence/confidence handling is still a deeper follow-on area. |
| Ledger | `/ledger` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Platform settings -> Compliance`; keep `/ledger` only as a compatibility redirect, not a separate owner. | P5 | `RE-AUDITED: OK` | `6.10` | Re-audited Saturday, August 15, 2026. Ledger is no longer a standalone workspace FinOps owner, and that collapse is now correctly implemented: `/ledger` is a compatibility redirect into `Platform Settings -> Compliance`, the docs teach the compliance-closure ownership model, and the shipped backend/supporting surfaces around closure summary, snapshots, verification, evidence links, Postman, smoke coverage, manual lab, and example all align to that platform-owned workflow. |
