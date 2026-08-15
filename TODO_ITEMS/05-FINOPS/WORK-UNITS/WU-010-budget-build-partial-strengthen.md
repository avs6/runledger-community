# WU-010: Budget Control × Build & Improve PARTIAL Strengthening

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budgets, Budget overrides, Budget notifications
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budgets | Build: Playground | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Prompts list | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Prompt detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Agents list | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Agent detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Workflows list | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Workflow detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Workflow run detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Eval studio | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Experiments | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Replay lab | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Replay experiment detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Model scorecards | 05×06 | PARTIAL | STRONG |
| FinOps: Budgets | Build: Runbooks | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Playground | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Prompts list | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Prompt detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Agents list | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Agent detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Workflows list | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Workflow detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Workflow run detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Eval studio | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Experiments | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Replay lab | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Replay experiment detail | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Model scorecards | 05×06 | PARTIAL | STRONG |
| FinOps: Budget overrides | Build: Runbooks | 05×06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budgets/Overrides × Build cells
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Budgets/Overrides
- `FEATURE-STATUS.md` — 05-A × 06 PARTIAL counts

## Scope

- **Backend**: Budget posture should be consumable by Build surfaces: applicable budget on playground sessions, prompt evaluations, agent runs, workflow executions, experiments, and replays. Override status should be visible as engineering context. Build surfaces should warn when approaching budget limits.
- **UI**: Build surfaces should show applicable budget posture and warn on approach to limits. Playground should show session budget context. Workflow and agent detail should show cost against budget. Evaluation and experiment surfaces should show budget impact. Override exceptions should be visible as engineering context in Build surfaces.
- **Docs**: Document the FinOps feedback loop into Build surfaces.
- **Postman**: Add budget posture to Build-facing endpoints.
- **Scripts/Examples**: Add example viewing budget warnings in playground and workflow contexts.

## Acceptance Criteria

1. Build surfaces show applicable budget posture
2. Budget warnings appear when approaching limits
3. Override context visible in Build surfaces
4. Playground, workflow, agent, and evaluation surfaces show cost against budget
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
