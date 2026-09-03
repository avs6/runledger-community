# WU-017: Workflow Run Evidence Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - B (Managed Execution Assets)
- **Target**: 06-BUILD-AND-IMPROVE/workflow-run-detail
- **Created**: 2026-08-16
- **Completed**: 2026-09-02

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Workflow run detail | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Workflow run detail | Gateway: Response cache | 06x02 | PARTIAL | STRONG |
| Build: Workflow run detail | Gateway: Rate limits | 06x02 | PARTIAL | STRONG |
| Build: Workflow run detail | Observe: Runs list | 06x03 | PARTIAL | STRONG |
| Build: Workflow run detail | Observe: Request flow | 06x03 | PARTIAL | STRONG |
| Build: Workflow run detail | FinOps: Budget detail | 06x05 | PARTIAL | STRONG |
| Build: Workflow run detail | Safety: Audit log | 06x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Workflow run detail row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Workflow run detail cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Workflow Run Detail as an evidence surface for one execution, not only a read-only trace.
- **UI**: Strengthen cache, guardrail, throttle, request-flow, and cost explanation from the run view.
- **Docs**: Position workflow run detail as part of the runtime and governance evidence chain.
- **Postman**: Keep run-detail and replay-adjacent flows aligned.
- **Scripts/Examples**: Add a workflow-run scenario linking one run to request evidence, budget impact, and audit traces.

## Acceptance Criteria

1. Workflow Run Detail is re-audited as an execution evidence surface
2. Runtime, governance, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
