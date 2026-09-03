# WU-022: Replay Result Analysis Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/replay-experiment-detail
- **Created**: 2026-08-16
- **Completed**: 2026-09-03

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Replay experiment detail | Gateway: Response cache | 06x02 | STRONG | STRONG |
| Build: Replay experiment detail | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Replay experiment detail | Gateway: Model gateway | 06x02 | PARTIAL | STRONG |
| Build: Replay experiment detail | FinOps: Cost and savings | 06x05 | PARTIAL | STRONG |
| Build: Replay experiment detail | Observe: Run detail | 06x03 | PARTIAL | STRONG |
| Build: Replay experiment detail | Build: Optimization simulator | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Replay experiment detail row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Replay experiment detail cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Replay Result Detail as the analyzed output surface for runtime change decisions.
- **UI**: Strengthen route recommendation, cost delta, and runtime evidence interpretation.
- **Docs**: Position replay result analysis as downstream decision support inside evaluation.
- **Postman**: Keep replay-result and route-recommendation flows aligned.
- **Scripts/Examples**: Add a replay-result scenario that links analysis to optimization and gateway follow-through.

## Acceptance Criteria

1. Replay Result Detail is re-audited as a decision-analysis surface
2. Runtime, cache, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
