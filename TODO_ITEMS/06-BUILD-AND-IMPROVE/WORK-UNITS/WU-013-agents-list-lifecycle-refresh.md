# WU-013: Agents List Lifecycle Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - B (Managed Execution Assets)
- **Target**: 06-BUILD-AND-IMPROVE/agents-list
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Agents list | Org: Workspaces | 06x01 | PARTIAL | STRONG |
| Build: Agents list | Org: AI hub | 06x01 | PARTIAL | STRONG |
| Build: Agents list | Gateway: Provider profiles | 06x02 | PARTIAL | STRONG |
| Build: Agents list | Gateway: Model gateway | 06x02 | PARTIAL | STRONG |
| Build: Agents list | Observe: Runs list | 06x03 | PARTIAL | STRONG |
| Build: Agents list | FinOps: Chargeback | 06x05 | PARTIAL | STRONG |
| Build: Agents list | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Agents list row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Agents list cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Agents List as the managed agent registry, not an API-only directory.
- **UI**: Strengthen create/update/retire expectations and runtime context from the list view.
- **Docs**: Position agent registry as a full asset-management entry surface.
- **Postman**: Keep agent lifecycle and linked-run flows aligned.
- **Scripts/Examples**: Add an agent-registry scenario that connects list ownership to runtime, evaluation, and cost review.

## Acceptance Criteria

1. Agents List is re-audited as a managed asset surface
2. Runtime, evaluation, and attribution relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
