# FinOps — GAP Matrix

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
| Budget tiers | `/budget-tiers` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Model gateway` quota controls and keep only as a compatibility redirect. | P5 | `PENDING` | `6.5` | Bundle context: supports Bundle A indirectly but should remain collapsed under Gateway rather than reopened as a standalone FinOps product. Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/budget-tiers` page now exists only as a compatibility redirect into the Gateway quota-tiers section. Backend CRUD, tier assignment, and compatibility API coverage remain intact, but the primary UI ownership has moved to `/gateway#gateway-quota-tiers`. |
| Budgets | `/budgets` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate as the parent FinOps control. | P5 | `PENDING` | `6.4` | Bundle A - Budget Control Plane. As of Friday, August 14, 2026, the budgets surface now has a real backend/UI lifecycle: create, list, get, update, deactivate, embedded notifications, and an integrated overrides workflow inside `/budgets`. The second pass also added access-group, API-key, and provider-profile-aware budget scope support plus richer related-scope labels in the UI. It is still not complete because the matrix gaps around broader FinOps/Observe/Gateway cross-links, richer projection/coverage views, and stronger runtime ownership beyond the current request context remain open. |
| Budget detail | `/budgets/{id}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Budgets` as breach/history detail, not a separate feature. | P5 | `PENDING` | `6.4` | Bundle A - Budget Control Plane. As of Friday, August 14, 2026, `/budgets/{id}` is now a true detail page with edit-in-place policy controls, breach history, override management, richer scope selection, and related-scope context instead of acting as breach history only. It still needs the fuller cohesion pass described in the matrix and blueprint, such as stronger cross-links into access ownership, provider/routing context, approvals evidence history, and future projection/coverage views. |
| Budget overrides | `/budget-overrides` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Budgets` as advanced override workflow. | P5 | `PENDING` | `6.6` | Bundle A - Budget Control Plane. As of Friday, August 14, 2026, the standalone overrides page is now only a compatibility redirect into `/budgets?tab=overrides`, and the main budgets experience owns create/list/revoke override workflows directly. The second pass also made overrides approval-aware: operators can now request approval before activation, pending overrides stay visible in the budget lifecycle, and approval-linked overrides can be activated or denied through the existing approvals system. Remaining gaps are still real: override lifecycle is not full CRUD, approval UX is still linked rather than deeply embedded, and the evidence/history model still needs a deeper polish pass. |
| Model budgets | `/model-budgets` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Model gateway` or `API keys` advanced quota settings and keep only as a compatibility redirect. | P5 | `PENDING` | `6.7` | Bundle context: supports Bundle A indirectly but should stay collapsed into Gateway or API key quota controls. Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/model-budgets` page now exists only as a compatibility redirect into the Gateway model-quotas section. Backend lifecycle now includes create/list/update/delete, and the primary UI ownership has moved to `/gateway#gateway-model-quotas` so operators no longer need to paste API-key UUIDs into a separate page. |
| Billing periods | `/billing` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate as the parent billing area. | P5 | `PENDING` | `6.9` | Bundle B - Billing and Reconciliation. Completed on Friday, August 14, 2026. `/billing` now acts as the real billing operations shell: summary, periods, and shared-cost policies live together; backend period create/list/get/close/export plus shared-cost policy CRUD are surfaced cleanly in the UI; and docs, Postman, manual lab, smoke script, and example coverage now reflect the shipped workflow. |
| Billing period detail | `/billing/{period_id}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep as billing detail. | P5 | `PENDING` | `6.9` | Bundle B - Billing and Reconciliation. Completed on Friday, August 14, 2026. The detail page is now a true period workspace with summary, reconciliation, breakdown, adjustments, and exports tabs. The missing router reconciliation contract is now real, billing adjustments are manageable from the detail UI with create/edit/delete while periods are open, and the surrounding docs/Postman/lab/example surfaces match the updated operator flow. |
| Chargeback | `/chargeback` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate, but align around workspaces/access groups/workflows. | P5 | `PENDING` | `6.3`, `6.8` | Bundle C - Attribution and Allocation. Completed on Friday, August 14, 2026 for core backend/UI/support-surface delivery: rule CRUD now includes update/edit, the report and export endpoints are real, docs/Postman/lab/smoke/example coverage is aligned, and the active dimension model stays on modern workspace/workflow/application/user/provider primitives. It remains `IN PROGRESS` at the cohesion layer because deeper access-group/API-key-native attribution and broader confidence/evidence views are still future Bundle C deepening work. |
| Ledger | `/ledger` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Platform settings -> Compliance`; keep `/ledger` only as a compatibility redirect, not a separate owner. | P5 | `PENDING` | `6.10` | Bundle D - Compliance Closure. Completed on Friday, August 14, 2026. The real operator home now lives under Platform Settings -> Compliance, where closure readiness, evidence-chain status, snapshot generation, verification, and links into Billing, Chargeback, Audit, and backup evidence are all visible together. `/ledger` remains a compatibility route, while backend `closure-summary`, docs, Postman, smoke coverage, manual lab, and the example now match that ownership model. |
