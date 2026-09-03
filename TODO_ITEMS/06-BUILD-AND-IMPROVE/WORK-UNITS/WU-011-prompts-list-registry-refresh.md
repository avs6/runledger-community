# WU-011: Prompts List Registry Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - A (Interactive Build Surfaces)
- **Target**: 06-BUILD-AND-IMPROVE/prompts-list
- **Created**: 2026-08-16
- **Completed**: 2026-09-02

## Completion Notes

- Backend: `PromptsListObservePosture` schema + `GET /analytics/prompts-list-observe-posture` endpoint querying AgentRun, ProviderCall, EvalDataset, EvalExperiment for observe + eval context
- TypeScript: `PromptsListObservePosture` interface + `getPromptsListObservePosture` API function
- UI: Cyan "Observe & Analytics Context" card + rose "Build & Improve Loop" card (reusing `build-internal-posture`) on Prompts list page with drill-through to Analytics Overview, Runs, Model Usage, Cost & Savings, Evaluation Studio, Workflows, Replay Lab, Optimization
- Docs: Added "Observe & Analytics Context (Prompts List)" section to prompts.mdx
- Postman: Added "Prompts List Observe Posture" entry
- Example: `examples/139_prompts_list_observe_posture.py`
- Pre-closed cells: Workspaces, AI hub, Provider profiles, Model gateway (WU-001), Budgets (05-FINOPS). New cells closed: Analytics overview P→S, Evaluation studio P→S

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Prompts list | Org: Workspaces | 06x01 | PARTIAL | STRONG |
| Build: Prompts list | Org: AI hub | 06x01 | PARTIAL | STRONG |
| Build: Prompts list | Gateway: Provider profiles | 06x02 | PARTIAL | STRONG |
| Build: Prompts list | Gateway: Model gateway | 06x02 | PARTIAL | STRONG |
| Build: Prompts list | FinOps: Budgets | 06x05 | PARTIAL | STRONG |
| Build: Prompts list | Observe: Analytics overview | 06x03 | PARTIAL | STRONG |
| Build: Prompts list | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Prompts list row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Prompts list cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Prompts List as the workspace-scoped prompt registry with real runtime and catalog adjacency.
- **UI**: Make model, provider, and evaluation context more explicit from the list surface.
- **Docs**: Position prompt registry as a cross-loop asset owner, not a standalone library.
- **Postman**: Keep prompt list and lifecycle flows aligned with runtime and evaluation usage.
- **Scripts/Examples**: Add a prompt-registry scenario linking prompt selection to evaluation and optimization loops.

## Acceptance Criteria

1. Prompts List is re-audited as a managed registry surface
2. Model, provider, evaluation, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
