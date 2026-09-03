# WU-014: Agent Detail Memory Governance Refresh

- **Status**: COMPLETED
- **Bundle**: 06-Build - B (Managed Execution Assets)
- **Target**: 06-BUILD-AND-IMPROVE/agent-detail-and-memory
- **Created**: 2026-08-16
- **Completed**: 2026-09-02

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Agent detail | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Agent detail | Observe: Run detail | 06x03 | PARTIAL | STRONG |
| Build: Agent detail | Safety: Data capture | 06x04 | PARTIAL | STRONG |
| Build: Agent memory | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Agent memory | Safety: Data capture | 06x04 | PARTIAL | STRONG |
| Build: Agent memory | Safety: Security | 06x04 | PARTIAL | STRONG |
| Build: Agent memory | Build: Evaluation studio | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Agent detail and Agent memory rows
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Agent detail and memory cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Agent Detail plus Memory as one execution-governance surface with explicit memory handling and runtime evidence.
- **UI**: Tighten edit/retire expectations and integrate memory as a tabbed subordinate concern.
- **Docs**: Document memory as part of agent governance unless intentionally promoted later.
- **Postman**: Keep agent and memory action flows aligned with the collapsed ownership model.
- **Scripts/Examples**: Add a scenario that links memory handling to run evidence, guardrails, and evaluation review.

## Acceptance Criteria

1. Agent Detail and Memory are re-audited as one governance-aware asset story
2. Runtime, memory, and safety relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
