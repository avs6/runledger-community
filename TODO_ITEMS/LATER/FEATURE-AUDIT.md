# RunLedger Feature Audit

Last updated: Friday, August 14, 2026

## Purpose

This audit file is based on the actual feature surfaces currently present in the product:

- sidebar navigation in `apps/web/components/layout/Sidebar.tsx`
- top-level dashboard routes in `apps/web/app/(dashboard)`
- backend routers in `apps/api/runledger_api/routers`

This file is the primary feature-audit source of truth for the shipped product surface.

It is intended to complement, not replace, the broader delivery-surface matrix in [`TODO_ITEMS/DELIVERY-AUDIT.md`](/C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/DELIVERY-AUDIT.md).

Use this file when auditing the real shipped product surface page by page.

When we intentionally introduce roadmap items before the code exists, keep them in a separate planned-architecture section so the shipped-surface audit stays honest.

## Legend

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet audited |
| `OK` | Verified working |
| `PARTIAL` | Present but partial, buggy, or unclear |
| `MISSING` | Missing, broken, or disconnected |
| `LEGACY` | Legacy/transitional surface; audit it, but do not expand it |

## Audit Columns

| Column | What to verify |
|--------|----------------|
| `Backend` | API/router exists, auth works, CRUD and data shape are real |
| `UI` | Page renders, controls load, statuses display correctly |
| `Actions` | Buttons, forms, toggles, mutations, drill-downs, exports |
| `Docs` | Relevant docs accurately describe the current behavior |
| `Postman` | Requests exist and reflect the current route/API shape |
| `Scripts/Examples` | A realistic scenario, example, or script exercises the feature |
| `Complete` | Mark `OK` only when backend CRUD and UI CRUD are present where expected and the supporting surfaces are complete |
| `Cohesion` | Scope and product fit: does the feature align cleanly with workspace, org, or platform surfaces around it |
| `Notes` | Bugs, ambiguity, legacy status, missing states, cleanup items |
| `Merge / Collapse` | Flag duplicate, overlapping, legacy, or redirect-only surfaces that should be merged, collapsed, retired, or absorbed elsewhere |
| `Fix Order` | Recommended remediation sequence so foundation scopes and runtime paths are fixed before dependent feature surfaces |
| `Fix Status` | Track the current matrix-driven remediation state. After the matrix reset, use this column only after a fresh re-audit against both the Feature Gap Matrix and the Feature Cohesion Matrix. |
| `Delivery Audit Crosswalk` | Bridge this user-facing feature to the broader delivery-surface rows in `TODO_ITEMS/DELIVERY-AUDIT.md` |

---
## FEATURE GAP MATRIX

Reset note:

- The `Fix Status` column in this matrix has been reset to `RE-AUDIT REQUIRED`.
- Earlier fix-status values were recorded before the Feature Gap Matrix and Feature Cohesion Matrix became the primary audit workflow.
- Do not trust older completion momentum from this column without a new matrix-driven audit pass.
- Before any feature work resumes, re-audit the feature row, its gap state, and its cohesion relationships, then update `Fix Status` from there.

## 1. Organization & Access

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Organization profile | `/organization` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Primary org console now absorbs `Org settings`; keep this as the single org-admin entry point. | P1 | `RE-AUDIT REQUIRED` | `1.2`, `1.7` | Complete as an org console: org metadata update, members/workspaces CRUD, org-owned destinations, and org notification settings are aligned across backend, UI, docs, Postman, and script/example coverage. Org creation/deletion intentionally remains in platform lifecycle surfaces at `/organizations`. |
| Org settings | `/org-settings` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Legacy redirect only; collapsed into `/organization` and should not expand separately. | P1 | `RE-AUDIT REQUIRED` | `1.7`, `9.1`, `9.2` | The old route now serves only as a compatibility redirect into the organization console tabs and is no longer a parallel feature surface. |
| Onboarding | `/onboarding` | `PARTIAL` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `NO` | `OK` | Primary setup/discovery surface for Claude, Codex, MCP, telemetry, and existing-stack connection guides. | P1 | `RE-AUDIT REQUIRED` | `1.8`, `2.3`, `2.6`, `8.6`, `9.14` | This is now the intended setup home for external-tool connectivity and guided adoption. It is strong as a product guide, but completion should still be judged as setup coverage rather than CRUD because it is not a managed entity surface. |
| Users | `/users` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P1 | `RE-AUDIT REQUIRED` | `1.4`, `1.6` | Org user management is now aligned end to end: org admins and org managers can operate the page, docs reflect the role model, and the shared access-foundation smoke coverage exercises user creation plus workspace/access-group assignment. |
| Workspaces | `/workspace` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse all remaining `teams` language into this feature; this is the canonical replacement. | P1 | `RE-AUDIT REQUIRED` | `1.3` | Backend and UI support create/list/rename/delete plus membership management; this is the canonical team boundary and aligns with the repo’s workspace-first model. |
| Access groups | `/access-groups` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P1 | `RE-AUDIT REQUIRED` | `7.15`, `1.6` | Full managed-entity story is present with create/update/delete, member assignment, docs, Postman, and end-to-end script/example coverage; it also ties into budgets and guardrail profiles rather than inventing a parallel concept. |
| API keys | `/api-keys` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Absorb `Model budgets` into this area if key-level controls remain. | P1 | `RE-AUDIT REQUIRED` | `1.5`, `6.7` | API key management is now aligned end to end with create/list/detail/update/revoke/history flows across backend and UI, plus docs, Postman, and access-foundation smoke coverage. Gateway now also embeds API-key quota-tier assignment and per-model quota controls, so `/api-keys` no longer needs to be the only place those relationships are discoverable. |
| Integrations | `/integrations` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapsed into `Onboarding`; keep only as a compatibility redirect while deeper operational surfaces live in Telemetry, MCP, Organization Console, and Platform Settings. | P1 | `RE-AUDIT REQUIRED` | `1.8`, `2.3`, `2.4`, `2.5`, `8.6`, `9.6`, `9.7`, `9.8` | This route should no longer own setup UX. Claude, Codex, and similar external-tool guides move into Onboarding, OTLP deep operations move into Telemetry, and org/platform-owned config stays in the appropriate settings consoles. |
| Telemetry | `/monitoring/telemetry` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `NO` | `OK` | Keep `/otlp` only as a compatibility redirect into this observability surface. | P1 | `RE-AUDIT REQUIRED` | `2.3`, `2.8`, `9.9`, `9.10` | OTLP ingestion is now correctly owned by Observability. The page provides ingest stats, batch pagination, batch drill-in, and setup guidance, while `/otlp` redirects here for compatibility. This remains an observability/admin surface rather than a CRUD entity. |
| MCP registry | `/mcp-registry` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Primary MCP area with setup + registry tabs. | P1 | `RE-AUDIT REQUIRED` | `2.6`, `8.5` | The setup wizard from `/mcp` now lives here, and the page now supports the full MCP server lifecycle: create, detail review, edit, deactivate, re-activate, permission policies, tool testing, and call history. Docs, README, Postman, manual labs, automated scripts, and an example are now aligned with the consolidated surface. |
| AI hub | `/ai-hub` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep as the workspace model catalog, but cross-link it tightly with `Provider profiles` and `Model usage`. | P1 | `RE-AUDIT REQUIRED` | `8.8`, `10.1`, `10.2` | Backend and UI now both have real CRUD, provider sync, access requests, and deprecation controls. Docs, README, Postman, manual labs, automated scripts, and a runnable example are now aligned with the feature. |
| Projects | `/projects` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | Retired from Org & Access; keep only as a compatibility redirect into `Workspaces` while deeper runtime/storage cleanup can continue separately. | P1 | `RE-AUDIT REQUIRED` | `8.7` | The active page has been removed from the user workflow, the route redirects to `/workspace`, the frontend helper/types have been removed, and the public backend router is no longer mounted. Remaining model/schema files are now internal legacy cleanup only. |
| Team models | `/team-models` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | Retired from Org & Access; keep only as a compatibility redirect into `Provider profiles` while model-approval semantics are re-homed elsewhere. | P1 | `RE-AUDIT REQUIRED` | `4.2`, `8.8` | The active page has been removed from the user workflow, the route redirects to `/provider-profiles`, the frontend helper/types have been removed, and the public backend router is no longer mounted. Remaining model/schema files are now internal legacy cleanup only. |

---

## 2. Gateway & Routing

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Provider profiles | `/provider-profiles` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P2 | `RE-AUDIT REQUIRED` | `4.2`, `6.2` | Verified against the current codebase and UI: backend supports list/create/update/delete plus import, example download, reprice flows, and now provider-profile budget counts; the dashboard exposes real admin actions with filters, workspace/global scope handling, and direct scoped budget links; docs, Postman, examples, and simulation/manual lab coverage are all present. Bundle A started a deeper cohesion pass on Friday, August 14, 2026 by tightening the provider-profile to budget-policy bridge. |
| Model gateway | `/gateway` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Absorb `Response cache` and `Rate limits` here rather than separate top-level items. | P2 | `RE-AUDIT REQUIRED` | `4.1`, `4.3`, `4.4`, `4.5`, `4.7`, `4.8`, `4.10`, `5.5`, `5.7` | The gateway control plane now clears the completion bar: routes, routing groups, routing policies, pass-through endpoints, response-cache profiles, runtime rate-limit overview, API-key quota tiers, and per-model quota controls all have real backend/UI ownership on the Gateway surface, while benchmarking, routing log, flywheel, docs, Postman, examples, and scripts remain aligned with the Rust data-plane split. Bundle A started a deeper cohesion pass on Friday, August 14, 2026 by clarifying Gateway-to-Budgets ownership and linking operators directly into the spend-policy surface. |
| Guardrails | `/guardrails` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P2 | `RE-AUDIT REQUIRED` | `7.4` | Completed on Friday, August 14, 2026. The `/guardrails` page now acts as a cohesive operator surface instead of a partial dashboard: it covers custom rule CRUD, built-in content filter management, template-driven rule creation, test playground execution, test-case creation/deletion, regression runs with visible reports, partner guardrail create/edit/delete/health flows, event false-positive feedback, alert evaluate/acknowledge actions, bulk enable/disable for selected rules, and a dedicated filterable/paginated violations log at `/guardrails/violations`. Backend, UI, docs, Postman, scripts, and examples are now aligned closely enough to treat Guardrails as feature-complete in this phase while keeping the runtime enforcement path Python-based as intended. |
| Response cache | `/response-cache` | `OK` | `LEGACY` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | Collapse into `Model gateway` route settings and cache analytics. | P2 | `RE-AUDIT REQUIRED` | `5.1`, `5.2` | Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/response-cache` page is no longer treated as a first-class product area and now exists only as a compatibility redirect into `/gateway`. The collapsed ownership is now complete rather than redirect-only: backend cache profile lifecycle includes create/list/get/update/delete plus stats, and the Gateway UI now exposes cache-profile create/edit/delete and detail drill-in alongside the existing route-level `semantic_cache_enabled` controls and cache analytics. |
| Rate limits | `/rate-limits` | `OK` | `LEGACY` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | Collapse into `Budgets`, `Budget tiers`, and `Model gateway` controls. | P2 | `RE-AUDIT REQUIRED` | `4.9`, `6.4`, `6.5` | Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/rate-limits` page now exists only as a compatibility redirect into `/gateway`, and the real ownership has been moved back into the primary features: Gateway now exposes a backend-driven runtime rate-limit overview for ingest/analytics/management/system tiers plus route/pass-through throttles and embedded API-key/model quota management, while Budget Tiers and Model Budgets remain the compatibility home for those same quota controls. |

---

## 3. Observe

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Workspace dashboard | `/dashboard` | `OK` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Merged into `Analytics overview` as a compatibility redirect; do not keep a separate first-class dashboard shell. | P3 | `RE-AUDIT REQUIRED` | `3.1` | Completed on Friday, August 14, 2026. `/dashboard` now exists only as a compatibility redirect into `/analytics?scope=workspace&view=overview`, and the overview docs/supporting coverage now reflect that ownership clearly enough that this no longer needs to remain open as a separate workspace dashboard feature. |
| Analytics overview | `/analytics` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Primary scoped overview shell for workspace, org, and platform; keep detailed workspace charts under `Analytics Breakdown` instead of parallel dashboard homes. | P3 | `RE-AUDIT REQUIRED` | `3.8` | Completed on Friday, August 14, 2026. `/analytics` is now the cohesive Observe entry point: scope switching, overview metrics, top intents/models, request-analysis drilldowns, economics handoff, and compatibility redirects from the old dashboard homes are all aligned across code, docs, and support material. |
| Runs list | `/runs` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.2` | Completed on Friday, August 14, 2026. The list has real backend filtering, cursor pagination, export, and strong drill-in behavior, and it now sits cleanly inside the request-analysis workflow with direct bridges into Request Flow and Request Explorer. This is an investigative observability surface rather than a CRUD entity, and it now clears the correct completion bar for that class of feature. |
| Run detail | `/runs/{run_id}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.3` | Completed on Friday, August 14, 2026. The page provides the full execution DAG, payload and provider-call detail, tool/span inspection, and the backend-backed cancel action for running runs. Supporting docs, Postman, and scenario coverage are sufficient for a read/investigation surface, so this no longer needs to remain partially open. |
| Sessions list | `/sessions` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.4` | Completed on Friday, August 14, 2026. The list now uses backend-backed search, filters, offset pagination, and CSV export, and it fits cleanly into the Observe workflow as the conversation-level complement to Runs and Request Explorer. Completion here is based on investigative-read completeness rather than CRUD because sessions are not a managed entity. |
| Session detail | `/sessions/{session_id}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.5` | Completed on Friday, August 14, 2026. The page gives the intended session drilldown with cost-over-turns, duration, user context, and per-turn run links, and it now sits on top of a stronger list page with better filtering/export behavior. This is a read-only observability detail page by design and is complete on that basis. |
| Request flow | `/request-flow` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Group with `Request flow focus` and `Request explorer` under one request analysis suite. | P3 | `RE-AUDIT REQUIRED` | `3.6` | Completed on Friday, August 14, 2026. This is now the primary request-causality surface over `/runs/flow`: it supports scope/mode pivots, export, drill-in, and explicit bridges into Analytics Overview, Request Explorer, and Focus Mode. The supporting docs, Postman collection, labs, and examples already existed and now match the shipped UI more closely. |
| Request flow focus | `/request-flow/focus` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Request flow` as a mode/state, not a distinct feature line. | P3 | `RE-AUDIT REQUIRED` | `3.6` | Completed on Friday, August 14, 2026 as a deliberate mode-level collapse rather than an independent feature. The route remains useful for demos and dense debugging, but it is now clearly framed as the large-canvas state of Request Flow over the same backend contract and support material. |
| Request explorer | `/request-explorer` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Group with `Request flow`; likely one request analysis area with tabs. | P3 | `RE-AUDIT REQUIRED` | `3.7` | Completed on Friday, August 14, 2026. The page now uses the dedicated `/analytics/request-explorer` contract for list/filter/pagination, preserves the deeper run/graph/outcome/gateway drill-in, and explicitly bridges back to Analytics Overview, Request Flow, Runs, and Sessions. The docs were updated to match the real filter surface and request-level investigation model, so this request-analysis feature is now cohesive end to end. |
| Model usage | `/model-usage` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Group with `Analytics economics` and `Cost and savings`. | P3 | `RE-AUDIT REQUIRED` | `3.12` | Completed on Friday, August 14, 2026. This is now treated as one of the primary deep economics drilldowns rather than a suspicious composite. The page already had strong scope, routing, latency, quality, and model concentration behavior; the follow-on economics overview pass now places it clearly inside the broader user workflow instead of leaving it as a disconnected analytics page. |
| Analytics economics | `/analytics/economics` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep as the economics overview bridge; route users into `Model usage`, `Cost and savings`, and `Billing` instead of treating this as a competing deep drilldown. | P3 | `RE-AUDIT REQUIRED` | `3.9` | Completed on Friday, August 14, 2026. The page is no longer a thin orphan dashboard. It now acts as the economics overview surface: top workflows by cost, version compare, regressions, and annotations stay here, while the page explicitly routes users into Model Usage, Cost & Savings, and Billing for deeper work. Docs now match that overview role. |
| Cost and savings | `/cost-savings` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Group with `Analytics economics`, `Model usage`, and `Billing summary`. | P3 | `RE-AUDIT REQUIRED` | `3.18`, `6.3` | Completed on Friday, August 14, 2026. This remains the primary optimization-economics drilldown for realized savings, business-dimension breakdown, ROI targeting, and budget context. Like other observability-style surfaces, it is composite by design, but its backend inputs, UI actions, docs, Postman coverage, and scenario story now form a cohesive economics feature rather than an unfinished page. |
| Billing summary | `/billing-summary` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapsed into `Billing` as a summary tab/view; keep this route only as a compatibility redirect. | P3 | `RE-AUDIT REQUIRED` | `6.9` | Completed on Friday, August 14, 2026 as a deliberate collapse. The summary experience now lives inside `/billing` with the export controls and rollup chart/table intact, and `/billing-summary` redirects there for compatibility. This removes the parallel billing entry point and keeps finance workflows together. |
| Outcomes and ROI | `/outcomes` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.19` | Completed on Friday, August 14, 2026. The feature is no longer analytics-only: the backend now supports get/update/delete in addition to create/list/ROI endpoints, the UI now includes a managed outcome ledger with create/filter/edit/delete flows alongside the summary, trend, workflow ROI, and quality-correlation analytics, the Postman collection was regenerated from the current OpenAPI spec, and the docs/examples/lab story now match the actual lifecycle. |
| Analytics users | `/analytics/users` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.10` | Completed on Friday, August 14, 2026. The list already had strong behavior for top spenders, cohort tiers, anomaly flags, and segmentation tabs; this pass finished the feature by adding dedicated user-analytics documentation and clearer workflow bridges into Request Explorer and Outcomes & ROI so the page is no longer relying on indirect analytics docs. |
| Analytics user detail | `/analytics/users/{end_user_id}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.10` | Completed on Friday, August 14, 2026. The detail page already delivered the intended per-user charts and breakdowns, and this pass tightened cohesion with explicit pivots into Request Explorer, Request Flow, and Outcomes & ROI while adding dedicated docs coverage and confirming example support. As an investigative observability surface, it is complete without requiring entity CRUD. |
| Engineering | `/engineering` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P3 | `RE-AUDIT REQUIRED` | `3.11` | Completed on Friday, August 14, 2026. This remains a read/investigation surface rather than a CRUD entity, but it now clears the correct completion bar: backend metrics are real, the UI exposes direct drilldowns into Request Explorer, Request Flow, and Model Usage, and the docs/Postman/supporting story match the shipped page. |
| Monitoring | `/monitoring` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep as the operations triage shell; deep setup and configuration stay in Security, Alert Rules, Gateway, and Telemetry. | P3 | `RE-AUDIT REQUIRED` | `3.13` | Completed on Friday, August 14, 2026. Monitoring is now treated as a cohesive triage surface rather than a failed CRUD feature: it aggregates security events, alert firings, gateway request health, and explicit handoff into Telemetry and other operational owners, with the docs now reflecting that role. |
| Quality scores | `/evaluations` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Merged with `Evaluation studio`, `Datasets`, `Experiments`, and `Replay lab` into one evaluation suite. | P3 | `RE-AUDIT REQUIRED` | `3.20`, `7.2`, `7.3` | Completed on Friday, August 14, 2026 as a deliberate collapse. The standalone `/evaluations` route now redirects into the `Scores` tab inside `/evaluation`, so score submission, score summary, and recent score review live inside the evaluation suite instead of remaining a stray observability page. |
| Organization dashboard | `/organization/dashboard` | `OK` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Merged into `Analytics overview` as an org-scoped compatibility redirect. | P3 | `RE-AUDIT REQUIRED` | `1.2`, `3.1` | Completed on Friday, August 14, 2026. `/organization/dashboard` now exists only as a compatibility redirect into `/analytics?scope=org&view=overview`, and the shared overview shell plus refreshed docs/supporting coverage make this an intentionally closed redirect surface rather than an in-progress org dashboard. |
| Global dashboard | `/global-dashboard` | `OK` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Merged into `Analytics overview` as a platform-scoped compatibility redirect. | P3 | `RE-AUDIT REQUIRED` | `1.7`, `3.1` | Completed on Friday, August 14, 2026. `/global-dashboard` now exists only as a compatibility redirect into `/analytics?scope=platform&view=overview`, and the platform-scoped overview ownership is documented cleanly enough that this no longer needs to stay partially open. |

---

## 4. Safety & Governance

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| MCP servers | `/mcp` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Redirect into `MCP registry`; do not keep as a separate management surface. | P4 | `RE-AUDIT REQUIRED` | `2.6`, `8.5` | This route now exists only as a compatibility entry point into `/mcp-registry?tab=setup`, while the combined MCP area is fully consolidated under Org & Access and documented as such. |
| Search tools | `/search-tools` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapsed into `Tool registry` as the search-provider management tab; keep this route only as a compatibility redirect. | P4 | `RE-AUDIT REQUIRED` | `7.12` | Completed on Friday, August 14, 2026 as a deliberate collapse. The standalone page was too thin to justify long-term ownership, so search-provider CRUD and policy pivots now live inside `/tool-registry?tab=search`, while `/search-tools` redirects there for compatibility. |
| Tool registry | `/tool-registry` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Primary registry/admin surface inside the broader tool governance area. | P4 | `RE-AUDIT REQUIRED` | `7.13` | Completed on Friday, August 14, 2026. The page now owns both runtime registry management and collapsed search-provider management with real create/edit/deactivate flows, runtime-enforcement controls, and explicit pivots into tool policies, so this is no longer just a list/upsert stub. |
| Tool policies | `/tool-policies` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Primary policy/governance surface grouped with `Tool registry`; it now also owns simulation and dry-run review. | P4 | `RE-AUDIT REQUIRED` | `7.14` | Completed on Friday, August 14, 2026. Backend policy actions were normalized to match runtime governance, the page now supports create/edit/deactivate flows for managed policy entities, and the simulator plus dry-run review are folded into the same operator surface instead of being split across disconnected pages. |
| Policy dry run | `/policy-dry-run` | `LEGACY` | `LEGACY` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapsed into `Tool policies` as the dry-run/testing tab; keep this route only as a compatibility redirect. | P4 | `RE-AUDIT REQUIRED` | `7.8` | Completed on Friday, August 14, 2026 as a deliberate collapse. The live dry-run workflow now belongs to the Tool Policies surface at `/tool-policies?tab=dry-run`, while `/policy-dry-run` remains only as a compatibility entry point. |
| Approvals | `/approvals` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P4 | `RE-AUDIT REQUIRED` | `7.5` | Completed on Friday, August 14, 2026. This pass closed the main lifecycle gap: the surface now supports real auto-approval policy create/list/update/delete management in both backend and UI, expanded request-type support to match the shipped UX, and enforces matching auto-approval policies directly when approval requests are created so the page is no longer depending on decorative policy management. |
| Data capture | `/data-capture` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P4 | `RE-AUDIT REQUIRED` | `7.10` | Completed on Friday, August 14, 2026. The scoped-override lifecycle is now complete instead of create-only: backend supports list, create or update, and delete for scoped capture policy entries, the UI exposes edit/delete in place, the docs now match the real privacy modes, and support coverage includes refreshed Postman plus governance scenario and example updates. |
| Security | `/security` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P4 | `RE-AUDIT REQUIRED` | `7.16` | Completed on Friday, August 14, 2026. The page now clears the managed-entity bar: workspace security posture, OIDC providers, and IP ACL rules all have real create/edit/delete coverage in the UI over the existing backend contracts, the team-scoped ACL prompt is no longer part of the active workflow, and docs/Postman/scripts/examples have been tightened to match the stronger surface. |
| Alert rules | `/alert-rules` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P4 | `RE-AUDIT REQUIRED` | `7.6` | Completed on Friday, August 14, 2026. Edit-in-place is now closed end to end: backend update accepts the full managed rule shape needed by operators, and the page now supports editing thresholds, metric/operator selection, windows, and email delivery without forcing delete-and-recreate behavior. |
| Audit log | `/audit` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Group with `Governance pack` and compliance evidence, not a separate top-level governance primitive. | P4 | `RE-AUDIT REQUIRED` | `7.9` | Completed on Friday, August 14, 2026 for its actual feature class. This is intentionally a read and investigation surface rather than a CRUD domain, and it now has the right completion shape: filter/export, event-detail drill-in, linked evidence workflow, refreshed documentation context, and regenerated Postman coverage aligned with the current API. |
| Governance pack | `/governance-pack` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Group with `Audit log` and platform compliance surfaces. | P4 | `RE-AUDIT REQUIRED` | `7.9` | Completed on Friday, August 14, 2026. The backend contract and export path are real, the UI now bridges clearly into the other governance evidence owners, and the remaining support gap has been closed with updated docs, regenerated Postman artifacts, and scenario/example coverage so this can be treated as a finished evidence surface rather than a partial placeholder. |
| Tags | `/tags` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate as the taxonomy and auto-tagging owner; only collapse it later if product direction intentionally removes first-class taxonomy management. | P4 | `RE-AUDIT REQUIRED` | `7.11` | Completed on Friday, August 14, 2026. The page now owns the full lifecycle it implied all along: tag create/edit/archive, auto-tagging rule create/edit/delete, hierarchy review, and simulation are all backed by real API contracts, including the missing auto-rule delete route. Docs, regenerated Postman, governance scenario coverage, and a runnable example now match the feature. |

---

## 5. FinOps

Recommended user-flow implementation bundles for FinOps:

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

Recommended execution order:

1. `Bundle A` - Budget Control Plane
2. `Bundle B` - Billing and Reconciliation
3. `Bundle C` - Attribution and Allocation
4. `Bundle D` - Compliance Closure

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Budget tiers | `/budget-tiers` | `OK` | `LEGACY` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Model gateway` quota controls and keep only as a compatibility redirect. | P5 | `RE-AUDIT REQUIRED` | `6.5` | Bundle context: supports Bundle A indirectly but should remain collapsed under Gateway rather than reopened as a standalone FinOps product. Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/budget-tiers` page now exists only as a compatibility redirect into the Gateway quota-tiers section. Backend CRUD, tier assignment, and compatibility API coverage remain intact, but the primary UI ownership has moved to `/gateway#gateway-quota-tiers`. |
| Budgets | `/budgets` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `NO` | `OK` | Keep separate as the parent FinOps control. | P5 | `RE-AUDIT REQUIRED` | `6.4` | Bundle A - Budget Control Plane. As of Friday, August 14, 2026, the budgets surface now has a real backend/UI lifecycle: create, list, get, update, deactivate, embedded notifications, and an integrated overrides workflow inside `/budgets`. The second pass also added access-group, API-key, and provider-profile-aware budget scope support plus richer related-scope labels in the UI. It is still not complete because the matrix gaps around broader FinOps/Observe/Gateway cross-links, richer projection/coverage views, and stronger runtime ownership beyond the current request context remain open. |
| Budget detail | `/budgets/{id}` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `NO` | `PARTIAL` | Collapse into `Budgets` as breach/history detail, not a separate feature. | P5 | `RE-AUDIT REQUIRED` | `6.4` | Bundle A - Budget Control Plane. As of Friday, August 14, 2026, `/budgets/{id}` is now a true detail page with edit-in-place policy controls, breach history, override management, richer scope selection, and related-scope context instead of acting as breach history only. It still needs the fuller cohesion pass described in the matrix and blueprint, such as stronger cross-links into access ownership, provider/routing context, approvals evidence history, and future projection/coverage views. |
| Budget overrides | `/budget-overrides` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `NO` | `OK` | Collapse into `Budgets` as advanced override workflow. | P5 | `RE-AUDIT REQUIRED` | `6.6` | Bundle A - Budget Control Plane. As of Friday, August 14, 2026, the standalone overrides page is now only a compatibility redirect into `/budgets?tab=overrides`, and the main budgets experience owns create/list/revoke override workflows directly. The second pass also made overrides approval-aware: operators can now request approval before activation, pending overrides stay visible in the budget lifecycle, and approval-linked overrides can be activated or denied through the existing approvals system. Remaining gaps are still real: override lifecycle is not full CRUD, approval UX is still linked rather than deeply embedded, and the evidence/history model still needs a deeper polish pass. |
| Model budgets | `/model-budgets` | `OK` | `LEGACY` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `NO` | `OK` | Collapse into `Model gateway` or `API keys` advanced quota settings and keep only as a compatibility redirect. | P5 | `RE-AUDIT REQUIRED` | `6.7` | Bundle context: supports Bundle A indirectly but should stay collapsed into Gateway or API key quota controls. Completed as a deliberate collapse on Friday, August 14, 2026. The standalone `/model-budgets` page now exists only as a compatibility redirect into the Gateway model-quotas section. Backend lifecycle now includes create/list/update/delete, and the primary UI ownership has moved to `/gateway#gateway-model-quotas` so operators no longer need to paste API-key UUIDs into a separate page. |
| Billing periods | `/billing` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate as the parent billing area. | P5 | `RE-AUDIT REQUIRED` | `6.9` | Bundle B - Billing and Reconciliation. Completed on Friday, August 14, 2026. `/billing` now acts as the real billing operations shell: summary, periods, and shared-cost policies live together; backend period create/list/get/close/export plus shared-cost policy CRUD are surfaced cleanly in the UI; and docs, Postman, manual lab, smoke script, and example coverage now reflect the shipped workflow. |
| Billing period detail | `/billing/{period_id}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep as billing detail. | P5 | `RE-AUDIT REQUIRED` | `6.9` | Bundle B - Billing and Reconciliation. Completed on Friday, August 14, 2026. The detail page is now a true period workspace with summary, reconciliation, breakdown, adjustments, and exports tabs. The missing router reconciliation contract is now real, billing adjustments are manageable from the detail UI with create/edit/delete while periods are open, and the surrounding docs/Postman/lab/example surfaces match the updated operator flow. |
| Chargeback | `/chargeback` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `NO` | `PARTIAL` | Keep separate, but align around workspaces/access groups/workflows. | P5 | `RE-AUDIT REQUIRED` | `6.3`, `6.8` | Bundle C - Attribution and Allocation. Completed on Friday, August 14, 2026 for core backend/UI/support-surface delivery: rule CRUD now includes update/edit, the report and export endpoints are real, docs/Postman/lab/smoke/example coverage is aligned, and the active dimension model stays on modern workspace/workflow/application/user/provider primitives. It remains `IN PROGRESS` at the cohesion layer because deeper access-group/API-key-native attribution and broader confidence/evidence views are still future Bundle C deepening work. |
| Ledger | `/ledger` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collapse into `Platform settings -> Compliance`; keep `/ledger` only as a compatibility redirect, not a separate owner. | P5 | `RE-AUDIT REQUIRED` | `6.10` | Bundle D - Compliance Closure. Completed on Friday, August 14, 2026. The real operator home now lives under Platform Settings -> Compliance, where closure readiness, evidence-chain status, snapshot generation, verification, and links into Billing, Chargeback, Audit, and backup evidence are all visible together. `/ledger` remains a compatibility route, while backend `closure-summary`, docs, Postman, smoke coverage, manual lab, and the example now match that ownership model. |

---

## 6. Build & Improve

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Playground | `/playground` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.4` | Backend session/request CRUD and send/compare APIs exist, but the UI is mostly a history viewer with API examples rather than an interactive playground. |
| Prompts list | `/prompts` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `7.1` | Solid list/create/delete UI backed by real prompt APIs, but full lifecycle completion depends on prompt detail/version flows. |
| Prompt detail and versions | `/prompts/{name}` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `7.1` | One of the strongest shipped feature sets: versioning, promotion, metrics, edit-as-new-version, and Git sync align well with workflow improvement. |
| Agents list | `/agents` | `OK` | `PARTIAL` | `MISSING` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.1` | Backend agent CRUD exists, but the page is read-only card browsing and explicitly tells users to use the API to create agents. |
| Agent detail | `/agents/{agent_id}` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.1` | Good read surface for stats and recent runs, but no edit/retire controls are exposed in the UI. |
| Agent memory | `/agents/{agent_id}/memory` | `PARTIAL` | `OK` | `PARTIAL` | `MISSING` | `PARTIAL` | `MISSING` | `PARTIAL` | `OK` | Collapse into `Agent detail` as a tab unless memory becomes a first-class managed domain. | P6 | `RE-AUDIT REQUIRED` | `8.1` | Useful observability page over memory read endpoints, but it is not a memory management UI and has weak docs/Postman/story coverage. |
| Workflows list | `/workflows` | `OK` | `PARTIAL` | `MISSING` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.2` | Backend workflow CRUD exists, but the page is read-only and tells users to create definitions via API. |
| Workflow detail | `/workflows/{workflow_id}` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.2` | Strong detail page for cost and runs, but no edit/archive controls despite backend support. |
| Workflow run detail | `/workflows/{workflow_id}/runs/{run_id}` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.2`, `3.2` | Good drilldown on workflow execution steps, but it is investigative only and lightly documented. |
| Datasets | `/datasets` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | Group under `Evaluation studio` instead of a separate top-level area. | P6 | `RE-AUDIT REQUIRED` | `7.3` | UI supports create/list/delete and detail viewing, but backend lacks full update flows and docs are bundled into evaluations/replay material. |
| Evaluation studio | `/evaluation` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | Make this the single parent surface for scores, datasets, experiments, and replay. | P6 | `RE-AUDIT REQUIRED` | `7.2`, `7.3` | Cohesive cross-surface studio for experiments, datasets, prompts, and evaluators, but it is an aggregator rather than a clean end-to-end CRUD owner for each entity. |
| Experiments | `/experiments` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | Group under `Evaluation studio`. | P6 | `RE-AUDIT REQUIRED` | `7.3` | Good create/run/delete UI, but full backend CRUD is not complete because update/edit is not exposed as a first-class experiment contract. |
| Replay lab | `/replay` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | Collapse into the evaluation suite as replay mode, not a parallel lab product. | P6 | `RE-AUDIT REQUIRED` | `3.15`, `7.3` | The route works, but it reuses dataset/experiment APIs and concepts instead of a clearly separate replay domain, which weakens cohesion versus the product story. |
| Replay experiment detail | `/replay/{experiment_id}` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | Collapse into `Experiments` detail or evaluation result detail. | P6 | `RE-AUDIT REQUIRED` | `3.15`, `7.3` | Good result view with route recommendation action, but it is built on replay results plus gateway recommendation APIs and lacks a fuller replay management surface. |
| Optimization opportunities | `/optimization-opportunities` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `5.7`, `8.9` | Strong recommendation dashboard, but it derives opportunities heuristically from run-flow data instead of using a dedicated backend opportunities contract. |
| Optimization simulator | `/optimization-simulator` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `3.17`, `5.5`, `5.7` | Real simulation endpoint plus clear UI, but it is a what-if analysis surface rather than a CRUD-managed entity. |
| Model scorecards | `/model-scorecards` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Group with `Model usage` if the product wants one model intelligence area. | P6 | `RE-AUDIT REQUIRED` | `3.14` | Completed on Friday, August 14, 2026. The page already had the real scorecard/trend APIs and an interactive UI; this pass finished the cohesion work by adding dedicated documentation and explicit workflow bridges into Model Usage and Evaluations so the feature is no longer relying on indirect coverage or a CRUD-oriented completion bar that does not fit observability-style model intelligence. |
| Vector stores list | `/vector-stores` | `OK` | `PARTIAL` | `MISSING` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.3` | Backend collection CRUD is real, but the UI is a read-only catalog that again tells users to use the API to create stores. |
| Vector store detail | `/vector-stores/{collection_id}` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `8.3` | Good read-only detail for stats and recent queries, but no rename/update/delete/query actions are surfaced despite backend capability. |
| Runbooks | `/runbooks` | `PARTIAL` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | Keep separate. | P6 | `RE-AUDIT REQUIRED` | `3.16` | Valuable operator workflow with generate/list/export, but it is not a full CRUD domain and backend lives under runs rather than a dedicated runbooks router. |

---

## 7. Platform

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| All organizations | `/organizations` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `NO` | `OK` | Keep separate. | P7 | `RE-AUDIT REQUIRED` | `1.2`, `1.7` | Platform-admin lifecycle hub is real with create/list/update/delete plus suspend/reactivate controls. Not fully complete because support coverage is uneven outside the core UI/API. |
| Platform settings | `/settings` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `NO` | `OK` | Make this the single home for `Ledger`, `Retention`, `Backup`, and ops/compliance surfaces. | P7 | `RE-AUDIT REQUIRED` | `1.7`, `7.7`, `9.3`, `9.4`, `9.5`, `9.11`, `9.12`, `9.13`, `9.14` | This is an umbrella console for compliance, retention, backups, and ops posture. Some subareas like retention are strong CRUD, but the route as a whole is not one cohesive managed entity with a single completion bar. |

---

## 8. Additional Admin / Utility Routes

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Plugins | `/plugins` | `PARTIAL` | `LEGACY` | `LEGACY` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `OK` | Collapse into `Onboarding`; do not keep a redirect-only top-level route. | P1 | `RE-AUDIT REQUIRED` | `8.6` | Backend has full plugin CRUD plus execution logs, but `/plugins` is now only a compatibility redirect into Onboarding. Setup/discovery belongs there; any future dedicated plugin management should be reintroduced intentionally rather than preserved as a ghost route. |

---

## 9. Planned Architecture Additions

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| High-performance gateway service split | `planned service: runledger-gateway-rs` | `PARTIAL` | `MISSING` | `PARTIAL` | `PARTIAL` | `MISSING` | `MISSING` | `NO` | `OK` | Split the inline gateway/runtime path out of the current API service; keep control-plane config in `/gateway` but move hot-path execution into a separately scalable Rust service. | P0 | `RE-AUDIT REQUIRED` | `4.1`, `4.3`, `4.4`, `4.5`, `4.8`, `4.10` | Major architecture addition. The core requirement is a high-performance data plane that can scale independently from the Python control plane without losing policy, routing, cache, budget, and ledger cohesion. The runtime architecture is now tracked in the unified doc `docs/gateway/gateway-rs-spec.mdx`, and the phase 1 backend contract endpoints already exist for runtime snapshots plus signed event ingest. |
| Review refactored gateway modules and migrate remaining hot data path into Rust | `cross-cutting: gateway router split` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `MISSING` | `MISSING` | `NO` | `OK` | Keep the refactored Python router split as the control-plane layout, but move any remaining live request-path logic out of Python and into `runledger-gateway-rs`. | P0 | `RE-AUDIT REQUIRED` | `4.1`, `4.3`, `4.4`, `4.5`, `4.8`, `4.10`, `apps/api/runledger_api/routers/gateway*.py` | The recent split into `gateway.py` (thin aggregator), `gateway_shared.py`, `gateway_legacy.py`, `gateway_routing.py`, `gateway_passthrough.py`, `gateway_runtime.py`, and `gateway_observability.py` is directionally correct and should not be undone. It clarifies the control-plane boundary. The follow-up task is to review those modules and identify anything still on the hot data path, especially runtime-support behavior concentrated in `gateway_runtime.py` and any execution helpers still pulled through `gateway_shared.py`. Desired end state: Python keeps CRUD, snapshots, observability, benchmarks, flywheel/recommendations, compatibility shims, and admin/config UX support; Rust owns authentication resolution needed for execution, live route decisioning, provider execution, fallback/retries, cache participation, and other latency-sensitive runtime enforcement. |
| Collapse `runledger-router` into the Rust gateway | `planned service merge: runledger-router -> runledger-gateway-rs` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `MISSING` | `MISSING` | `NO` | `OK` | Fold the hot-path intelligent routing classifier into the Rust gateway runtime; keep Python control-plane routing/admin APIs separate and do not confuse runtime decisioning with admin/config routing surfaces. | P0 | `RE-AUDIT REQUIRED` | `4.3`, `4.4`, `4.5`, `4.8`, `4.10`, `docs/gateway/*`, `docker-compose.yml` | Architecture recommendation for the final gateway pass based on the current code: `runledger-router` is a narrow auxiliary service, not a broad control-plane subsystem. The Python side only uses it through `apps/api/runledger_api/services/intelligent_router.py` via `ROUTER_SVC_URL`, and that client is invoked directly on the live gateway hot path in `apps/api/runledger_api/routers/gateway_runtime.py`. That makes it a strong fit to fold into `runledger-gateway-rs` so the data-plane path becomes authenticate -> preflight -> classify -> choose route -> execute, without bouncing into a separate Python microservice. Move to Rust next: intelligent routing/classification, any remaining route selection and fallback logic still tied to Python preflight, semantic cache lookup/store if the goal is a fully self-contained request path, and context compiler only if we are willing to reimplement it cleanly because it is materially larger than the router. Keep in Python for now: gateway CRUD/admin APIs in `routers/gateway_routing.py`, runtime snapshot and signed event ingest in `services/gateway_runtime.py`, `/gateway/flywheel` recommendation surfaces, stats/requests/benchmark/management endpoints, and UI-facing config surfaces. Target architecture: Rust gateway = data plane for auth resolution, intelligent routing, route selection, provider execution, retries/fallback, cache, and live-traffic enforcement. Python API = control plane for CRUD, snapshots, analytics, recommendations, observability summaries, and admin UX support. Operational note: `docker-compose.yml` still defines `runledger-router` as a separate sidecar using the same gateway runtime port family, which adds stack complexity and is another reason to collapse it once parity is complete. |
| Legacy Python gateway deprecation and consumer migration | `cross-cutting: docs/examples/postman/scripts` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `NO` | `OK` | Collapse all remaining inline-gateway assumptions into the Rust runtime model and remove stale Python-hosted completion references. | P0 | `RE-AUDIT REQUIRED` | `4.1`, `4.3`, `4.8`, `reference/api`, `docs/*`, `scripts/*`, `examples/*` | Track the cleanup work after the hard cut: move all live completion examples to `runledger-gateway-rs`, keep management and analytics APIs on the control plane, migrate generated Postman/OpenAPI guidance, and remove dead inline-runtime code from the Python gateway router once the remaining consumers are updated. |
| Pipeline studio and flow builder | `/pipeline-studio` | `MISSING` | `MISSING` | `MISSING` | `PARTIAL` | `MISSING` | `MISSING` | `NO` | `OK` | New surface; this should unify visualization and authoring instead of spawning separate “diagram” and “builder” products. | P0 | `RE-AUDIT REQUIRED` | `2.3`, `2.5`, `2.6`, `3.6`, `4.1`, `6.4` | Intended as both an execution-path visualization and a flow builder: ingest -> routing -> branches -> enforcement -> outcomes -> reporting. Needs a strong workflow-centered model before UI work starts. |
| API explorer and generated Swagger UI | `/api-docs` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `LEGACY` | `MISSING` | `NO` | `OK` | Collapse manual Postman-first maintenance into generated OpenAPI/Swagger plus an embedded GUI explorer. | P1 | `RE-AUDIT REQUIRED` | `reference/api` | OpenAPI already exists, but the desired state is a first-class generated Swagger surface with in-product exploration and less manual Postman drift. |
| In-app customer documentation and help hub | `planned top-right help / docs hub` | `MISSING` | `MISSING` | `MISSING` | `PARTIAL` | `N/A` | `MISSING` | `NO` | `OK` | New surface; do not scatter help links randomly across pages. | P1 | `RE-AUDIT REQUIRED` | `1.8`, `docs/*` | The goal is contextual help inside the product, likely launched from the top-right corner, with customer-facing docs and task guidance embedded rather than forcing external navigation. |
| UI theme refresh and dark-mode redesign | `cross-app` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `MISSING` | `N/A` | `MISSING` | `NO` | `OK` | One cross-app design system pass, not page-by-page ad hoc recoloring. | P1 | `RE-AUDIT REQUIRED` | `apps/web/app/globals.css`, `apps/web/components/*` | The current dark theme works functionally but needs a more intentional color system, contrast review, and overall platform visual polish. |
| Documentation IA, hierarchy, and diagrams | `docs/` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `NO` | `OK` | Reorganize docs by product workflow and architecture domains instead of historical/random accretion. | P1 | `RE-AUDIT REQUIRED` | `docs/introduction.mdx`, `docs/architecture.md`, `docs/mint.json` | This pass starts the docs reorganization, but the larger goal is feature-oriented navigation, richer mermaid coverage, and a clearer hierarchical explanation of how the platform is used end to end. |
| Broader repo naming and historical cleanup review | `cross-cutting: tests/scripts/docs` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `NO` | `OK` | Keep as a final consistency pass; remove historical phase-style naming and delivery-era labels where they no longer help operators or developers. | P1 | `RE-AUDIT REQUIRED` | `docs/*`, `scripts/*`, `apps/api/tests/*` | Add a broader review after feature delivery work stabilizes: scrub leftover phase-oriented naming, stale migration language, and other history-shaped labels across tests, scripts, docs, and support assets so the repo reads in product terms instead of implementation chronology. This is lower risk than runtime work, but it improves cohesion for both human operators and future AI agents navigating the codebase. |
| Scope-aware runtime governance enforcement deepening | `cross-cutting: gateway + tool governance hot path` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `MISSING` | `MISSING` | `NO` | `OK` | Keep Tool Registry and Tool Policies as the control-plane UX, but deepen enforcement in the runtime path so scope context is enforced directly on live traffic. | P1 | `RE-AUDIT REQUIRED` | `4.1`, `4.5`, `7.13`, `7.14`, `apps/api/runledger_api/services/plugin_runner.py`, `apps/api/runledger_api/routers/workspace_controls.py`, `runledger-gateway-rs` | Current governance is materially stronger now that registry and policy management are cohesive, but richer scope-aware runtime enforcement is still a future deepening pass. Today the runtime matching is still centered mainly on tool/action decisions. The follow-up should enforce broader scope context such as workspace and access-group ownership directly on the hot path, with clearer propagation of scope identity into execution, logging, and violation outcomes so policy decisions are not limited to coarse tool/action matching alone. |

---

## 10. Final Pass

Use this section for polish, coherence, and close-out work after a feature is already functionally complete. These rows should capture UX cleanup, naming cleanup, interaction consistency, and final audit tightening rather than first-pass implementation.

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Gateway management UX polish | `/gateway` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Keep inside `Model gateway`; do not split into a separate long-term feature. | P9 | `RE-AUDIT REQUIRED` | `4.1`, `4.3`, `4.4`, `4.7` | Final pass completed on Friday, August 14, 2026: the gateway page now has edit-in-place flows for routes, routing groups, routing policies, and pass-through endpoints, plus clearer inline editing affordances so the management surface feels cohesive instead of toggle-only. |

---

## Audit Notes

- Audit `FEATURE-AUDIT.md` against the real routed product surface first.
- Audit `DELIVERY-AUDIT.md` against broader delivery coverage, documentation, examples, automation, and infrastructure second.
- Treat `FEATURE-AUDIT.md` as both the audit record and the gap-capture / fix-tracking file: audit the real feature, capture the gaps directly here, fix the feature end to end, verify cohesion across backend/UI/docs/Postman/scripts/examples, and only then move on to the next feature.
- When a feature has a list page and a detail page, do not mark the feature done until both are audited.
- For legacy pages (`Projects`, `Team Models`), document whether they should be maintained, minimized, or retired.

---

## 11. Feature Cohesion Matrix

Purpose:

- track whether major feature families actually work together
- prevent features from being built in isolation
- create an explicit cross-feature audit surface we can fill section by section

Matrix status legend:

- `STRONG` = current feature relationship is real and directionally cohesive
- `PARTIAL` = some integration exists but it is incomplete, awkward, or not operator-friendly
- `GAP` = feature relationship should exist but is missing or too weak to rely on
- `N/A` = no meaningful direct dependency

Matrix expansion plan:

- this section starts with a FinOps-first audit because Bundle A is the next implementation target
- future passes should add equivalent matrices for Gateway, Observe, Safety & Governance, Organization & Access, and Build & Improve

### 11.1 Current Matrix Scope

Major feature families and subfeatures currently in scope for matrix-driven auditing:

- `Organization & Access`
  - Organization profile
  - Org settings
  - Onboarding
  - Users
  - Workspaces
  - Access groups
  - API keys
  - Integrations
  - Telemetry
  - MCP registry
  - AI hub
  - Projects
  - Team models
- `Gateway & Routing`
  - Provider profiles
  - Model gateway
  - Guardrails
  - Response cache
  - Rate limits
- `Safety & Governance`
  - MCP servers
  - Search tools
  - Tool registry
  - Tool policies
  - Policy dry run
  - Approvals
  - Data capture
  - Security
  - Alert rules
  - Audit log
  - Governance pack
  - Tags
- `FinOps`
  - Budgets
  - Budget detail
  - Budget overrides
  - Budget notifications
  - Billing periods
  - Billing period detail
  - Chargeback
  - Ledger

This is the first fully expanded matrix pass for `FinOps` against the full shipped feature surface that has already been audited in sections `1-8`.

- columns are now expanded to the actual minor features, not just the major family names
- completed features are included on purpose so cohesion is audited across the whole shipped suite, not only against unfinished work
- planned architecture additions from section `9` and polish-only items from section `10` should be added in a later matrix pass after the shipped surface is fully captured here

### 11.2 FinOps Cohesion Matrix

This first populated matrix follows the diagram pattern more closely while staying readable in Markdown:

- left side = audited major feature plus its subfeatures
- top side = major/minor features from the other feature families
- cells = current cohesion state for the relationship
- because Markdown tables cannot merge header cells like the sketch, each column is labeled as `Major Feature: Minor Feature`
- because one true mega-table would be too wide to audit properly, the full column set is split into aligned sub-matrices by feature family

Current row major feature under audit: `FinOps`

### 11.2a FinOps x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| FinOps | Budgets | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `GAP` | `GAP` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Strongest current relationship is workspace ownership; biggest missing relationships are access-group and API-key budget scope. |
| FinOps | Budget detail | `GAP` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `GAP` | `GAP` | `N/A` | `PARTIAL` | `N/A` | `GAP` | `N/A` | `N/A` | The missing true detail page blocks useful cross-links into org rollups, key ownership, and model-catalog context. |
| FinOps | Budget overrides | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `GAP` | `GAP` | `N/A` | `N/A` | `N/A` | `GAP` | `N/A` | `N/A` | Overrides exist, but they are not yet integrated with the main org and access-control operating model. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Notification delivery is real, but it is not yet surfaced as part of the main org-facing FinOps workflow. |
| FinOps | Billing periods | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Billing already consumes workspace spend well, but attribution and ownership dimensions remain thin. |
| FinOps | Billing period detail | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Detail view is informative, but not yet a strong operational bridge back into the access and catalog surfaces. |
| FinOps | Chargeback | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Chargeback is directionally aligned to workspaces, but still needs stronger access-group and API-key attribution. |
| FinOps | Ledger | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger belongs more to platform compliance than to daily org operations. |

### 11.2b FinOps x Gateway & Routing

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------|
| FinOps | Budgets | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | FinOps and Gateway are related today, but spend policy still is not clearly the canonical owner across provider, cache, and throttling controls. |
| FinOps | Budget detail | `GAP` | `GAP` | `N/A` | `GAP` | `GAP` | The current detail experience is too shallow to show route, provider, or quota-aware spend analysis. |
| FinOps | Budget overrides | `GAP` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Overrides can influence runtime behavior, but the product does not yet expose that relationship cleanly. |
| FinOps | Budget notifications | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Notifications should eventually reflect gateway-side quota or route pressure events more explicitly. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | Billing can already consume gateway-shaped spend, but the operator surface does not make that relationship rich enough. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | Detail view needs clearer route, provider, and quota breakdowns if reconciliation is going to be trusted. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | Chargeback is moving in the right direction, but it still lacks stronger gateway-native business attribution. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger is downstream evidence, not an active gateway operating surface. |

### 11.2c FinOps x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-------------------|------------------|-----------------|------------------------|-------------|------------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Observe already consumes spend data broadly, but budget policy is still not the clear source of truth for many of those views. |
| FinOps | Budget detail | `GAP` | `GAP` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `GAP` | `N/A` | `GAP` | `GAP` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `GAP` | `GAP` | `GAP` | `GAP` | `PARTIAL` | The missing real budget detail page is the biggest cohesion blocker between FinOps and Observability. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | Overrides should become more visible in investigative surfaces so operators can explain spend exceptions. |
| FinOps | Budget notifications | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | Notification history belongs in the broader observe-and-act story but is not yet visible there. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Billing already has strong economics cohesion, especially with the economics and billing-summary surfaces. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Richer drilldowns are present, but still not tied tightly enough to scope-level reconciliation and operator actions. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Chargeback fits naturally into the economics/analytics layer, but its business-dimension model still needs hardening. |
| FinOps | Ledger | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | Ledger should be referenced by observe surfaces, but not owned by them. |

### 11.2d FinOps x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| FinOps | Budgets | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `GAP` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Governance evidence exists, but budget policy lifecycle is still not tightly integrated with approvals, alerts, and tagging. |
| FinOps | Budget detail | `N/A` | `N/A` | `GAP` | `N/A` | `N/A` | `GAP` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `GAP` | `GAP` | Detail is too weak to support meaningful governance review or traceability. |
| FinOps | Budget overrides | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `GAP` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `GAP` | Overrides are the clearest place where approval-driven governance should exist and currently does not. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | Notification and evidence paths are stronger than the main budget workflow today. |
| FinOps | Billing periods | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Billing has useful evidence hooks, but not a deeply governed operator story yet. |
| FinOps | Billing period detail | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Reconciliation detail can support governance, but the user flow still feels finance-only rather than policy-aware. |
| FinOps | Chargeback | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tagging and evidence are important here, but the overall governance relationship is still moderate rather than strong. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `N/A` | Ledger is primarily a compliance evidence surface, so governance-pack cohesion is one of the strongest relationships in the matrix. |

### 11.2e FinOps x Build & Improve

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | FinOps should increasingly act as a feedback loop into optimization, workflows, and prompt/model improvement rather than sitting as a separate finance island. |
| FinOps | Budget detail | `GAP` | `GAP` | `GAP` | `GAP` | `GAP` | `N/A` | `GAP` | `GAP` | `PARTIAL` | `N/A` | `GAP` | `GAP` | `GAP` | `GAP` | `PARTIAL` | `PARTIAL` | `GAP` | `N/A` | `N/A` | `GAP` | Without a real detail page, FinOps cannot meaningfully guide improvement work across the build surfaces. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Override decisions should eventually be visible as explicit engineering or evaluation exceptions. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | Notifications should feed operators and builders when spend issues affect workflow improvement loops. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Billing and optimization already want to work together; the product should lean into that relationship more intentionally. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Reconciliation detail should become a stronger input into experimentation and optimization decisions. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Chargeback is most cohesive when tied to workflows and improvement programs rather than only to flat finance reports. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger is largely outside the day-to-day build loop except as downstream evidence. |

### 11.2f FinOps x Platform and Utility

| Row Major Feature | Row Subfeature | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|-------------------|-------------------|---------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `N/A` | FinOps should surface clearly at both org and platform scope, but platform ownership is still under-structured. |
| FinOps | Budget detail | `GAP` | `PARTIAL` | `N/A` | Platform operators still lack a strong detail view for cross-org spend governance. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `N/A` | Override governance should eventually include platform-level review and reporting. |
| FinOps | Budget notifications | `PARTIAL` | `PARTIAL` | `N/A` | Notifications need stronger platform-level visibility and administration. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `N/A` | Billing already has platform relevance, but the user workflow is not fully unified yet. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `N/A` | Platform-side billing drilldowns should become more operational and less passive. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `N/A` | Chargeback belongs at both org and platform layers, but the allocation model needs deepening. |
| FinOps | Ledger | `PARTIAL` | `STRONG` | `N/A` | Ledger is the clearest FinOps-to-platform-settings relationship in the current product. |

### 11.2g FinOps x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| FinOps | Budgets | `STRONG` | `GAP` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budgets is the intended FinOps control-plane anchor, but too many internal relationships are still weak or indirect. |
| FinOps | Budget detail | `GAP` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `GAP` | `GAP` | The missing true detail surface is the biggest internal cohesion break inside FinOps. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Overrides are real, but they still feel like a side-table instead of a first-class budget lifecycle feature. |
| FinOps | Budget notifications | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Notification behavior exists, but it is still not tightly embedded into the day-to-day FinOps operator experience. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | Billing is internally the most cohesive FinOps block today, but it still does not fully connect back to budget governance. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | Billing detail is structurally sound, but its ties to the rest of the FinOps control plane remain moderate. |
| FinOps | Chargeback | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | Chargeback belongs inside FinOps, but it still behaves more like an adjacent report than a deeply integrated allocation engine. |
| FinOps | Ledger | `PARTIAL` | `GAP` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Ledger closes the loop for evidence and verification, but it is not yet woven tightly into the upstream operating flows. |

### 11.2h Matrix Reading Notes

- `FinOps -> Budgets x Workspaces = STRONG`
  Means the current implementation already has a meaningful real relationship there.
- `FinOps -> Budgets x Access groups = GAP`
  Means the relationship should exist, but the current product and runtime do not yet expose it strongly enough.
- `FinOps -> Budget detail x Provider profiles = GAP`
  Means the detail experience is too weak to expose a relationship that Bundle A should eventually support.
- `FinOps -> Billing periods x Analytics economics = STRONG`
  Means the relationship is already real in the shipped suite, even if the operator workflow still needs tightening.
- `FinOps -> Chargeback x Workflow detail = STRONG`
  Means the product direction is clearest when financial attribution is tied back to workflows rather than to legacy organizational abstractions.
- `FinOps -> Budgets x Budget detail = GAP`
  Means the main control-plane feature still lacks the internal detail experience needed to make the rest of FinOps cohesive.

### 11.2i FinOps Bundle A Audit Findings

These findings should directly shape `Bundle A - Spend Control Plane`:

1. `Budgets` must become access-aware.
   Current code and UI treat workspace as the main real scope, but the next implementation pass should explicitly support access groups and API keys as first-class budget scopes.
2. `Budgets` must become gateway-aware but not gateway-owned.
   Gateway quota tiers and model quotas are related, but spend governance should remain owned by FinOps while cross-linking clearly into Gateway technical controls.
3. `Budget detail` is the biggest current cohesion gap.
   Without a true detail page, budgets cannot meaningfully connect to organization rollups, access scopes, API keys, provider profiles, approvals, or policy history.
4. `Budget overrides` must be approval-aware.
   The current lifecycle is useful, but it behaves like a detached exception table instead of a governed override workflow.
5. `Budget notifications` should be pulled into the main Spend Control Plane.
   The backend is already stronger than the UI here, so this is a high-value cohesion win for Bundle A.
6. `Provider profiles` and `Tags / workflows` are missing as first-class budget dimensions.
   These are essential if FinOps is going to become one of the strongest feature families instead of remaining workspace-only.
7. `Audit log` and `Governance pack` already provide the right evidence direction.
   Bundle A should lean into these instead of inventing separate evidence flows.
8. `Organization profile` should consume budget rollups, but Bundle A should remain the canonical spend-policy owner.
   This keeps FinOps cohesive without scattering budget editing into org admin pages.

### 11.3 Organization & Access Cohesion Matrix

This section applies the same matrix structure to `Organization & Access` against the rest of the shipped feature surface.

Current row major feature under audit: `Organization & Access`

### 11.3a Organization & Access x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| Organization & Access | Organization profile | `PARTIAL` | `GAP` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Org profile should consume spend posture and budget posture, but it should not become a second FinOps control plane. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only; no separate long-term cohesion target. |
| Organization & Access | Onboarding | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Onboarding should eventually help operators discover budgets and billing setup, but it is not the operating surface itself. |
| Organization & Access | Users | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | User identity should connect more clearly to spend accountability and attribution. |
| Organization & Access | Workspaces | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | Workspaces are already the strongest real join between Org & Access and FinOps. |
| Organization & Access | Access groups | `GAP` | `GAP` | `GAP` | `N/A` | `GAP` | `GAP` | `PARTIAL` | `N/A` | Access groups should become first-class financial scopes and currently are not. |
| Organization & Access | API keys | `GAP` | `GAP` | `GAP` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | API keys already carry runtime identity but are not yet treated as first-class budget owners. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Telemetry should reinforce financial attribution by org scope, but the relationship is still indirect. |
| Organization & Access | MCP registry | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | MCP lifecycle is mostly orthogonal to FinOps today. |
| Organization & Access | AI hub | `PARTIAL` | `GAP` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | AI hub needs clearer ties to provider cost posture, model budgets, and downstream financial ownership. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3b Organization & Access x Gateway & Routing

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------|
| Organization & Access | Organization profile | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | The org console should summarize runtime posture without duplicating gateway control-plane ownership. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Onboarding is the right discovery surface for connecting to gateway capabilities, but not for long-term management. |
| Organization & Access | Users | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | User identity and role posture should connect more clearly to runtime and provider access. |
| Organization & Access | Workspaces | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Workspaces are already the canonical runtime boundary and should remain so. |
| Organization & Access | Access groups | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | Access groups are becoming a meaningful governance and runtime scoping primitive, but the gateway path can deepen further. |
| Organization & Access | API keys | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | API keys already bridge deeply into gateway and quota controls, making this one of the strongest cross-feature relationships. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Telemetry has a meaningful relationship to runtime ownership, but not much direct configuration linkage. |
| Organization & Access | MCP registry | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | MCP should increasingly inherit org/workspace/access context more explicitly across live execution. |
| Organization & Access | AI hub | `STRONG` | `STRONG` | `N/A` | `N/A` | `PARTIAL` | AI hub, provider profiles, and gateway ownership should read as one cohesive model-access story. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3c Organization & Access x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-----------------|------------------|-----------------|------------------------|-------------|------------|---------|
| Organization & Access | Organization profile | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Org profile should summarize cross-workspace activity, but analytics remains the proper investigative owner. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | Onboarding should explain where operators go next, but not own the operational observability loop. |
| Organization & Access | Users | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `N/A` | `N/A` | User analytics already provides the clearest observability counterpart to user management. |
| Organization & Access | Workspaces | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Observe is already heavily workspace-scoped, making this one of the strongest suite-level cohesion stories. |
| Organization & Access | Access groups | `PARTIAL` | `PARTIAL` | `GAP` | `GAP` | `N/A` | `N/A` | `GAP` | `N/A` | `GAP` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Observability does not yet expose access-group scope strongly enough for investigation and chargeback-style use cases. |
| Organization & Access | API keys | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | API-key identity is present in places, but it is not yet a first-class investigation dimension across Observe. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | Telemetry is correctly inside Observe now, but should keep inheriting org/workspace scope more consistently. |
| Organization & Access | MCP registry | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | MCP activity should become easier to inspect through the broader observability layer over time. |
| Organization & Access | AI hub | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | AI hub and model-usage surfaces already form a natural cross-feature story. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3d Organization & Access x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| Organization & Access | Organization profile | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Org profile should summarize governance posture, but the governance features should keep their own control planes. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Onboarding is the right place for discovery and setup guidance across governance features. |
| Organization & Access | Users | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Users should connect more clearly to approval, security, and audit workflows. |
| Organization & Access | Workspaces | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Workspaces are already a core scope primitive for many governance features. |
| Organization & Access | Access groups | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | Access groups and tags/guardrails are moving toward a meaningful governance-scoping story that can deepen further. |
| Organization & Access | API keys | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | API keys should be better integrated into approvals, data capture, and runtime policy evidence. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Telemetry should increasingly participate in security, alerting, and evidence workflows. |
| Organization & Access | MCP registry | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | MCP registry already sits near the center of the tool-governance story. |
| Organization & Access | AI hub | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | AI hub needs clearer ties to approval and evidence flows around model access and deprecation. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3e Organization & Access x Build & Improve

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|---------|
| Organization & Access | Organization profile | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Org scope should eventually shape build surfaces more consistently, but today the relationship is mostly indirect. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Onboarding is the natural front door into the build surfaces and should stay that way. |
| Organization & Access | Users | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Builder identity and ownership should flow more clearly from users into build and experimentation areas. |
| Organization & Access | Workspaces | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Workspaces are already the clearest cohesion backbone for Build & Improve. |
| Organization & Access | Access groups | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Access groups should show up much more explicitly as execution and experimentation scope in build surfaces. |
| Organization & Access | API keys | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | API-key identity matters in execution and evaluation, but the UI does not yet reflect that coherently. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Telemetry should increasingly feed replay, experiments, and optimization. |
| Organization & Access | MCP registry | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | MCP should eventually feel more native inside the build workflow rather than adjacent to it. |
| Organization & Access | AI hub | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | AI hub is already naturally close to prompts, workflows, and model scorecards, but the full story can tighten more. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3f Organization & Access x Platform / Utility / Self

| Row Major Feature | Row Subfeature | All organizations | Platform settings | Plugins | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|-------------------|-------------------|---------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| Organization & Access | Organization profile | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Organization profile is the core admin anchor, but it should remain a coordinator rather than absorbing every org feature directly. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Onboarding should stay the guided entry point into the whole organization surface. |
| Organization & Access | Users | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Users is a strong managed entity, but should connect more visibly to workspaces, access groups, and keys as one identity story. |
| Organization & Access | Workspaces | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Workspaces are the most cohesive non-legacy feature inside this family. |
| Organization & Access | Access groups | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Access groups are strategically important but still not as deeply threaded through the suite as workspaces. |
| Organization & Access | API keys | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | API keys are strong operationally, but the cross-feature story is still split between org and gateway surfaces. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Collapsed legacy surface; coherence is now defined by Onboarding. |
| Organization & Access | Telemetry | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | Telemetry is intentionally adjacent rather than central in this family. |
| Organization & Access | MCP registry | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | MCP registry is cohesive, but its relationship to the rest of Org & Access can still be tightened. |
| Organization & Access | AI hub | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | AI hub is cohesive as a workspace model-catalog surface, but it still needs clearer bridges into the broader org-admin flow. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.4 Gateway & Routing Cohesion Matrix

This section applies the same matrix structure to `Gateway & Routing` against the rest of the shipped feature surface.

Current row major feature under audit: `Gateway & Routing`

### 11.4a Gateway & Routing x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| Gateway & Routing | Provider profiles | `PARTIAL` | `PARTIAL` | `GAP` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Friday, August 14, 2026 pass added backend budget posture, scoped budget links, and scoped budget creation from provider profiles, but richer billing and override cohesion is still open. |
| Gateway & Routing | Model gateway | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Friday, August 14, 2026 pass improved the Gateway-to-Budgets operator bridge, but deeper embedded budget context and downstream FinOps cohesion are still not strong enough to close the matrix. |
| Gateway & Routing | Guardrails | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Guardrails is only indirectly tied to FinOps today. |
| Gateway & Routing | Response cache | `PARTIAL` | `GAP` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Cache economics matter, but the product does not yet surface that relationship richly enough. |
| Gateway & Routing | Rate limits | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Rate limits and quota controls are related to spend but still not modeled as one cohesive operator flow. |

### 11.4b Gateway & Routing x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| Gateway & Routing | Provider profiles | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | Provider profiles are already close to AI hub and workspace ownership, but can still connect more clearly to org-level access decisions. |
| Gateway & Routing | Model gateway | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | Gateway control plane already intersects strongly with workspaces, API keys, and AI hub. |
| Gateway & Routing | Guardrails | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Guardrails already connect meaningfully to access groups and should keep deepening there. |
| Gateway & Routing | Response cache | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Response cache is now intentionally a gateway-owned subfeature, not a separate access surface. |
| Gateway & Routing | Rate limits | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Rate limits already intersect strongly with API keys and should connect more clearly to scope ownership. |

### 11.4c Gateway & Routing x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-----------------|------------------|-----------------|------------------------|-------------|------------|---------|
| Gateway & Routing | Provider profiles | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | Provider profiles and model-usage surfaces already have a strong natural cohesion. |
| Gateway & Routing | Model gateway | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | Gateway and Observe already form one of the strongest runtime-to-investigation stories in the suite. |
| Gateway & Routing | Guardrails | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | Guardrail impacts should become easier to follow in the request-analysis flow. |
| Gateway & Routing | Response cache | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | Cache behavior matters to performance and economics, but the observability story is still moderate. |
| Gateway & Routing | Rate limits | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | Rate-limit behavior should become easier to inspect alongside live request and monitoring data. |

### 11.4d Gateway & Routing x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| Gateway & Routing | Provider profiles | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Provider access and deprecation controls should become more explicitly policy-aware. |
| Gateway & Routing | Model gateway | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Model gateway is already central to runtime governance and should remain so. |
| Gateway & Routing | Guardrails | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | Guardrails is already one of the strongest bridges between runtime enforcement and governance surfaces. |
| Gateway & Routing | Response cache | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Cache should remain subordinate to gateway policy and auditability rather than becoming an isolated feature. |
| Gateway & Routing | Rate limits | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | Throttling and quota behaviors belong close to policy, alerting, and security posture. |

### 11.4e Gateway & Routing x Build & Improve / Platform / Self

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | All organizations | Platform settings | Plugins | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|-------------------|-------------------|---------|-------------------|---------------|------------|----------------|-------------|---------|
| Gateway & Routing | Provider profiles | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Provider profiles already tie together model operations well, but platform and improvement links can still get tighter. |
| Gateway & Routing | Model gateway | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Gateway is already central to execution and optimization, and should remain the canonical runtime control-plane owner. |
| Gateway & Routing | Guardrails | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `N/A` | `N/A` | Guardrails is internally cohesive and increasingly well tied to the broader runtime path. |
| Gateway & Routing | Response cache | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | Response cache now belongs inside gateway, and its strongest cohesion is with simulation and runtime optimization. |
| Gateway & Routing | Rate limits | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | Rate limits is now correctly collapsed into gateway, but its relationships to platform operations and optimization can still deepen. |

### 11.5 Observe Cohesion Matrix

This section applies the same matrix structure to `Observe` against the rest of the shipped feature surface.

Current row major feature under audit: `Observe`

### 11.5a Observe x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| Observe | Analytics overview | `PARTIAL` | `GAP` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Analytics overview consumes economics context well, but it is still not anchored cleanly to the FinOps control plane. |
| Observe | Runs list | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Runs should become easier to explain through budget, quota, and allocation context. |
| Observe | Run detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Run detail has the raw data to support FinOps explanations, but the product bridges are still thin. |
| Observe | Request flow | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Request Flow is a natural place to visualize financial and quota impacts, but that linkage is still immature. |
| Observe | Request explorer | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Request Explorer should be one of the strongest surfaces for cost attribution and budget debugging. |
| Observe | Model usage | `PARTIAL` | `GAP` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Model Usage already shares a strong natural relationship with provider cost, but budget and billing bridges can deepen. |
| Observe | Analytics economics | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | Observe is already strongest where it overlaps with economics and billing, which is a good base for deeper FinOps cohesion. |
| Observe | Cost and savings | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | Cost and Savings is already a natural FinOps companion and should keep tightening to the budget control plane. |
| Observe | Outcomes and ROI | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Outcomes and ROI should become a clearer top-layer consumer of spend and chargeback data. |
| Observe | Monitoring | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Monitoring should increasingly show the operational consequences of spend controls and thresholds. |

### 11.5b Observe x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| Observe | Analytics overview | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Observe already inherits workspace and org scope well, but access-group and API-key scope need strengthening. |
| Observe | Runs list | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Runs are strongly workspace-native, but weaker for access-group and key-centric investigation. |
| Observe | Run detail | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Run detail should increasingly expose identity and scope provenance more explicitly. |
| Observe | Request flow | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Request Flow is one of the best candidates for deeper scope-aware observability. |
| Observe | Request explorer | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Request Explorer should become a stronger bridge to access groups and API-key identity. |
| Observe | Model usage | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `N/A` | Model Usage and AI Hub already form a strong model-intelligence pair. |
| Observe | Analytics users | `PARTIAL` | `N/A` | `N/A` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | User analytics is the clearest existing Observe bridge to the user-management surface. |
| Observe | Telemetry | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | Telemetry is already correctly placed in Observe, with scope inheritance still improving. |
| Observe | Monitoring | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Monitoring and telemetry together should become the clearest operational reflection of scope posture. |
| Observe | Model scorecards | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | Scorecards already align well with AI Hub and workspace model ownership. |

### 11.5c Observe x Gateway & Routing / Safety & Governance / Self

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Tool registry | Tool policies | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Analytics overview | Runs list | Request flow | Request explorer | Monitoring | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------------|---------------|-----------|--------------|----------|-------------|-----------|-----------------|------|--------------------|-----------|--------------|------------------|------------|---------|
| Observe | Analytics overview | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Analytics overview is the suite’s observability front door, but it should connect more explicitly to runtime governance and gateway posture. |
| Observe | Runs list | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | Runs are already one of the strongest bridge entities between runtime, governance, and investigation. |
| Observe | Run detail | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | Run detail should remain a core correlation surface across the suite. |
| Observe | Request flow | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | Request Flow is one of the strongest runtime-to-observability bridges and should keep deepening. |
| Observe | Request explorer | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | Request Explorer already sits near the center of investigative cohesion. |
| Observe | Model usage | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Model Usage and provider profiles are one of the clearest cross-feature joins in the product. |
| Observe | Monitoring | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Monitoring is already a strong operational hub and should continue converging runtime and governance signals. |
| Observe | Telemetry | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Telemetry is now correctly treated as observability rather than integration setup. |
| Observe | Analytics economics | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Analytics economics is internally cohesive, but should remain an overview bridge rather than a competing deep-dive owner. |
| Observe | Cost and savings | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Cost and Savings is already cohesive with the economics layer and should stay clearly positioned there. |

### 11.6 Safety & Governance Cohesion Matrix

This section applies the same matrix structure to `Safety & Governance` against the rest of the shipped feature surface.

Current row major feature under audit: `Safety & Governance`

### 11.6a Safety & Governance x FinOps / Organization & Access

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Chargeback | Ledger | Organization profile | Onboarding | Users | Workspaces | Access groups | API keys | MCP registry | AI hub | Finding |
|-------------------|----------------|---------|---------------|------------|--------|----------------------|------------|-------|------------|---------------|----------|--------------|--------|---------|
| Safety & Governance | Tool registry | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | Tool Registry is already central to MCP and runtime policy, but financial and identity posture can deepen further. |
| Safety & Governance | Tool policies | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | Tool Policies already align strongly with MCP and workspace control, and should deepen with richer scope awareness. |
| Safety & Governance | Approvals | `GAP` | `GAP` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Approvals should connect much more strongly to budget overrides, model access, and scope governance. |
| Safety & Governance | Data capture | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Data Capture is well-scoped operationally, but still reads as a separate policy island in places. |
| Safety & Governance | Security | `N/A` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Security is already well-rooted in org/workspace scope and should remain one of the stronger governance blocks. |
| Safety & Governance | Alert rules | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Alert Rules is already a good operations bridge and should connect more clearly to budget and policy conditions. |
| Safety & Governance | Audit log | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Audit Log is a strong evidence layer, but upstream surfaces should link into it more explicitly. |
| Safety & Governance | Governance pack | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | Governance Pack is strongest as evidence closure and should keep consuming the rest of the suite cleanly. |
| Safety & Governance | Tags | `PARTIAL` | `GAP` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | Tags are strategically important because they can become a shared scoping and attribution layer across the suite. |

### 11.6b Safety & Governance x Gateway & Routing / Observe / Self

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Runs list | Run detail | Request flow | Request explorer | Monitoring | Tool registry | Tool policies | Approvals | Security | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|-----------|------------|--------------|------------------|------------|---------------|---------------|-----------|----------|-----------|-----------------|------|---------|
| Safety & Governance | Tool registry | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tool Registry is already a major runtime-governance anchor and should stay tightly coupled to gateway control. |
| Safety & Governance | Tool policies | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tool Policies is already one of the strongest cross-feature governance surfaces. |
| Safety & Governance | Approvals | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Approvals is operationally real, but it still needs stronger suite-wide adoption as a first-class exception path. |
| Safety & Governance | Data capture | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Data capture should continue converging with runtime and evidence flows rather than staying privacy-only. |
| Safety & Governance | Security | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | Security is already a strong operational and runtime bridge, especially with monitoring and gateway posture. |
| Safety & Governance | Alert rules | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Alert Rules already tie runtime and monitoring together and should keep growing as the action layer. |
| Safety & Governance | Audit log | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | Audit Log is one of the clearest evidence backbones in the suite. |
| Safety & Governance | Governance pack | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | Governance Pack is strongest when it is clearly downstream of evidence and policy surfaces rather than competing with them. |
| Safety & Governance | Tags | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | Tags is a cross-cutting primitive and should continue to grow as a shared classification layer. |

### 11.7 Build & Improve Cohesion Matrix

This section applies the same matrix structure to `Build & Improve` against the rest of the shipped feature surface.

Current row major feature under audit: `Build & Improve`

### 11.7a Build & Improve x Organization & Access / Gateway & Routing

| Row Major Feature | Row Subfeature | Workspaces | Access groups | API keys | AI hub | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|------------|---------------|----------|--------|-------------------|---------------|------------|----------------|-------------|---------|
| Build & Improve | Playground | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Playground should feel much more like a live gateway-aware experimentation surface over time. |
| Build & Improve | Prompts list | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Prompts already fit the workflow-improvement model, but their gateway/runtime links could be more obvious. |
| Build & Improve | Workflow detail | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Workflow Detail is one of the strongest candidates for tying together scope, execution, and improvement. |
| Build & Improve | Evaluation studio | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Evaluation Studio already acts as an umbrella, but it still needs a clearer cross-feature ownership story. |
| Build & Improve | Experiments | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Experiments are operationally useful, but the relationship to runtime configuration could still be tighter. |
| Build & Improve | Replay lab | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Replay is useful, but still not as cohesive a first-class feature as the rest of the build suite should become. |
| Build & Improve | Optimization opportunities | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Optimization Opportunities is naturally close to gateway behavior and should remain so. |
| Build & Improve | Optimization simulator | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Optimization Simulator is already a strong bridge between runtime and improvement loops. |
| Build & Improve | Model scorecards | `PARTIAL` | `N/A` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Model Scorecards already have strong natural cohesion with AI Hub and provider/model surfaces. |

### 11.7b Build & Improve x FinOps / Observe / Self

| Row Major Feature | Row Subfeature | Budgets | Billing periods | Chargeback | Analytics overview | Runs list | Run detail | Request flow | Request explorer | Model usage | Cost and savings | Playground | Workflows list | Evaluation studio | Optimization opportunities | Optimization simulator | Model scorecards | Finding |
|-------------------|----------------|---------|-----------------|------------|--------------------|-----------|------------|--------------|------------------|-------------|------------------|------------|----------------|-------------------|----------------------------|------------------------|------------------|---------|
| Build & Improve | Playground | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Playground should become a stronger live lab that consumes cost, routing, and runtime insights directly. |
| Build & Improve | Prompt detail and versions | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Prompt versioning is strong on its own, but can still gain richer loop-closure with observability and FinOps. |
| Build & Improve | Workflow detail | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | Workflow Detail is one of the clearest “one brick at a time” cohesion surfaces in the whole suite. |
| Build & Improve | Evaluation studio | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Evaluation Studio is strategically important, but still not as consolidated as it should eventually be. |
| Build & Improve | Experiments | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Experiments should become easier to tie to economics and runtime changes. |
| Build & Improve | Replay lab | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Replay is useful but still feels more adjunct than deeply integrated. |
| Build & Improve | Optimization opportunities | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | Optimization Opportunities is one of the strongest Build & Improve bridges to FinOps and Observe. |
| Build & Improve | Optimization simulator | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | Optimization Simulator is already positioned well as a cross-feature decision tool. |
| Build & Improve | Model scorecards | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Model Scorecards already has one of the clearest internal and cross-feature identities in this family. |

### 11.8 Platform / Utility Cohesion Matrix

This section applies the same matrix structure to `Platform` and the currently minimal `Additional Admin / Utility Routes` surface.

Current row major feature under audit: `Platform / Utility`

### 11.8a Platform / Utility x FinOps / Organization & Access / Self

| Row Major Feature | Row Subfeature | Budgets | Billing periods | Chargeback | Ledger | Organization profile | Onboarding | Workspaces | API keys | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|---------|-----------------|------------|--------|----------------------|------------|------------|----------|-------------------|-------------------|---------|---------|
| Platform / Utility | All organizations | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | All Organizations is the true platform-admin lifecycle owner and should remain the parent to org creation and suspension. |
| Platform / Utility | Platform settings | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | Platform Settings is strategically important as a convergence surface, but is still an umbrella rather than one cohesive product area. |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | Plugins is now correctly collapsed under onboarding/discovery rather than preserved as a first-class admin plane. |

### 11.8b Platform / Utility x Gateway / Observe / Governance / Build

| Row Major Feature | Row Subfeature | Model gateway | Guardrails | Monitoring | Telemetry | Audit log | Governance pack | Evaluation studio | Optimization simulator | Finding |
|-------------------|----------------|---------------|------------|------------|-----------|-----------|-----------------|-------------------|------------------------|---------|
| Platform / Utility | All organizations | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Platform org management should summarize downstream posture, but not absorb each control plane. |
| Platform / Utility | Platform settings | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | Platform Settings is already the clearest home for cross-cutting compliance and operational defaults. |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | Plugins now belong in the guided onboarding and tool-connection story, not in a separate ops island. |
