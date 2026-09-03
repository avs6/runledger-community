# WU-020: Experiments Comparison Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/experiments
- **Created**: 2026-08-16
- **Completed**: 2026-09-03

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Experiments | Org: API keys | 06x01 | PARTIAL | STRONG |
| Build: Experiments | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Experiments | Gateway: Response cache | 06x02 | PARTIAL | STRONG |
| Build: Experiments | FinOps: Billing periods | 06x05 | PARTIAL | STRONG |
| Build: Experiments | Observe: Run detail | 06x03 | PARTIAL | STRONG |
| Build: Experiments | Build: Replay lab | 06x06 | PARTIAL | STRONG |
| Build: Experiments | Build: Optimization opportunities | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Experiments row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Experiments cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Experiments as comparison and evaluation runs with stronger runtime and cost linkage.
- **UI**: Tighten update/edit expectations and links into replay and optimization.
- **Docs**: Position experiments as part of one evidence-backed improvement loop.
- **Postman**: Keep experiment lifecycle and result flows aligned with the studio model.
- **Scripts/Examples**: Add an experiment scenario linking evaluation outcomes to replay and optimization follow-up.

## Acceptance Criteria

1. Experiments are re-audited as comparison and evaluation surfaces
2. Runtime, replay, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
