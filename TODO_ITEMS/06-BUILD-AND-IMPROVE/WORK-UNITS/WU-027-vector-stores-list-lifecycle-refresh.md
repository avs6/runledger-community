# WU-027: Vector Stores List Lifecycle Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - B (Managed Execution Assets)
- **Target**: 06-BUILD-AND-IMPROVE/vector-stores-list
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Vector stores list | Org: Workspaces | 06x01 | PARTIAL | STRONG |
| Build: Vector stores list | Observe: Request explorer | 06x03 | PARTIAL | STRONG |
| Build: Vector stores list | FinOps: Chargeback | 06x05 | PARTIAL | STRONG |
| Build: Vector stores list | Build: Workflows list | 06x06 | PARTIAL | STRONG |
| Build: Vector stores list | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |
| Build: Vector stores list | Build: Optimization opportunities | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Vector stores list row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Vector stores list cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Vector Stores List as a managed retrieval asset catalog, not a read-only collection list.
- **UI**: Tighten in-product lifecycle actions and links into workflows, evaluation, and evidence.
- **Docs**: Position vector stores as workflow-quality assets with runtime relevance.
- **Postman**: Keep collection lifecycle flows aligned with retrieval use cases.
- **Scripts/Examples**: Add a retrieval-asset scenario that connects one vector store to workflow and evaluation outcomes.

## Acceptance Criteria

1. Vector Stores List is re-audited as a managed retrieval catalog
2. Workflow, evaluation, and attribution relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
