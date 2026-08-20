# WU-018: Billing Detail Evidence Refresh

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - B (Billing and Reconciliation)
- **Target**: 05-FINOPS/billing-period-detail
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Billing period detail | Org: Organization profile | 05x01 | GAP | STRONG |
| FinOps: Billing period detail | Org: Users | 05x01 | GAP | STRONG |
| FinOps: Billing period detail | Org: Access groups | 05x01 | GAP | STRONG |
| FinOps: Billing period detail | Org: API keys | 05x01 | GAP | STRONG |
| FinOps: Billing period detail | Gateway: Model gateway | 05x02 | PARTIAL | STRONG |
| FinOps: Billing period detail | Observe: Sessions list | 05x03 | PARTIAL | STRONG |
| FinOps: Billing period detail | Observe: Request explorer | 05x03 | PARTIAL | STRONG |
| FinOps: Billing period detail | Safety: Governance pack | 05x04 | PARTIAL | STRONG |
| FinOps: Billing period detail | Build: Replay lab | 05x06 | PARTIAL | STRONG |
| FinOps: Billing period detail | Platform: All organizations | 05x07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/GAP-MATRIX.md` - Billing period detail row
- `05-FINOPS/COHESION-MATRIX.md` - Billing period detail cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - org, access-group, and API key reconciliation view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - model-gateway reconciliation drillback view
- `03-OBSERVE/COHESION-MATRIX.md` - session and request evidence view
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - governance-pack evidence view
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - replay and improvement feedback view
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - cross-org reconciliation view

## Scope

- **Backend**: Re-audit Billing Detail as the evidence-rich reconciliation workspace for one period's spend, adjustments, and downstream packaging.
- **UI**: Improve drillback into org owners, request/session evidence, model effects, and platform-level review context.
- **Docs**: Document the detail route as the main reconciliation workspace, not only a child report.
- **Postman**: Keep detail, adjustments, reconciliation, and export flows aligned with the intended operator experience.
- **Scripts/Examples**: Add a scenario that starts with a billing discrepancy and walks through evidence, replay, and governance packaging.

## Acceptance Criteria

1. Billing Detail is re-audited as the main reconciliation workspace
2. Ownership, evidence, and platform-review relationships are explicitly covered
3. Replay and governance-pack relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
