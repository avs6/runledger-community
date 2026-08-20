# WU-015: Data Capture Evidence Runtime Refresh

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - C (Data Protection, Security, and Taxonomy)
- **Target**: 04-SAFETY-AND-GOVERNANCE/data-capture
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Data capture | FinOps: Budgets | 04x05 | PARTIAL | STRONG |
| Safety: Data capture | FinOps: Ledger | 04x05 | PARTIAL | STRONG |
| Safety: Data capture | Org: Workspaces | 04x01 | PARTIAL | STRONG |
| Safety: Data capture | Org: API keys | 04x01 | PARTIAL | STRONG |
| Safety: Data capture | Gateway: Provider profiles | 04x02 | PARTIAL | STRONG |
| Safety: Data capture | Gateway: Model gateway | 04x02 | PARTIAL | STRONG |
| Safety: Data capture | Gateway: Response cache | 04x02 | PARTIAL | STRONG |
| Safety: Data capture | Observe: Request flow | 04x03 | PARTIAL | STRONG |
| Safety: Data capture | Observe: Request explorer | 04x03 | PARTIAL | STRONG |
| Safety: Data capture | Safety: Audit log | 04x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` - Data capture row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - Data capture cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - workspace and API key data posture view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - provider, gateway, and cache evidence view
- `03-OBSERVE/COHESION-MATRIX.md` - request-analysis evidence view
- `05-FINOPS/COHESION-MATRIX.md` - spend and ledger evidence view

## Scope

- **Backend**: Re-audit how capture policy affects runtime records, storage decisions, evidence trails, and cost interpretation.
- **UI**: Show clearer linkage between capture posture, request visibility, cache behavior, and downstream audit evidence.
- **Docs**: Explain Data Capture as part of the runtime evidence contract, not only privacy configuration.
- **Postman**: Keep scoped policy and evidence-facing flows aligned with the intended runtime story.
- **Scripts/Examples**: Add a scenario that shows a scoped capture rule affecting runtime traces, exports, and cost/evidence interpretation.

## Acceptance Criteria

1. Data Capture is re-audited as a runtime and evidence-layer control
2. Scope, gateway, and request-analysis relationships are explicitly covered
3. Audit and FinOps evidence implications are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
