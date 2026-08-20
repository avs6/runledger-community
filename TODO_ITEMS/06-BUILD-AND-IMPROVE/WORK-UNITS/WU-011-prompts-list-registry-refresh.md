# WU-011: Prompts List Registry Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - A (Interactive Build Surfaces)
- **Target**: 06-BUILD-AND-IMPROVE/prompts-list
- **Created**: 2026-08-16
- **Completed**:

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
