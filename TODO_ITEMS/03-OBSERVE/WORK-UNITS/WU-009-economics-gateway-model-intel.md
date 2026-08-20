# WU-009: Economics & Model Intelligence Gateway Links

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - C (Economics & Intel)
- **Target**: 03-OBSERVE/Model usage, Analytics economics, Cost and savings, Model scorecards
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Model usage | Gateway: Model gateway | 03×02 | PARTIAL | STRONG |
| Observe: Model usage | Observe: Runs list | 03×03 | PARTIAL | STRONG |
| Observe: Model usage | Observe: Request flow | 03×03 | PARTIAL | STRONG |
| Observe: Model usage | Observe: Request explorer | 03×03 | PARTIAL | STRONG |
| Observe: Model usage | Safety: Tags | 03×04 | PARTIAL | STRONG |
| Observe: Analytics economics | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Analytics economics | Gateway: Model gateway | 03×02 | PARTIAL | STRONG |
| Observe: Analytics economics | Observe: Runs list | 03×03 | PARTIAL | STRONG |
| Observe: Analytics economics | Observe: Request flow | 03×03 | PARTIAL | STRONG |
| Observe: Analytics economics | Observe: Request explorer | 03×03 | PARTIAL | STRONG |
| Observe: Analytics economics | Observe: Monitoring | 03×03 | PARTIAL | STRONG |
| Observe: Cost and savings | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Cost and savings | Gateway: Model gateway | 03×02 | PARTIAL | STRONG |
| Observe: Cost and savings | Observe: Runs list | 03×03 | PARTIAL | STRONG |
| Observe: Cost and savings | Observe: Request flow | 03×03 | PARTIAL | STRONG |
| Observe: Cost and savings | Observe: Request explorer | 03×03 | PARTIAL | STRONG |
| Observe: Cost and savings | Observe: Monitoring | 03×03 | PARTIAL | STRONG |
| Observe: Model scorecards | Org: Workspaces | 03×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Economics/Scorecards × Gateway/Self/Safety/Org cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of economics features
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Model scorecards
- `FEATURE-STATUS.md` — 03-C × 02/03/04 counts

## Scope

- **Backend**: Model usage should integrate gateway route-level breakdown. Economics and cost/savings should show provider-level attribution and link to gateway config. Internal Observe cross-links should be richer: economics should drill into runs and request analysis, model usage should pivot to request flow. Model scorecards should be workspace-aware.
- **UI**: Model usage should show route-level model breakdown with gateway links. Economics and cost/savings should show provider attribution with gateway drill-through. Observe surfaces should cross-link more explicitly to runs and request analysis from economics. Model scorecards should support workspace filtering.
- **Docs**: Document economics-to-gateway and model-intelligence cross-navigation.
- **Postman**: Add gateway context to model usage and economics endpoints.
- **Scripts/Examples**: Add example navigating from model usage through gateway route breakdown into request investigation.

## Acceptance Criteria

1. Model usage shows route-level breakdown with gateway links
2. Economics and cost/savings show provider-level attribution
3. Economics surfaces drill into runs and request analysis
4. Model scorecards support workspace filtering
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
