# WU-001: Budget Control × Org & Access Scope

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budgets, Budget detail, Budget overrides
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budgets | Org: Access groups | 05×01 | GAP | STRONG |
| FinOps: Budgets | Org: API keys | 05×01 | GAP | STRONG |
| FinOps: Budget detail | Org: Organization profile | 05×01 | GAP | STRONG |
| FinOps: Budget detail | Org: Access groups | 05×01 | GAP | STRONG |
| FinOps: Budget detail | Org: API keys | 05×01 | GAP | STRONG |
| FinOps: Budget detail | Org: AI hub | 05×01 | GAP | STRONG |
| FinOps: Budget overrides | Org: Access groups | 05×01 | GAP | STRONG |
| FinOps: Budget overrides | Org: API keys | 05×01 | GAP | STRONG |
| FinOps: Budget overrides | Org: AI hub | 05×01 | GAP | STRONG |
| FinOps: Budgets | Org: Organization profile | 05×01 | PARTIAL | STRONG |
| FinOps: Budgets | Org: Telemetry | 05×01 | PARTIAL | STRONG |
| FinOps: Budgets | Org: AI hub | 05×01 | PARTIAL | STRONG |
| FinOps: Budget detail | Org: Workspaces | 05×01 | PARTIAL | STRONG |
| FinOps: Budget detail | Org: Telemetry | 05×01 | PARTIAL | STRONG |
| FinOps: Budget overrides | Org: Organization profile | 05×01 | PARTIAL | STRONG |
| FinOps: Budget overrides | Org: Workspaces | 05×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budgets/Budget detail/Overrides × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Budget surfaces
- `05-FINOPS/GAP-MATRIX.md` — Budgets, Budget detail, Budget overrides rows
- `FEATURE-STATUS.md` — 05-A × 01 counts

## Scope

- **Backend**: Make access groups and API keys first-class budget scopes. Budget detail must link to org profile rollups, access-group ownership, API-key attribution, and AI hub model catalog context. Overrides must carry access-group and API-key scope when applicable.
- **UI**: Budget creation must support access-group and API-key scope selection. Budget detail must show org profile rollup, access-group ownership, API-key attribution, and AI hub model links. Override creation must support access-group and API-key scoped exceptions.
- **Docs**: Document access-group and API-key budget scoping workflows.
- **Postman**: Add access-group and API-key scope to budget and override endpoints.
- **Scripts/Examples**: Add example creating budgets scoped to access groups and API keys.

## Acceptance Criteria

1. Access groups are first-class budget scopes (create, detail, override)
2. API keys are first-class budget scopes (create, detail, override)
3. Budget detail links to org profile rollups
4. Budget detail shows AI hub model catalog context
5. Overrides carry access-group and API-key scope
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
