# WU-010: AI Hub Governance and Org-Admin Links

- **Status**: NOT_STARTED
- **Bundle**: 01-Org & Access - D (Capability Catalog)
- **Target**: 01-ORG-AND-ACCESS/AI hub (`/ai-hub`)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: AI hub | FinOps: Budget detail | 01×05 | GAP | STRONG |
| Org: AI hub | FinOps: Budgets | 01×05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Billing periods | 01×05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Billing period detail | 01×05 | PARTIAL | STRONG |
| Org: AI hub | FinOps: Chargeback | 01×05 | PARTIAL | STRONG |
| Org: AI hub | Safety: Tool registry | 01×04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Tool policies | 01×04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Approvals | 01×04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Security | 01×04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Audit log | 01×04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Governance pack | 01×04 | PARTIAL | STRONG |
| Org: AI hub | Safety: Tags | 01×04 | PARTIAL | STRONG |
| Org: AI hub | Platform: All organizations | 01×07 | PARTIAL | STRONG |
| Org: AI hub | Platform: Platform settings | 01×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — AI hub × FinOps/Safety/Platform cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of AI hub
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of AI hub
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of AI hub
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — AI hub row
- `FEATURE-STATUS.md` — 01-D × 04/05/07 counts

## Scope

- **Backend**: AI hub should expose model cost posture (linked to budget detail and billing), model access governance status (linked to approvals, audit log, governance pack), and platform-level model visibility. Budget detail should show model-level cost when drilling from AI hub context.
- **UI**: AI hub should display model cost posture card linking to budget detail and billing. Model access requests should integrate with approvals. Model deprecation and policy actions should link to audit log and governance pack. Platform admin should see cross-org model capability summary.
- **Docs**: Document AI hub's governance and financial integration patterns.
- **Postman**: Add model cost posture and model governance status endpoints.
- **Scripts/Examples**: Add example reviewing model cost posture from AI hub and checking governance status.

## Acceptance Criteria

1. AI hub shows per-model cost posture with drill-through to budget detail
2. Model access requests integrate with the approvals workflow
3. Model policy actions appear in audit log and governance pack
4. Platform admin can view cross-org model capability summary
5. AI hub tags participate in the tags/governance scoping model
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
