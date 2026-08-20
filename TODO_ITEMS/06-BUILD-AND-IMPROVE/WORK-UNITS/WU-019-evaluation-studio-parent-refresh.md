# WU-019: Evaluation Studio Parent Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/evaluation-studio
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Evaluation studio | Org: Access groups | 06x01 | PARTIAL | STRONG |
| Build: Evaluation studio | Org: API keys | 06x01 | PARTIAL | STRONG |
| Build: Evaluation studio | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Evaluation studio | Gateway: Response cache | 06x02 | PARTIAL | STRONG |
| Build: Evaluation studio | FinOps: Budgets | 06x05 | PARTIAL | STRONG |
| Build: Evaluation studio | Observe: Request flow | 06x03 | PARTIAL | STRONG |
| Build: Evaluation studio | Build: Optimization simulator | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Evaluation studio row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Evaluation studio cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Evaluation Studio as the clear parent owner for datasets, experiments, replay, and result review.
- **UI**: Strengthen unified runtime, scope, and cost context across the studio shell.
- **Docs**: Teach Evaluation Studio as one cohesive validation workflow.
- **Postman**: Keep studio and subdomain flows aligned with parent ownership.
- **Scripts/Examples**: Add a studio-level scenario tying evaluation inputs, runtime evidence, and optimization outputs together.

## Acceptance Criteria

1. Evaluation Studio is re-audited as the umbrella owner
2. Scope, runtime, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
