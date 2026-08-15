# WU-009: Budget Control × Observe PARTIAL Strengthening

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budgets, Budget overrides, Budget notifications
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budgets | Observe: Workspace dashboard | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Analytics overview | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Runs list | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Run detail | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Request flow | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Request explorer | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Model usage | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Billing summary | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Outcomes and ROI | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Analytics users | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Analytics user detail | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Engineering | 05×03 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Monitoring | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Workspace dashboard | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Analytics overview | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Runs list | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Run detail | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Request flow | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Request explorer | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Model usage | 05×03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Monitoring | 05×03 | PARTIAL | STRONG |
| FinOps: Budget notifications | Observe: Workspace dashboard | 05×03 | PARTIAL | STRONG |
| FinOps: Budget notifications | Observe: Analytics overview | 05×03 | PARTIAL | STRONG |
| FinOps: Budget notifications | Observe: Monitoring | 05×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budgets/Overrides/Notifications × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Budgets/Overrides/Notifications
- `FEATURE-STATUS.md` — 05-A × 03 PARTIAL counts

## Scope

- **Backend**: Budget posture (active budgets, utilization, at-risk, breached) should be consumable by Observe surfaces. Override status should be visible in investigation context. Budget notification events should appear in monitoring. Budget policy should be the source of truth for spend governance in analytics and investigation views.
- **UI**: Workspace dashboard, analytics overview, and monitoring should show budget posture signals. Investigation surfaces (runs, request flow, request explorer) should show budget status context. Override status should be visible when investigating spend anomalies. Budget notifications should be visible in monitoring.
- **Docs**: Document budget posture visibility across Observe surfaces.
- **Postman**: Add budget posture to Observe-facing endpoints.
- **Scripts/Examples**: Add example viewing budget posture from workspace dashboard and investigating overrides from request flow.

## Acceptance Criteria

1. Observe surfaces show budget posture (utilization, at-risk, breached)
2. Investigation surfaces show override status context
3. Monitoring shows budget notification events
4. Budget policy is the spend governance source of truth for analytics
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
