# WU-026: Model Scorecards Intelligence Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - D (Optimization and Decision Support)
- **Target**: 06-BUILD-AND-IMPROVE/model-scorecards
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Model scorecards | Org: AI hub | 06x01 | PARTIAL | STRONG |
| Build: Model scorecards | Gateway: Provider profiles | 06x02 | PARTIAL | STRONG |
| Build: Model scorecards | Gateway: Model gateway | 06x02 | PARTIAL | STRONG |
| Build: Model scorecards | FinOps: Chargeback | 06x05 | PARTIAL | STRONG |
| Build: Model scorecards | Observe: Model usage | 06x03 | PARTIAL | STRONG |
| Build: Model scorecards | Build: Optimization opportunities | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Model scorecards row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Model scorecards cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Model Scorecards as the intelligence layer feeding routing and optimization decisions.
- **UI**: Tighten links into provider catalogs, runtime posture, and cost ownership.
- **Docs**: Position scorecards as decision support, not only model reporting.
- **Postman**: Keep scorecard and linked-intelligence flows aligned.
- **Scripts/Examples**: Add a scorecard scenario that connects model evidence to optimization and routing changes.

## Acceptance Criteria

1. Model Scorecards are re-audited as model-intelligence surfaces
2. Routing, model-usage, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
