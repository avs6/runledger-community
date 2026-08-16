# Platform & Utility — GAP Matrix

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

## Platform Features

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| All organizations | `/organizations` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | Keep separate. | P7 | `RE-AUDIT REQUIRED` | `1.2`, `1.7` | Complete as a managed entity: full CRUD (POST/GET/PUT/DELETE /org/tenants) with require_platform_admin auth. UI has table with search, create modal (admin_email/password/skip_verification), edit, delete with confirmation, status badges (active/suspended/archived), workspace/member counts. Docs at administration/organizations.mdx. Postman has 4 requests in the organizations folder. Scripts cover org lifecycle but there is still no dedicated standalone example (PARTIAL). Cohesion stays PARTIAL because the platform lifecycle surface links strongly to org/workspace management but only indirectly to FinOps and Observe. External-rubric N/A review note: a platform org-lifecycle surface usually has meaningful ties to budgets, governance, runtime posture, and observability scope, so several current `N/A` cohesion cells should be revisited. |
| Platform settings | `/settings` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Make this the single home for `Ledger`, `Retention`, `Backup`, and ops/compliance surfaces. | P7 | `RE-AUDIT REQUIRED` | `1.7`, `7.7`, `9.3`, `9.4`, `9.5`, `9.11`, `9.12`, `9.13`, `9.14` | Umbrella console with 5 tabs: Compliance (ledger closures/snapshots/verify), Data Retention (capture-policy scopes/preview/PII test), Email & SMTP (preferences/status/test/history/log), Storage (ops status/feature-flags/policy-evaluation/queues/storage), Backup & Restore (config/run/drill/snapshots/history/test). Backend has broad coverage across the settings router and Postman coverage is extensive. Docs still live mostly as separate sub-area pages rather than one unified `/settings` guide (PARTIAL). Scripts and examples cover important flows but not the full umbrella surface (PARTIAL). Complete remains PARTIAL because this is still a collection of strong controls rather than one fully converged managed entity. External-rubric N/A review note: a platform settings console is structurally cross-cutting and should rarely be fully non-applicable to runtime, governance, billing, or observability relationships. |

---

## Additional Admin / Utility Routes

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Plugins | `/plugins` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `MISSING` | `MISSING` | `PARTIAL` | `PARTIAL` | Collapse into `Onboarding`; do not keep a redirect-only top-level route. | P1 | `RE-AUDIT REQUIRED` | `8.6` | Hybrid surface: backend has full CRUD (create/list/get/update/deactivate) plus execution log at `/plugins`, actively used by MCP tool governance. The route itself still redirects to `/onboarding?section=connections`, so the product-owned UI remains collapsed. Docs only mention plugins indirectly, Postman still has no plugin requests, and there are no plugin-specific scripts or examples. Overall this remains a partial utility surface rather than a finished first-class page. External-rubric N/A review note: even when collapsed in the UI, plugin/app connection surfaces usually affect setup, governance, runtime capabilities, and observability, so current `N/A` usage should be re-audited. |
