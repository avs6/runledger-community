# Organization & Access — Delivery Status

Last updated: 2026-08-16

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
| 1.8 | Onboarding and product tour | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `N/A` | `N/A` | Onboarding now owns the primary setup/discovery story for Claude, Codex, MCP, telemetry, and existing-stack guidance, but it remains a guide surface rather than a managed CRUD domain. |

## Recent Re-Audit Delta

- `2026-08-16` — Organization Console now ships a real read-only FinOps posture layer. `/organization` summarizes cross-workspace spend, budget/override/notification coverage, overdue billing, chargeback readiness, and ledger readiness through `GET /org/finance`, then hands operators into Budgets, Billing, Chargeback, and Compliance.
- `2026-08-16` — Access groups now ship as first-class financial scopes across Budgets, Billing, and Chargeback. The access-groups dashboard deep-links into scoped financial views, and the supporting docs/Postman/example surfaces were refreshed to match.
- `2026-08-16` — Access groups now also ship as first-class Observe investigation scopes. `/access-groups` deep-links into scoped Analytics Overview, Runs, Request Flow, and Request Explorer, and the supporting backend/UI/docs/Postman/example/smoke surfaces now preserve `access_group_id`.
- `2026-08-16` — API keys now ship as first-class budget owners across Budgets, Billing, and Chargeback. The API-key detail page drills into scoped financial posture, and the supporting docs/Postman/smoke/example surfaces were refreshed to match.
