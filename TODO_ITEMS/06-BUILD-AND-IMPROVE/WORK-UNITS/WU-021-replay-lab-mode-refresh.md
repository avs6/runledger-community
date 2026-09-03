# WU-021: Replay Lab Mode Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/replay-lab
- **Created**: 2026-08-16
- **Completed**: 2026-09-03

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Replay lab | Gateway: Response cache | 06x02 | STRONG | STRONG |
| Build: Replay lab | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Replay lab | FinOps: Cost and savings | 06x05 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Request flow | 06x03 | PARTIAL | STRONG |
| Build: Replay lab | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |
| Build: Replay lab | Build: Runbooks | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Replay lab row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Replay lab cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Replay Lab as a replay mode inside evaluation with strong runtime and savings evidence.
- **UI**: Tighten alignment between replay routes, replay APIs, and evaluation ownership.
- **Docs**: Describe replay as part of the validation workflow, not a parallel product island.
- **Postman**: Keep replay and evaluation result flows aligned.
- **Scripts/Examples**: Add a replay scenario linking cache effects, runtime evidence, and runbook guidance.

## Acceptance Criteria

1. Replay Lab is re-audited as an evaluation mode
2. Runtime, savings, and runbook relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
