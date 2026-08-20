# WU-010: Playground Live Lab Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - A (Interactive Build Surfaces)
- **Target**: 06-BUILD-AND-IMPROVE/playground
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Playground | Org: Workspaces | 06x01 | PARTIAL | STRONG |
| Build: Playground | Org: API keys | 06x01 | PARTIAL | STRONG |
| Build: Playground | Gateway: Provider profiles | 06x02 | PARTIAL | STRONG |
| Build: Playground | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Playground | Gateway: Response cache | 06x02 | PARTIAL | STRONG |
| Build: Playground | FinOps: Budgets | 06x05 | PARTIAL | STRONG |
| Build: Playground | Observe: Run detail | 06x03 | PARTIAL | STRONG |
| Build: Playground | Observe: Request explorer | 06x03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Playground row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Playground cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Playground as the live builder lab over real runtime, not stub-style request history.
- **UI**: Strengthen scope, provider, cache, guardrail, and cost context inside the interactive lab flow.
- **Docs**: Position Playground as the main live test surface for builders.
- **Postman**: Keep interactive session and request flows aligned with the real lab story.
- **Scripts/Examples**: Add a builder-lab scenario that traces prompt/model iteration into runtime and cost evidence.

## Acceptance Criteria

1. Playground is re-audited as a real interactive build surface
2. Scope, runtime, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
