# WU-005: Evaluation & Replay × Observe Bridge

- **Status**: NOT_STARTED
- **Bundle**: 06-Build & Improve - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/Evaluation studio, Experiments, Replay lab
- **Created**: 2026-08-15
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Evaluation studio | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Evaluation studio | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Evaluation studio | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Evaluation studio | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Evaluation studio | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Evaluation studio | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Evaluation studio | Observe: Cost and savings | 06×03 | PARTIAL | STRONG |
| Build: Experiments | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Experiments | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Experiments | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Experiments | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Experiments | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Experiments | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Experiments | Observe: Cost and savings | 06×03 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Replay lab | Observe: Cost and savings | 06×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Eval studio/Experiments/Replay × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Eval studio/Experiments/Replay
- `FEATURE-STATUS.md` — 06-C × 03 counts

## Scope

- **Backend**: Evaluation studio should consume run, request flow, and cost/savings data for evaluation context. Experiments should link to observable runs and request evidence. Replay should tie directly to source runs, request flows, and model usage for comparison. All three surfaces should consume analytics overview and request explorer data.
- **UI**: Evaluation studio should show run evidence, request flow traces, model usage, and cost impact for evaluated assets. Experiments should display observable run links and performance comparisons. Replay should show side-by-side source vs replay run data with request flow and cost differences. Deep links to all Observe surfaces from evaluation, experiment, and replay views.
- **Docs**: Document the evaluation-to-observe feedback loop and replay evidence integration.
- **Postman**: Add observe context to evaluation, experiment, and replay endpoints.
- **Scripts/Examples**: Add example viewing experiment results with run evidence and cost impact overlay.

## Acceptance Criteria

1. Evaluation studio shows run evidence, request flows, and cost impact
2. Experiments link to observable runs and performance data
3. Replay shows source vs replay comparison with observe evidence
4. Deep links to Observe surfaces from all evaluation/experiment/replay views
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
