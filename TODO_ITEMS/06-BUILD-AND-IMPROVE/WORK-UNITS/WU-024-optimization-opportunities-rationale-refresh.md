# WU-024: Optimization Opportunities Rationale Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - D (Optimization and Decision Support)
- **Target**: 06-BUILD-AND-IMPROVE/optimization-opportunities
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Optimization opportunities | Gateway: Response cache | 06x02 | STRONG | STRONG |
| Build: Optimization opportunities | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Optimization opportunities | FinOps: Budgets | 06x05 | PARTIAL | STRONG |
| Build: Optimization opportunities | FinOps: Chargeback | 06x05 | PARTIAL | STRONG |
| Build: Optimization opportunities | Observe: Model usage | 06x03 | PARTIAL | STRONG |
| Build: Optimization opportunities | Build: Model scorecards | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Optimization opportunities row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Optimization opportunities cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Optimization Opportunities as an evidence-backed recommendation intake layer.
- **UI**: Strengthen rationale, source evidence, and action handoffs across runtime, scorecards, and spend.
- **Docs**: Position recommendations as evidence-based decisions, not only heuristics.
- **Postman**: Keep recommendation and linked-source flows aligned.
- **Scripts/Examples**: Add an optimization-recommendation scenario tracing evidence, savings, and follow-through.

## Acceptance Criteria

1. Optimization Opportunities are re-audited as rationale-backed recommendations
2. Runtime, scorecard, and FinOps relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
