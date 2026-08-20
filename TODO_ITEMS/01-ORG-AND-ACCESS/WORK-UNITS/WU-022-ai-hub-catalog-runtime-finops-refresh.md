# WU-022: AI Hub Catalog Runtime FinOps Refresh

- **Status**: NOT_STARTED
- **Bundle**: 01-Org & Access - Bundle D (Workspace Capability Catalog and Legacy Transition)
- **Target**: 01-ORG-AND-ACCESS/AI hub (`/ai-hub`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: AI hub | FinOps: Budgets | 01x05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Budget detail | 01x05 | GAP | PARTIAL |
| Org: AI hub | FinOps: Budget overrides | 01x05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Budget notifications | 01x05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Billing periods | 01x05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Billing period detail | 01x05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Chargeback | 01x05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Ledger | 01x05 | PARTIAL | STRONG |
| Org: AI hub | Gateway: Guardrails | 01x02 | N/A | PARTIAL |
| Org: AI hub | Gateway: Response cache | 01x02 | N/A | PARTIAL |
| Org: AI hub | Observe: Analytics overview | 01x03 | PARTIAL | STRONG |
| Org: AI hub | Observe: Runs list | 01x03 | PARTIAL | STRONG |
| Org: AI hub | Observe: Run detail | 01x03 | PARTIAL | STRONG |
| Org: AI hub | Observe: Request flow | 01x03 | PARTIAL | STRONG |
| Org: AI hub | Observe: Request explorer | 01x03 | PARTIAL | STRONG |
| Org: AI hub | Safety: Approvals | 01x04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Audit log | 01x04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Governance pack | 01x04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Tags | 01x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — AI hub row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — AI hub cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of AI hub
- `03-OBSERVE/COHESION-MATRIX.md` — their view of AI hub
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of AI hub
- `05-FINOPS/COHESION-MATRIX.md` — their view of AI hub
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 8.8 if delivery changes

## Scope

- **Backend**: Strengthen AI-hub linkage to pricing, policy, approvals, usage intelligence, and runtime compatibility metadata.
- **UI**: Make AI hub a real control-adjacent catalog with stronger links into FinOps, Observe, Gateway, and Governance.
- **Docs**: Clarify AI hub as a workspace capability catalog with financial and governance meaning.
- **Postman**: Add missing AI hub request coverage.
- **Scripts/Examples**: Expand AI hub scenarios to include sync, policy posture, and model-usage/FinOps linkage.

## Acceptance Criteria

1. AI hub clearly participates in pricing, runtime compatibility, governance, and model-intelligence workflows.
2. Operators can move from catalog metadata into the relevant owner surfaces for spend, usage, and policy posture.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
