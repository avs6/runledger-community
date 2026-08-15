# WU-008: Build × FinOps Strengthening

- **Status**: NOT_STARTED
- **Bundle**: 06-Build & Improve - A/C/D
- **Target**: 06-BUILD-AND-IMPROVE/Playground, Prompt detail, Evaluation studio, Experiments, Replay lab, Optimization opportunities, Optimization simulator, Model scorecards
- **Created**: 2026-08-15
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Playground | FinOps: Budgets | 06×05 | PARTIAL | STRONG |
| Build: Prompt detail | FinOps: Budgets | 06×05 | PARTIAL | STRONG |
| Build: Evaluation studio | FinOps: Budgets | 06×05 | PARTIAL | STRONG |
| Build: Experiments | FinOps: Budgets | 06×05 | PARTIAL | STRONG |
| Build: Replay lab | FinOps: Budgets | 06×05 | PARTIAL | STRONG |
| Build: Optimization opportunities | FinOps: Billing periods | 06×05 | PARTIAL | STRONG |
| Build: Optimization opportunities | FinOps: Chargeback | 06×05 | PARTIAL | STRONG |
| Build: Optimization simulator | FinOps: Billing periods | 06×05 | PARTIAL | STRONG |
| Build: Optimization simulator | FinOps: Chargeback | 06×05 | PARTIAL | STRONG |
| Build: Model scorecards | FinOps: Budgets | 06×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Build surfaces × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Build surfaces
- `FEATURE-STATUS.md` — 06-A/C/D × 05 counts

## Scope

- **Backend**: Build surfaces (playground, prompts, evaluation, experiments, replay) should consume budget posture and warn on approach to limits. Optimization surfaces should integrate billing period and chargeback context for cost-aware recommendations. Model scorecards should show budget impact by model.
- **UI**: Playground, prompt detail, evaluation, experiments, and replay should show applicable budget posture and limit warnings. Optimization opportunities should display billing period cost impact and chargeback attribution. Optimization simulator should show billing and chargeback context for simulated scenarios. Model scorecards should show per-model budget impact.
- **Docs**: Document the FinOps feedback loop into Build surfaces and optimization cost-awareness.
- **Postman**: Add budget and billing context to build surface endpoints.
- **Scripts/Examples**: Add example viewing playground session with budget warnings and optimization recommendation with billing context.

## Acceptance Criteria

1. Build surfaces show applicable budget posture and limit warnings
2. Optimization surfaces integrate billing period and chargeback context
3. Model scorecards show per-model budget impact
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
