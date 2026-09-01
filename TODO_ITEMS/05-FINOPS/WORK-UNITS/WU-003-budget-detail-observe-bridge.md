# WU-003: Budget Detail × Observe Surfaces Bridge

- **Status**: COMPLETED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budget detail
- **Created**: 2026-08-14
- **Completed**: 2026-08-31

## Completion Notes

### Backend
- Added `BudgetDetailObservePosture` schema (budget_context, spend_context, user_budget_context, engineering_context)
- Added `GET /analytics/budget-detail-observe-posture` endpoint

### UI
- Workspace Dashboard: Budget Posture card (active budgets, total limit, 30d spend, breach count) with drill-through links
- Analytics Users: Budget & Per-User Attribution card (users with budgets, active users, user budget total/spend)
- User Detail: Budget Context card (active budgets, 30d spend, breach count) with per-user budget drill-through link
- Engineering Dashboard: Budget Signals card (active/feature budgets, total limit, breach count)

### Docs
- Added Budget Detail × Observe Bridge section in budgets.mdx

### Postman
- Added Budget Detail Observe Posture request

### Cohesion
- 4 cells upgraded PARTIAL→STRONG: Budget detail × Workspace dashboard, Analytics users, Analytics user detail, Engineering
- 5 cells verified already STRONG: Analytics overview, Request flow, Request explorer, Model usage, Outcomes and ROI

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budget detail | Observe: Workspace dashboard | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Analytics overview | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Request flow | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Request explorer | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Model usage | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Outcomes and ROI | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Analytics users | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Analytics user detail | 05×03 | GAP | STRONG |
| FinOps: Budget detail | Observe: Engineering | 05×03 | GAP | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budget detail × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Budget detail
- `FEATURE-STATUS.md` — 05-A × 03 GAP counts

## Scope

- **Backend**: Budget detail must become a real page that Observe surfaces can link to and consume. Budget detail should expose: spend breakdown by investigation dimension (request, model, user), budget posture visible from workspace dashboard, budget context on analytics overview, budget impact per request in request flow/explorer, model-level budget utilization for model usage, budget ROI context for outcomes, per-user budget attribution for analytics users, and engineering budget signals.
- **UI**: Budget detail must be linkable from all listed Observe surfaces. Workspace dashboard should show budget posture. Analytics overview should show budget health. Request flow/explorer should link to budget impact. Model usage should show per-model budget utilization. Outcomes/ROI should show budget-relative value. Analytics users should show per-user budget attribution.
- **Docs**: Document budget detail as the central FinOps-to-Observe bridge.
- **Postman**: Add Observe-facing context to budget detail endpoint.
- **Scripts/Examples**: Add example navigating from analytics overview to budget detail and from request flow to budget impact.

## Acceptance Criteria

1. Budget detail is a real page with rich Observe context
2. Workspace dashboard shows budget posture summary
3. Request flow and explorer link to budget impact
4. Model usage shows per-model budget utilization
5. Analytics users show per-user budget attribution
6. Outcomes/ROI shows budget-relative value
7. All listed cohesion cells updated to target state
8. All paired feature files updated
9. FEATURE-STATUS.md dashboard updated
