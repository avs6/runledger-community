# WU-012: Chargeback × Cross-Feature Strengthening

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - C (Attribution & Allocation)
- **Target**: 05-FINOPS/Chargeback
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Chargeback | Org: Organization profile | 05×01 | PARTIAL | STRONG |
| FinOps: Chargeback | Org: Access groups | 05×01 | PARTIAL | STRONG |
| FinOps: Chargeback | Org: API keys | 05×01 | PARTIAL | STRONG |
| FinOps: Chargeback | Org: Telemetry | 05×01 | PARTIAL | STRONG |
| FinOps: Chargeback | Org: AI hub | 05×01 | PARTIAL | STRONG |
| FinOps: Chargeback | Gateway: Provider profiles | 05×02 | PARTIAL | STRONG |
| FinOps: Chargeback | Gateway: Model gateway | 05×02 | PARTIAL | STRONG |
| FinOps: Chargeback | Gateway: Response cache | 05×02 | PARTIAL | STRONG |
| FinOps: Chargeback | Safety: MCP servers | 05×04 | PARTIAL | STRONG |
| FinOps: Chargeback | Safety: Tool registry | 05×04 | PARTIAL | STRONG |
| FinOps: Chargeback | Safety: Audit log | 05×04 | PARTIAL | STRONG |
| FinOps: Chargeback | Safety: Governance pack | 05×04 | PARTIAL | STRONG |
| FinOps: Chargeback | Safety: Tags | 05×04 | PARTIAL | STRONG |
| FinOps: Chargeback | Platform: All organizations | 05×07 | PARTIAL | STRONG |
| FinOps: Chargeback | Platform: Platform settings | 05×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Chargeback × Org/Gateway/Safety/Platform cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Chargeback
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Chargeback
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Chargeback
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Chargeback
- `FEATURE-STATUS.md` — 05-C × 01/02/04/07 counts

## Scope

- **Backend**: Chargeback should support access-group and API-key-native attribution. Provider-level and model-level cost allocation should be deeper. Tag-based allocation rules should be first-class. Allocation decisions should flow into audit log and governance pack. Platform operators should see cross-org allocation posture.
- **UI**: Chargeback should show access-group and API-key allocation breakdowns. Provider and model allocation should be visible. Tags should be a first-class allocation dimension. Allocation evidence should link to audit log and governance pack. Platform view should show cross-org allocation.
- **Docs**: Document access-group/API-key chargeback attribution and tag-based allocation.
- **Postman**: Add attribution context to chargeback endpoints.
- **Scripts/Examples**: Add example creating tag-based allocation rules and viewing access-group attribution.

## Acceptance Criteria

1. Access-group and API-key-native attribution supported
2. Provider and model-level allocation visible
3. Tags are first-class allocation dimension
4. Allocation evidence flows into audit log and governance pack
5. Platform view shows cross-org allocation
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
