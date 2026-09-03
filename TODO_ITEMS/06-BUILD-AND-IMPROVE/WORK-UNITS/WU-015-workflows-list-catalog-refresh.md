# WU-015: Workflows List Catalog Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - B (Managed Execution Assets)
- **Target**: 06-BUILD-AND-IMPROVE/workflows-list
- **Created**: 2026-08-16
- **Completed**: 2026-09-02

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Workflows list | Org: Workspaces | 06x01 | PARTIAL | STRONG |
| Build: Workflows list | Org: AI hub | 06x01 | PARTIAL | STRONG |
| Build: Workflows list | Gateway: Provider profiles | 06x02 | PARTIAL | STRONG |
| Build: Workflows list | Gateway: Model gateway | 06x02 | PARTIAL | STRONG |
| Build: Workflows list | FinOps: Budgets | 06x05 | PARTIAL | STRONG |
| Build: Workflows list | Observe: Analytics overview | 06x03 | PARTIAL | STRONG |
| Build: Workflows list | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Workflows list row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Workflows list cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Workflows List as the managed workflow catalog, not an API-only launcher.
- **UI**: Strengthen workflow create/update/archive expectations and visible runtime/cost context.
- **Docs**: Position workflow catalog as a core build surface.
- **Postman**: Keep workflow lifecycle and linked-cost flows aligned.
- **Scripts/Examples**: Add a workflow-catalog scenario that links definitions to runtime, evaluation, and budget posture.

## Acceptance Criteria

1. Workflows List is re-audited as a managed execution catalog
2. Runtime, evaluation, and budget relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
