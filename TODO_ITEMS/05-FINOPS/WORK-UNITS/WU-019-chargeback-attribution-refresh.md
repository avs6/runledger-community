# WU-019: Chargeback Attribution Refresh

- **Status**: COMPLETED
- **Bundle**: 05-FinOps - C (Attribution and Allocation)
- **Target**: 05-FINOPS/chargeback
- **Created**: 2026-08-16
- **Completed**: 2026-09-01

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Chargeback | Org: Users | 05x01 | GAP | STRONG |
| FinOps: Chargeback | Org: Access groups | 05x01 | GAP | STRONG |
| FinOps: Chargeback | Org: API keys | 05x01 | GAP | STRONG |
| FinOps: Chargeback | Gateway: Response cache | 05x02 | PARTIAL | STRONG |
| FinOps: Chargeback | Observe: Monitoring | 05x03 | PARTIAL | STRONG |
| FinOps: Chargeback | Safety: Audit log | 05x04 | PARTIAL | STRONG |
| FinOps: Chargeback | Safety: Tags | 05x04 | PARTIAL | STRONG |
| FinOps: Chargeback | Build: Agent detail | 05x06 | STRONG | STRONG |
| FinOps: Chargeback | Build: Optimization opportunities | 05x06 | PARTIAL | STRONG |
| FinOps: Chargeback | Platform: Plugins | 05x07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/GAP-MATRIX.md` - Chargeback row
- `05-FINOPS/COHESION-MATRIX.md` - Chargeback cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - user, access-group, and API key attribution view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - cache-aware allocation view
- `03-OBSERVE/COHESION-MATRIX.md` - monitoring and economics attribution view
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - audit and tag evidence view
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - agent and optimization attribution view
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - plugin and platform allocation view

## Scope

- **Backend**: Re-audit Chargeback as the allocation engine across modern scope primitives, runtime savings signals, and downstream ownership evidence.
- **UI**: Make attribution confidence, cache-aware allocation, and tag- or API-key-driven ownership more explicit.
- **Docs**: Position Chargeback around workspaces, access groups, workflows, API keys, providers, and tags rather than legacy reporting models.
- **Postman**: Keep rule, allocation, exception, and export flows aligned with the modern attribution story.
- **Scripts/Examples**: Add a scenario showing cost allocation from provider/cache effects into access-group, API-key, and workflow owners.

## Acceptance Criteria

1. Chargeback is re-audited as the Bundle C allocation owner
2. Modern scope, runtime-savings, and evidence relationships are explicitly covered
3. Optimization and platform-allocation relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
