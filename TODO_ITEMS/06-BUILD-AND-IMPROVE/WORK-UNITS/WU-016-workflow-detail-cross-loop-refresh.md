# WU-016: Workflow Detail Cross Loop Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - B (Managed Execution Assets)
- **Target**: 06-BUILD-AND-IMPROVE/workflow-detail
- **Created**: 2026-08-16
- **Completed**: 2026-09-02

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Workflow detail | Org: Access groups | 06x01 | PARTIAL | STRONG |
| Build: Workflow detail | Org: API keys | 06x01 | PARTIAL | STRONG |
| Build: Workflow detail | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Workflow detail | Gateway: Response cache | 06x02 | PARTIAL | STRONG |
| Build: Workflow detail | Gateway: Rate limits | 06x02 | PARTIAL | STRONG |
| Build: Workflow detail | Observe: Run detail | 06x03 | PARTIAL | STRONG |
| Build: Workflow detail | FinOps: Budget detail | 06x05 | PARTIAL | STRONG |
| Build: Workflow detail | Build: Optimization opportunities | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Workflow detail row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Workflow detail cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Workflow Detail as the central cross-loop execution asset surface.
- **UI**: Strengthen scope, cache, guardrail, rate-limit, and cost drillbacks from workflow detail.
- **Docs**: Explain workflow detail as the main execution-to-improvement junction.
- **Postman**: Keep workflow detail and linked-run/cost flows aligned.
- **Scripts/Examples**: Add a workflow-detail scenario that traces one workflow through runtime, cost, and optimization evidence.

## Acceptance Criteria

1. Workflow Detail is re-audited as a cross-loop asset surface
2. Runtime, scope, and FinOps relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
