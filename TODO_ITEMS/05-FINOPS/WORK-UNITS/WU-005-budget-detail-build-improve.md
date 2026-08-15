# WU-005: Budget Detail × Build & Improve Surfaces

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budget detail
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budget detail | Build: Playground | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Prompts list | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Prompt detail | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Agents list | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Agent detail | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Workflows list | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Workflow detail | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Eval studio | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Experiments | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Replay lab | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Replay experiment detail | 05×06 | GAP | STRONG |
| FinOps: Budget detail | Build: Model scorecards | 05×06 | GAP | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budget detail × Build cells
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Budget detail
- `FEATURE-STATUS.md` — 05-A × 06 counts

## Scope

- **Backend**: Budget detail must expose build-surface-relevant cost context: per-playground-session cost, per-prompt cost attribution, per-agent cost, per-workflow cost, evaluation and experiment cost, replay cost, and model scorecard budget alignment. Build surfaces should be able to query applicable budget status.
- **UI**: Budget detail must be linkable from all Build surfaces. Playground should show session budget impact. Prompt detail should show prompt cost against budget. Agent and workflow detail should show cost against budget. Eval studio, experiments, and replay should show experiment cost against budget. Model scorecards should show budget alignment.
- **Docs**: Document the FinOps-to-Build feedback loop.
- **Postman**: Add Build cost context to budget detail endpoint.
- **Scripts/Examples**: Add example viewing budget impact from playground and workflow perspectives.

## Acceptance Criteria

1. Budget detail shows Build-surface cost attribution
2. Playground shows session budget impact
3. Agent and workflow detail show cost against budget
4. Eval and experiment surfaces show cost against budget
5. Model scorecards show budget alignment
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
