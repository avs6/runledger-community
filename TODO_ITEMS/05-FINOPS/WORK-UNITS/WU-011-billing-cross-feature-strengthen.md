# WU-011: Billing × Cross-Feature Strengthening

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - B (Billing & Reconciliation)
- **Target**: 05-FINOPS/Billing periods, Billing period detail
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Billing periods | Gateway: Provider profiles | 05×02 | PARTIAL | STRONG |
| FinOps: Billing periods | Gateway: Model gateway | 05×02 | PARTIAL | STRONG |
| FinOps: Billing periods | Gateway: Response cache | 05×02 | PARTIAL | STRONG |
| FinOps: Billing periods | Gateway: Rate limits | 05×02 | PARTIAL | STRONG |
| FinOps: Billing period detail | Gateway: Provider profiles | 05×02 | PARTIAL | STRONG |
| FinOps: Billing period detail | Gateway: Model gateway | 05×02 | PARTIAL | STRONG |
| FinOps: Billing period detail | Gateway: Response cache | 05×02 | PARTIAL | STRONG |
| FinOps: Billing period detail | Gateway: Rate limits | 05×02 | PARTIAL | STRONG |
| FinOps: Billing periods | Safety: Tool registry | 05×04 | PARTIAL | STRONG |
| FinOps: Billing periods | Safety: Alert rules | 05×04 | PARTIAL | STRONG |
| FinOps: Billing periods | Safety: Audit log | 05×04 | PARTIAL | STRONG |
| FinOps: Billing periods | Safety: Governance pack | 05×04 | PARTIAL | STRONG |
| FinOps: Billing periods | Safety: Tags | 05×04 | PARTIAL | STRONG |
| FinOps: Billing period detail | Safety: Tool registry | 05×04 | PARTIAL | STRONG |
| FinOps: Billing period detail | Safety: Alert rules | 05×04 | PARTIAL | STRONG |
| FinOps: Billing period detail | Safety: Audit log | 05×04 | PARTIAL | STRONG |
| FinOps: Billing period detail | Safety: Governance pack | 05×04 | PARTIAL | STRONG |
| FinOps: Billing period detail | Safety: Tags | 05×04 | PARTIAL | STRONG |
| FinOps: Billing periods | Platform: All organizations | 05×07 | PARTIAL | STRONG |
| FinOps: Billing periods | Platform: Platform settings | 05×07 | PARTIAL | STRONG |
| FinOps: Billing period detail | Platform: All organizations | 05×07 | PARTIAL | STRONG |
| FinOps: Billing period detail | Platform: Platform settings | 05×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Billing × Gateway/Safety/Platform cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Billing
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Billing
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Billing
- `FEATURE-STATUS.md` — 05-B × 02/04/07 counts

## Scope

- **Backend**: Billing periods should show provider-level and route-level cost breakdowns from Gateway. Period detail should integrate cache and rate-limit cost context. Billing events should flow into audit log and governance pack. Tag-based billing attribution should be supported. Platform-level billing rollups should be available.
- **UI**: Period detail should show provider and gateway cost breakdowns. Billing events should link to audit log. Period close should produce governance pack evidence. Tag-based billing grouping should be available. Platform operators should see cross-org billing posture.
- **Docs**: Document billing-to-gateway, billing-to-governance, and platform billing workflows.
- **Postman**: Add gateway and governance context to billing endpoints.
- **Scripts/Examples**: Add example viewing billing period with provider breakdown and governance evidence.

## Acceptance Criteria

1. Billing period detail shows provider and gateway cost breakdowns
2. Billing events flow into audit log and governance pack
3. Tag-based billing attribution available
4. Platform-level billing rollups accessible
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
