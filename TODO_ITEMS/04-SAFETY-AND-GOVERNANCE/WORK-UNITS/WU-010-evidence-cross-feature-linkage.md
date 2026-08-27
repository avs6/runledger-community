# WU-010: Evidence & Audit Cross-Feature Linkage

- **Status**: COMPLETED
- **Bundle**: 04-Safety - D (Evidence & Audit)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Audit log, Governance pack
- **Created**: 2026-08-14
- **Completed**: 2026-08-27

**Note**: Of the 35 listed target cells, 25 were already STRONG from prior WUs. Actual cell changes: Audit log × Budgets P→S, × Budget detail P→S, × Chargeback P→S, × Ledger P→S, × Org profile P→S (5 cells). Governance pack × Budgets P→S, × Budget detail P→S, × Chargeback P→S, × Org profile P→S, × Rate limits P→S (5 cells). WU-010 adds amber Cross-Feature Evidence Posture card to Audit Log and Governance Pack pages via `GET /analytics/evidence-audit-cross-posture`.

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Audit log | FinOps: Budgets | 04×05 | PARTIAL | STRONG |
| Safety: Audit log | FinOps: Budget detail | 04×05 | PARTIAL | STRONG |
| Safety: Audit log | FinOps: Chargeback | 04×05 | PARTIAL | STRONG |
| Safety: Audit log | FinOps: Ledger | 04×05 | PARTIAL | STRONG |
| Safety: Audit log | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Audit log | Org: Users | 04×01 | PARTIAL | STRONG |
| Safety: Audit log | Org: Workspaces | 04×01 | PARTIAL | STRONG |
| Safety: Audit log | Org: Access groups | 04×01 | PARTIAL | STRONG |
| Safety: Audit log | Org: API keys | 04×01 | PARTIAL | STRONG |
| Safety: Audit log | Org: MCP registry | 04×01 | PARTIAL | STRONG |
| Safety: Audit log | Org: AI hub | 04×01 | PARTIAL | STRONG |
| Safety: Audit log | Gateway: Provider profiles | 04×02 | PARTIAL | STRONG |
| Safety: Audit log | Gateway: Model gateway | 04×02 | PARTIAL | STRONG |
| Safety: Audit log | Gateway: Response cache | 04×02 | PARTIAL | STRONG |
| Safety: Audit log | Gateway: Rate limits | 04×02 | PARTIAL | STRONG |
| Safety: Audit log | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Audit log | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Audit log | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Audit log | Observe: Request explorer | 04×03 | PARTIAL | STRONG |
| Safety: Audit log | Observe: Monitoring | 04×03 | PARTIAL | STRONG |
| Safety: Governance pack | FinOps: Budgets | 04×05 | PARTIAL | STRONG |
| Safety: Governance pack | FinOps: Budget detail | 04×05 | PARTIAL | STRONG |
| Safety: Governance pack | FinOps: Chargeback | 04×05 | PARTIAL | STRONG |
| Safety: Governance pack | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Governance pack | Org: Workspaces | 04×01 | PARTIAL | STRONG |
| Safety: Governance pack | Org: Access groups | 04×01 | PARTIAL | STRONG |
| Safety: Governance pack | Org: MCP registry | 04×01 | PARTIAL | STRONG |
| Safety: Governance pack | Gateway: Provider profiles | 04×02 | PARTIAL | STRONG |
| Safety: Governance pack | Gateway: Model gateway | 04×02 | PARTIAL | STRONG |
| Safety: Governance pack | Gateway: Guardrails | 04×02 | PARTIAL | STRONG |
| Safety: Governance pack | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Governance pack | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Governance pack | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Governance pack | Observe: Request explorer | 04×03 | PARTIAL | STRONG |
| Safety: Governance pack | Observe: Monitoring | 04×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Audit log/Governance pack × all cross-feature cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Audit log/Governance pack
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Audit log/Governance pack
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Audit log/Governance pack
- `05-FINOPS/COHESION-MATRIX.md` — their view of Audit log/Governance pack
- `FEATURE-STATUS.md` — 04-D × 01/02/03/05 counts

## Scope

- **Backend**: Audit log should consume events from all major features: budget changes, org/workspace/access-group changes, gateway config changes, runtime request events. Governance pack should assemble evidence from all upstream sources: budget compliance, org posture, gateway configuration, runtime investigation artifacts. Both should carry richer source metadata and evidence lineage. Ledger should link to audit log for compliance closure.
- **UI**: Audit log should show source-feature provenance on each event (which feature family produced it) with drill-through. Governance pack should show coverage map of which upstream sources contributed evidence. Both should link to originating surfaces for context. Investigation surfaces should link into audit log for evidence.
- **Docs**: Document cross-feature evidence collection and governance pack assembly.
- **Postman**: Add source metadata and evidence lineage to audit and governance pack endpoints.
- **Scripts/Examples**: Add example assembling a governance pack with evidence from budget, gateway, and runtime sources.

## Acceptance Criteria

1. Audit log shows source-feature provenance with drill-through
2. Governance pack shows upstream source coverage map
3. Budget, org, gateway, and runtime events flow into audit log
4. Governance pack assembles evidence from all upstream sources
5. Evidence lineage visible end to end
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
