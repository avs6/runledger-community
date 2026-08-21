# Organization & Access — Delivery Status

Last updated: 2026-08-20

---

## Audited Overrides

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 1.1 | Platform bootstrap | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 1.2 | Organizations and tenants | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Reflects `/organizations` plus the completed Organization Console flow at `/organization`. |
| 1.3 | Workspaces | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `OK` | `N/A` | `N/A` | End-to-end CRUD is complete; examples are indirect rather than a dedicated workspace-only sample. |
| 1.4 | Users and memberships | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Backed by the completed org/access audit and the shared access-foundation smoke coverage. |
| 1.5 | API keys | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | As of Sunday, August 16, 2026, API keys are not only complete CRUD entities but also first-class FinOps owners: `/api-keys/{key_id}` exposes scoped budget assignment and spend attribution, while the supporting billing and chargeback paths now accept `api_key_id` for owner-specific evidence. |
| 1.6 | RBAC and role-aware access | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Docs and UI behavior are aligned; examples remain indirect. |
| 1.7 | Platform settings | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Strong sub-surfaces exist, but `/settings` remains an umbrella route rather than one finished feature. |
| 1.8 | Onboarding and product tour | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | Onboarding now ships a 19-step readiness model covering Foundation, FinOps, Gateway, Observe, and Safety with live boolean checks and set-up-now links. Backend returns structured readiness JSON. Docs, Postman, and example updated. README remains PARTIAL. |

## Recent Re-Audit Delta

- `2026-08-16` — Organization Console now ships a real read-only FinOps posture layer. `/organization` summarizes cross-workspace spend, budget/override/notification coverage, overdue billing, chargeback readiness, and ledger readiness through `GET /org/finance`, then hands operators into Budgets, Billing, Chargeback, and Compliance.
- `2026-08-16` — Access groups now ship as first-class financial scopes across Budgets, Billing, and Chargeback. The access-groups dashboard deep-links into scoped financial views, and the supporting docs/Postman/example surfaces were refreshed to match.
- `2026-08-16` — Access groups now also ship as first-class Observe investigation scopes. `/access-groups` deep-links into scoped Analytics Overview, Runs, Request Flow, and Request Explorer, and the supporting backend/UI/docs/Postman/example/smoke surfaces now preserve `access_group_id`.
- `2026-08-16` — API keys now ship as first-class budget owners across Budgets, Billing, and Chargeback. The API-key detail page drills into scoped financial posture, and the supporting docs/Postman/smoke/example surfaces were refreshed to match.
- `2026-08-20` — WU-006 Identity & Scope in Safety & Governance: Users, Access groups, and API keys now have STRONG cohesion with Safety & Governance surfaces. Approvals, audit log, and governance pack accept identity filters (requested_by, access_group_id, api_key_prefix, user_id, api_key_id). User detail shows governance footprint and cross-links. Access group and API key detail pages link to filtered Approvals, Audit Log, and Governance Pack. New GET /users/{user_id}/governance endpoint. Docs, Postman, and example updated.
- `2026-08-20` — WU-007 Identity & Scope in Build & Improve: Access groups and API keys now have STRONG cohesion with 22 Build & Improve surfaces. Agents, workflows, evaluations, experiments, replay, optimization, playground, and model scorecards accept access_group_id and/or api_key_id filters. WorkflowRun carries api_key_id and access_group_id via migration 085. Access group and API key detail pages link to filtered Build surfaces. Docs, Postman, and example updated.
- `2026-08-20` — WU-008 Org Profile Observe & Gateway Posture Rollups: Organization Console now includes read-only Runtime Posture (GET /org/runtime: routes, providers, policies, guardrails, rate limits) and Observability Posture (GET /org/observe: 30d runs, requests, models, errors, alert rules) rollups with per-workspace breakdowns and drill-through links to owning surfaces. 20 cohesion cells closed to STRONG across Observe and Gateway families. Docs, Postman, and example updated.
- `2026-08-20` — WU-009 Onboarding Setup Completeness: Onboarding now ships a 19-step readiness model (was 7) covering Foundation, FinOps (budget notifications, billing periods), Gateway (provider profiles, guardrails, rate limits), Observe (dashboard, analytics, monitoring links), and Safety (MCP servers, search tools, tool policies, approvals, data capture, security, tags). GET /settings/onboarding-status returns 19 boolean checks with completion stats. UI adds four new sections with set-up-now links to owning surfaces. 19 cohesion cells closed to STRONG across FinOps, Gateway, Observe, and Safety families. Docs, Postman, and example updated.
