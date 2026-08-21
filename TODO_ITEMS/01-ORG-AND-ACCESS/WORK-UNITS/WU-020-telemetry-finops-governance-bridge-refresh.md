# WU-020: Telemetry FinOps and Governance Bridge Refresh

- **Status**: DONE
- **Bundle**: 01-Org & Access - Bundle C (Onboarding and Connected Setup)
- **Target**: 01-ORG-AND-ACCESS/Telemetry (`/monitoring/telemetry`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Telemetry | FinOps: Budgets | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | FinOps: Budget detail | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | FinOps: Budget overrides | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | FinOps: Budget notifications | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | FinOps: Billing periods | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | FinOps: Billing period detail | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | FinOps: Chargeback | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | FinOps: Ledger | 01x05 | PARTIAL | STRONG |
| Org: Telemetry | Safety: Tool registry | 01x04 | PARTIAL | STRONG |
| Org: Telemetry | Safety: Tool policies | 01x04 | PARTIAL | STRONG |
| Org: Telemetry | Safety: Data capture | 01x04 | PARTIAL | STRONG |
| Org: Telemetry | Safety: Security | 01x04 | PARTIAL | STRONG |
| Org: Telemetry | Safety: Alert rules | 01x04 | PARTIAL | STRONG |
| Org: Telemetry | Safety: Audit log | 01x04 | PARTIAL | STRONG |
| Org: Telemetry | Safety: Governance pack | 01x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Telemetry row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Telemetry cells
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Telemetry
- `05-FINOPS/COHESION-MATRIX.md` — their view of Telemetry
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 2.3 / 2.8 if delivery changes

## Scope

- **Backend**: Strengthen telemetry-derived attribution and governance-evidence contracts.
- **UI**: Make telemetry’s role in spend interpretation, policy evidence, and alerting clearer from the surface itself.
- **Docs**: Clarify telemetry as an upstream dependency for FinOps and governance, not just ingest plumbing.
- **Postman**: Add any missing telemetry-to-evidence or telemetry-summary requests.
- **Scripts/Examples**: Add an ingest-to-cost/evidence walkthrough.

## Acceptance Criteria

1. Telemetry clearly supports downstream cost, evidence, and governance workflows in the product model.
2. Operators can trace ingest posture into the FinOps and governance surfaces that depend on it.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
