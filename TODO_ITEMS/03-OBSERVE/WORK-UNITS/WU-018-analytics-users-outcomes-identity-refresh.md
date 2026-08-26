# WU-018: Analytics Users Outcomes and Identity Refresh

- **Status**: COMPLETED
- **Bundle**: 03-Observe - Bundle C (Economics, Model Intelligence, and Outcomes)
- **Target**: 03-OBSERVE/Analytics users + Outcomes (`/analytics/users`, `/outcomes`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-25

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Analytics users | Org: Workspaces | PARTIAL | PARTIAL | STRONG |
| Observe: Analytics users | Org: API keys | N/A | PARTIAL | STRONG |
| Observe: Analytics users | Gateway: Model gateway | PARTIAL | PARTIAL | STRONG |
| Observe: Outcomes and ROI | FinOps: Budgets | PARTIAL | PARTIAL | STRONG |
| Observe: Outcomes and ROI | FinOps: Budget detail | PARTIAL | PARTIAL | STRONG |
| Observe: Outcomes and ROI | Org: Workspaces | PARTIAL | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Analytics users / Outcomes rows
- `03-OBSERVE/COHESION-MATRIX.md` — user-analytics and outcomes cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Analytics users / Outcomes
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Analytics users
- `05-FINOPS/COHESION-MATRIX.md` — their view of Outcomes and ROI
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.10 / 3.19 if delivery surfaces change

## Scope

- **Backend**: Strengthen user and outcome attribution to workspace, API-key, route, and budget context.
- **UI**: Make user analytics and outcomes better at explaining cost-per-user and cost-per-value through real scope lineage.
- **Docs**: Clarify how user analytics and ROI connect to identity and spend posture.
- **Postman**: Add any missing analytics-user or outcomes drillback requests.
- **Scripts/Examples**: Add a user-to-outcome investigation example.

## Acceptance Criteria

1. User analytics and outcomes can be interpreted through real identity, workspace, route, and budget context.
2. Operators can move from user/outcome signals into the right runtime and FinOps owner surfaces.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
