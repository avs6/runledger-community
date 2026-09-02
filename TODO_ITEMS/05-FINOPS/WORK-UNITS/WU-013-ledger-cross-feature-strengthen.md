# WU-013: Ledger × Cross-Feature Strengthening

- **Status**: COMPLETED
- **Bundle**: 05-FinOps - D (Compliance Closure)
- **Target**: 05-FINOPS/Ledger
- **Created**: 2026-08-14
- **Completed**: 2026-09-01

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Ledger | Org: Organization profile | 05×01 | PARTIAL | STRONG |
| FinOps: Ledger | Org: Org settings | 05×01 | PARTIAL | STRONG |
| FinOps: Ledger | Org: Workspaces | 05×01 | PARTIAL | STRONG |
| FinOps: Ledger | Observe: Analytics overview | 05×03 | PARTIAL | STRONG |
| FinOps: Ledger | Observe: Analytics economics | 05×03 | PARTIAL | STRONG |
| FinOps: Ledger | Observe: Cost and savings | 05×03 | PARTIAL | STRONG |
| FinOps: Ledger | Observe: Billing summary | 05×03 | PARTIAL | STRONG |
| FinOps: Ledger | Observe: Monitoring | 05×03 | PARTIAL | STRONG |
| FinOps: Ledger | Safety: Security | 05×04 | PARTIAL | STRONG |
| FinOps: Ledger | Safety: Audit log | 05×04 | PARTIAL | STRONG |
| FinOps: Ledger | Platform: All organizations | 05×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Ledger × Org/Observe/Safety/Platform cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Ledger
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Ledger
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Ledger
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Ledger
- `FEATURE-STATUS.md` — 05-D × 01/03/04/07 counts

## Scope

- **Backend**: Ledger should consume org and workspace context for compliance scoping. Observe economics surfaces should reference ledger verification status. Audit log should link to ledger evidence. Platform operators should see cross-org ledger posture. Security context should feed into ledger integrity.
- **UI**: Ledger/compliance view should show org and workspace scope. Economics and billing summary surfaces should show ledger verification status. Audit log should link to ledger events. Platform settings should show cross-org ledger posture.
- **Docs**: Document ledger compliance closure workflow across org, observe, and platform.
- **Postman**: Add cross-feature context to ledger endpoints.
- **Scripts/Examples**: Add example verifying ledger integrity and reviewing cross-org compliance posture.

## Acceptance Criteria

1. Ledger shows org and workspace compliance scoping
2. Economics surfaces reference ledger verification status
3. Audit log links to ledger evidence
4. Platform operators see cross-org ledger posture
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
