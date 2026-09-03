# WU-009: Internal Build & Improve Cohesion Tightening

- **Status**: COMPLETED
- **Bundle**: 06-Build & Improve - A/B/C/D
- **Target**: 06-BUILD-AND-IMPROVE/Self
- **Created**: 2026-08-15
- **Completed**: 2026-09-02

## Completion Notes

- Backend: `BuildInternalPosture` Pydantic schema + `GET /analytics/build-internal-posture` endpoint querying AgentRun, Prompt, WorkflowDefinition, WorkflowRun, EvalDataset, EvalExperiment, ReplayDataset, ReplayExperiment, HubModel, ScoreEvent, ProviderCall for cross-surface context
- TypeScript: `BuildInternalPosture` interface + `getBuildInternalPosture` API function
- UI: Rose "Build & Improve Loop" card on all 9 target pages (Playground, Prompt detail, Workflow detail, Evaluation studio, Experiments, Replay lab, Optimization opportunities, Optimization simulator, Model scorecards) showing sibling surface stats with drill-through links
- Docs: Added "Build & Improve Loop" sections to optimization.mdx, optimization-simulator.mdx, model-scorecards.mdx
- Postman: Added "Build Internal Posture" entry
- Example: `examples/138_build_internal_posture.py`
- 44 self-cohesion cells closed (all targeted Build × Build PARTIAL cells in 11.7b → STRONG; 10 remain: 6 diagonal + 4 cross-feature)

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Playground | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Playground | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Playground | Build: Optimization opportunities | 06×06 | PARTIAL | STRONG |
| Build: Playground | Build: Optimization simulator | 06×06 | PARTIAL | STRONG |
| Build: Playground | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Prompt detail | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Prompt detail | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Prompt detail | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Prompt detail | Build: Optimization opportunities | 06×06 | PARTIAL | STRONG |
| Build: Prompt detail | Build: Optimization simulator | 06×06 | PARTIAL | STRONG |
| Build: Prompt detail | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Workflow detail | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Workflow detail | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Workflow detail | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Evaluation studio | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Evaluation studio | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Evaluation studio | Build: Optimization opportunities | 06×06 | PARTIAL | STRONG |
| Build: Evaluation studio | Build: Optimization simulator | 06×06 | PARTIAL | STRONG |
| Build: Evaluation studio | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Experiments | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Experiments | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Experiments | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Experiments | Build: Optimization opportunities | 06×06 | PARTIAL | STRONG |
| Build: Experiments | Build: Optimization simulator | 06×06 | PARTIAL | STRONG |
| Build: Experiments | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Replay lab | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Replay lab | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Replay lab | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Replay lab | Build: Optimization opportunities | 06×06 | PARTIAL | STRONG |
| Build: Replay lab | Build: Optimization simulator | 06×06 | PARTIAL | STRONG |
| Build: Replay lab | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Optimization opportunities | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Optimization opportunities | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Optimization opportunities | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Optimization opportunities | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Optimization simulator | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Optimization simulator | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Optimization simulator | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Optimization simulator | Build: Model scorecards | 06×06 | PARTIAL | STRONG |
| Build: Model scorecards | Build: Playground | 06×06 | PARTIAL | STRONG |
| Build: Model scorecards | Build: Workflows list | 06×06 | PARTIAL | STRONG |
| Build: Model scorecards | Build: Evaluation studio | 06×06 | PARTIAL | STRONG |
| Build: Model scorecards | Build: Optimization opportunities | 06×06 | PARTIAL | STRONG |
| Build: Model scorecards | Build: Optimization simulator | 06×06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — all internal Build × Build cells
- `FEATURE-STATUS.md` — 06-SELF counts

## Scope

- **Backend**: Build surfaces should cross-reference each other as a connected improvement loop. Playground should link to workflows, evaluations, optimization, and scorecards. Prompt detail should connect to playground testing, workflow usage, evaluation results, and optimization impact. Workflow detail should link to playground testing and evaluation results. Evaluation studio should connect to playground, workflows, and optimization. Experiments and replay should link to all other build surfaces. Optimization surfaces should connect to playground, workflows, evaluation, and scorecards bidirectionally.
- **UI**: All Build surfaces should provide contextual navigation to related Build surfaces. Playground should offer pathways to workflows, evaluation, optimization, and scorecards. Prompt detail should show workflow usage, evaluation results, and optimization impact. Evaluation should link to playground testing and optimization follow-up. Optimization should connect to evaluation evidence, playground testing, and scorecard context. Model scorecards should link to all improvement surfaces.
- **Docs**: Document the Build & Improve internal improvement loop and cross-surface navigation.
- **Postman**: Add cross-surface links to build endpoints.
- **Scripts/Examples**: Add example walking through the full build improvement loop: playground → prompt → evaluation → optimization → scorecard.

## Acceptance Criteria

1. All Build surfaces provide contextual navigation to related Build surfaces
2. Playground connects to workflows, evaluation, optimization, and scorecards
3. Prompt detail shows workflow usage, evaluation results, and optimization impact
4. Evaluation connects to playground, workflows, and optimization
5. Optimization connects to evaluation evidence and scorecard context
6. Full improvement loop is navigable end-to-end
7. All listed cohesion cells updated to target state
8. All paired feature files updated
9. FEATURE-STATUS.md dashboard updated
