# WU-014: Budgets Scope Runtime Governance Refresh

- **Status**: COMPLETED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/budgets
- **Created**: 2026-08-16
- **Completed**: 2026-09-01

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budgets | Org: Users | 05x01 | GAP | STRONG |
| FinOps: Budgets | Org: API keys | 05x01 | PARTIAL | STRONG |
| FinOps: Budgets | Org: AI hub | 05x01 | PARTIAL | STRONG |
| FinOps: Budgets | Gateway: Provider profiles | 05x02 | PARTIAL | STRONG |
| FinOps: Budgets | Gateway: Model gateway | 05x02 | PARTIAL | STRONG |
| FinOps: Budgets | Gateway: Response cache | 05x02 | PARTIAL | STRONG |
| FinOps: Budgets | Observe: Request explorer | 05x03 | PARTIAL | STRONG |
| FinOps: Budgets | Safety: Approvals | 05x04 | PARTIAL | STRONG |
| FinOps: Budgets | Safety: Alert rules | 05x04 | PARTIAL | STRONG |
| FinOps: Budgets | Platform: Platform settings | 05x07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/GAP-MATRIX.md` - Budgets row
- `05-FINOPS/COHESION-MATRIX.md` - Budgets cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - user, API key, and catalog budget view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - provider, gateway, and cache budget view
- `03-OBSERVE/COHESION-MATRIX.md` - request and cost-investigation view
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - approvals and alert-governance view
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - platform-scope spend governance view

## Scope

- **Backend**: Re-audit Budgets as the primary spend-governance control plane across identity scope, runtime controls, and governed exceptions.
- **UI**: Clarify budget posture across users, API keys, providers, cache savings, and approval-driven exceptions.
- **Docs**: Update the budget story to reflect the broader live scope model, not only workspace-oriented coverage.
- **Postman**: Keep spend-policy, override, and runtime-facing budget flows aligned with the real cross-suite story.
- **Scripts/Examples**: Add a scenario covering provider-scoped and API-key-scoped budgets with approval-linked override behavior.

## Acceptance Criteria

1. Budgets are re-audited as the canonical FinOps control plane
2. User, API key, provider, and platform relationships are explicitly covered
3. Runtime, cache, and governed-exception relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
