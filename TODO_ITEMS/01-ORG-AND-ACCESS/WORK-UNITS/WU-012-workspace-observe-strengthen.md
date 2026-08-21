# WU-012: Workspace Observe Cohesion Strengthening

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/Workspaces (`/workspace`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Workspaces | Observe: Sessions list | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Session detail | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Request flow focus | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Model usage | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Analytics economics | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Cost and savings | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Billing summary | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Outcomes and ROI | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Analytics users | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Analytics user detail | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Engineering | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Monitoring | 01×03 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Budget detail | 01×05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Budget overrides | 01×05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Budget notifications | 01×05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Billing period detail | 01×05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Ledger | 01×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Workspaces × Observe and FinOps cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Workspaces
- `05-FINOPS/COHESION-MATRIX.md` — their view of Workspaces
- `FEATURE-STATUS.md` — 01-B × 03 and 01-B × 05 counts

## Scope

- **Backend**: Strengthen workspace-level scoping in remaining PARTIAL Observe surfaces: sessions, model usage, analytics economics, cost and savings, analytics users, engineering, monitoring. Strengthen workspace scoping in FinOps: budget detail, overrides, notifications, billing period detail, ledger.
- **UI**: Remaining Observe and FinOps surfaces should consistently show workspace context and support workspace-level drill-down where currently partial.
- **Docs**: Ensure workspace-scoped investigation and financial workflows are documented consistently.
- **Postman**: Verify workspace filter coverage across all PARTIAL endpoints.
- **Scripts/Examples**: Add examples exercising workspace-scoped investigation and financial workflows.

## Acceptance Criteria

1. Sessions list/detail fully support workspace scoping
2. Model usage, analytics economics, and cost/savings show workspace-level breakdown
3. Analytics users and engineering surfaces consistently inherit workspace context
4. Budget detail, overrides, notifications, and billing period detail are workspace-aware
5. Ledger compliance surface reflects workspace scope
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
