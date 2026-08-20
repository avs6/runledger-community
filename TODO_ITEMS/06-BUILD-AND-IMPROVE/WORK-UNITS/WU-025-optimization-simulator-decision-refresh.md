# WU-025: Optimization Simulator Decision Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - D (Optimization and Decision Support)
- **Target**: 06-BUILD-AND-IMPROVE/optimization-simulator
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Optimization simulator | Gateway: Provider profiles | 06x02 | STRONG | STRONG |
| Build: Optimization simulator | Gateway: Response cache | 06x02 | STRONG | STRONG |
| Build: Optimization simulator | FinOps: Budgets | 06x05 | PARTIAL | STRONG |
| Build: Optimization simulator | FinOps: Cost and savings | 06x05 | PARTIAL | STRONG |
| Build: Optimization simulator | Observe: Model usage | 06x03 | PARTIAL | STRONG |
| Build: Optimization simulator | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Optimization simulator row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Optimization simulator cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Optimization Simulator as the what-if decision layer over runtime and cost telemetry.
- **UI**: Tighten decision handoff into gateway, evaluation, and build asset changes.
- **Docs**: Explain simulator output as decision support with concrete follow-through.
- **Postman**: Keep simulation and linked-action flows aligned.
- **Scripts/Examples**: Add a simulation scenario that ties provider/cache tradeoffs to evaluation and budget outcomes.

## Acceptance Criteria

1. Optimization Simulator is re-audited as a decision-support surface
2. Runtime, cost, and evaluation relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
