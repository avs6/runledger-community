# WU-007: Billing × Org Access-Group Scope

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - B (Billing & Reconciliation)
- **Target**: 05-FINOPS/Billing periods, Billing period detail
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Billing periods | Org: Access groups | 05×01 | GAP | STRONG |
| FinOps: Billing period detail | Org: Access groups | 05×01 | GAP | STRONG |
| FinOps: Billing periods | Org: Organization profile | 05×01 | PARTIAL | STRONG |
| FinOps: Billing periods | Org: API keys | 05×01 | PARTIAL | STRONG |
| FinOps: Billing periods | Org: Telemetry | 05×01 | PARTIAL | STRONG |
| FinOps: Billing periods | Org: AI hub | 05×01 | PARTIAL | STRONG |
| FinOps: Billing period detail | Org: Organization profile | 05×01 | PARTIAL | STRONG |
| FinOps: Billing period detail | Org: API keys | 05×01 | PARTIAL | STRONG |
| FinOps: Billing period detail | Org: Telemetry | 05×01 | PARTIAL | STRONG |
| FinOps: Billing period detail | Org: AI hub | 05×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Billing × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Billing surfaces
- `FEATURE-STATUS.md` — 05-B × 01 counts

## Scope

- **Backend**: Billing periods and period detail should support access-group-level breakdowns and attribution. API-key billing attribution should be visible. Org profile should show billing posture. AI hub should show model-level billing context.
- **UI**: Billing period detail should show access-group breakdown. Billing list should show org profile context. Period detail should show API-key attribution where applicable. AI hub billing context should be visible.
- **Docs**: Document access-group-scoped billing workflows.
- **Postman**: Add access-group and API-key context to billing endpoints.
- **Scripts/Examples**: Add example viewing billing period with access-group breakdown.

## Acceptance Criteria

1. Billing period detail shows access-group breakdown
2. API-key billing attribution visible in period detail
3. Org profile shows billing posture summary
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
