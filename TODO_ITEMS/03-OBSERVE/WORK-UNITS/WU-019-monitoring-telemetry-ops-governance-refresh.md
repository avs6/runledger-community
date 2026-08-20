# WU-019: Monitoring Telemetry Ops and Governance Refresh

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - Bundle D (Operations and Monitoring Intelligence)
- **Target**: 03-OBSERVE/Monitoring + Telemetry (`/monitoring`, `/monitoring/telemetry`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Monitoring | FinOps: Budget detail | 03x05 | N/A | PARTIAL |
| Observe: Monitoring | Org: API keys | 03x01 | PARTIAL | STRONG |
| Observe: Monitoring | Safety: Approvals | 03x04 | N/A | PARTIAL |
| Observe: Telemetry | Gateway: Guardrails | 03x02 | N/A | PARTIAL |
| Observe: Telemetry | Gateway: Response cache | 03x02 | N/A | PARTIAL |
| Observe: Telemetry | Gateway: Rate limits | 03x02 | N/A | PARTIAL |
| Observe: Telemetry | Safety: Tool registry | 03x04 | N/A | PARTIAL |
| Observe: Telemetry | Safety: Tool policies | 03x04 | N/A | PARTIAL |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Monitoring / Telemetry rows
- `03-OBSERVE/COHESION-MATRIX.md` — monitoring/telemetry cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Monitoring
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Monitoring / Telemetry
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Monitoring / Telemetry
- `05-FINOPS/COHESION-MATRIX.md` — their view of Monitoring
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.13 if delivery surfaces change

## Scope

- **Backend**: Improve operational triage contracts for budget, key, guardrail, cache, rate-limit, and governance correlation.
- **UI**: Make Monitoring and Telemetry stronger at explaining cross-suite operational consequences and next-step pivots.
- **Docs**: Clarify Monitoring as triage shell and Telemetry as deep evidence owner, with stronger runtime/governance linkage.
- **Postman**: Add any missing monitoring/telemetry correlation requests.
- **Scripts/Examples**: Add an ops triage walkthrough from signal to runtime/governance cause.

## Acceptance Criteria

1. Monitoring and Telemetry expose more actionable runtime, budget, and governance correlation.
2. Operators can pivot from triage signals into the right owner surfaces without guessing.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
