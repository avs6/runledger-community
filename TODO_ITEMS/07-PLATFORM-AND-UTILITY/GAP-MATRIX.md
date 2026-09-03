# Platform & Utility — GAP Matrix

Last updated: 2026-09-03

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
| All organizations | `/organizations` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | Keep separate. | P7 | `COMPLETED` | `1.2`, `1.7` | WU-001 completes the platform lifecycle hub. Backend: `GET /analytics/platform-lifecycle-posture` (platform admin) returns cross-org FinOps (billing periods, chargeback, ledger), gateway (routes, providers, guardrails), governance (audit events, tool policies, alert rules), and org access (workspaces, API keys, users). UI now shows 5 posture cards (Budget Control, FinOps Lifecycle, Gateway Readiness, Governance & Audit, Org & Access Lifecycle) with drill-through to all owning surfaces. Docs expanded with posture card documentation and lifecycle boundaries. Postman has Platform Lifecycle Posture request. Example 157 and smoke script added. Cohesion remains PARTIAL for a few observe/build cells (Monitoring, Telemetry, Evaluation studio, Optimization simulator) — targeted by WU-005. |
| Platform settings | `/settings` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | Make this the single home for `Ledger`, `Retention`, `Backup`, and ops/compliance surfaces. | P7 | `COMPLETED` | `1.7`, `7.7`, `9.3`, `9.4`, `9.5`, `9.11`, `9.12`, `9.13`, `9.14` | WU-002 converges platform settings with telemetry and audit posture. Backend: `GET /analytics/platform-settings-convergence-posture` (platform admin) returns telemetry (OTLP batches/spans 7d, capture policies), audit (audit/security events 7d), compliance (ledger snapshots/closures), and ops (alert rules/firings 7d). UI adds Telemetry & Capture Convergence card (cyan) and Audit & Compliance Convergence card (amber). Docs: unified `platform-settings.mdx` documents all tabs, posture cards, endpoint, and ownership boundaries. Scripts/Examples now include convergence posture smoke test and httpx example. Postman has Platform Settings Convergence Posture request. Cohesion remains PARTIAL for some observe/build cells. |

---

## Additional Admin / Utility Routes

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Plugins | `/plugins` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | Collapse into `Onboarding`; do not keep a redirect-only top-level route. | P1 | `COMPLETED` | `8.6` | WU-003 completes collapsed ownership model. Backend: full CRUD (create/list/get/update/deactivate) plus execution log and seed-defaults at `/plugins`, actively used by MCP tool governance. UI: intentional redirect to `/onboarding?section=connections`. Docs: `plugins.mdx` documents collapsed ownership model, backend API, and lifecycle boundaries (Onboarding owns discovery, Evaluation studio consumes connections). Postman: Plugins folder with 7 requests (Create, List, Get, Update, Deactivate, Executions, Seed Defaults). Example 159 covers full plugin lifecycle. Cohesion: Evaluation studio P→S. |
