# WU-013: Tool Policies Runtime Scope Refresh

- **Status**: COMPLETED
- **Bundle**: 04-Safety - A (Tool Governance Control Plane)
- **Target**: 04-SAFETY-AND-GOVERNANCE/tool-policies
- **Created**: 2026-08-16
- **Completed**: 2026-08-31

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tool policies | FinOps: Budgets | 04x05 | PARTIAL | STRONG |
| Safety: Tool policies | FinOps: Ledger | 04x05 | PARTIAL | STRONG |
| Safety: Tool policies | Org: Workspaces | 04x01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: Access groups | 04x01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: API keys | 04x01 | PARTIAL | STRONG |
| Safety: Tool policies | Gateway: Model gateway | 04x02 | PARTIAL | STRONG |
| Safety: Tool policies | Gateway: Guardrails | 04x02 | STRONG | STRONG |
| Safety: Tool policies | Observe: Request flow | 04x03 | PARTIAL | STRONG |
| Safety: Tool policies | Observe: Monitoring | 04x03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` - Tool policies row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - Tool policies cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - workspace, access-group, and API key scope view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - runtime enforcement and guardrail view
- `03-OBSERVE/COHESION-MATRIX.md` - request and monitoring evidence view
- `05-FINOPS/COHESION-MATRIX.md` - budget and ledger governance view

## Scope

- **Backend**: Re-audit policy ownership around scope inheritance, runtime enforcement, and financially material policy outcomes.
- **UI**: Make policy impact, scope boundaries, and runtime/evidence consequences easier to trace.
- **Docs**: Position Tool Policies as the active runtime policy authoring layer with real downstream effects.
- **Postman**: Keep policy CRUD, dry-run, and linked-context flows in sync with the intended governance story.
- **Scripts/Examples**: Add an end-to-end policy scenario covering scope selection, runtime application, and request evidence.

## Acceptance Criteria

1. Tool Policies are re-audited as a cross-suite governance control plane
2. Scope-aware policy relationships are explicitly covered
3. Runtime and evidence relationships are explicitly covered
4. Budget and ledger implications are explicitly covered
5. All listed cohesion cells move to the target state
6. FEATURE-STATUS.md is updated
