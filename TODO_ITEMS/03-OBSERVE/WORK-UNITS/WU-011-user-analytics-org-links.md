# WU-011: User Analytics & Overview Org Links

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - A/C (Overview, Economics & Intel)
- **Target**: 03-OBSERVE/Analytics users, Analytics user detail, Analytics overview
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Analytics users | Org: Organization profile | 03×01 | PARTIAL | STRONG |
| Observe: Analytics users | Org: Workspaces | 03×01 | PARTIAL | STRONG |
| Observe: Analytics overview | Observe: Request flow | 03×03 | PARTIAL | STRONG |
| Observe: Analytics overview | Observe: Request explorer | 03×03 | PARTIAL | STRONG |
| Observe: Analytics overview | Observe: Monitoring | 03×03 | PARTIAL | STRONG |
| Observe: Model usage | Org: Workspaces | 03×01 | PARTIAL | STRONG |
| Observe: Model usage | Org: API keys | 03×01 | PARTIAL | STRONG |
| Observe: Model usage | Org: Telemetry | 03×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Analytics users/overview/Model usage × Org/Self cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of these features
- `FEATURE-STATUS.md` — 03-A/C × 01/03 counts

## Scope

- **Backend**: Analytics users should support org-level and workspace-level breakdown. Analytics overview should cross-link more explicitly to request flow, request explorer, and monitoring. Model usage should support workspace, API-key, and telemetry context.
- **UI**: Analytics users should show org-level and workspace-level user activity. Analytics overview should have clearer drill-through to request analysis and monitoring. Model usage should filter by workspace and API key.
- **Docs**: Document user analytics org integration and overview cross-navigation.
- **Postman**: Add org/workspace context to user analytics and model usage endpoints.
- **Scripts/Examples**: Add example viewing user analytics scoped by workspace and navigating from overview into request analysis.

## Acceptance Criteria

1. Analytics users supports org and workspace level breakdown
2. Analytics overview cross-links to request flow, request explorer, and monitoring
3. Model usage filters by workspace and API key
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
