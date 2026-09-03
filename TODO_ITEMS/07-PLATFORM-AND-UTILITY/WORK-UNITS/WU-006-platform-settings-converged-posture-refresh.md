# WU-006: Platform Settings Converged Posture Refresh

- **Status**: COMPLETED
- **Bundle**: 07-Platform - B (Platform Settings Convergence)
- **Target**: 07-PLATFORM-AND-UTILITY/platform-settings
- **Created**: 2026-08-16
- **Completed**: 2026-09-03

## Completion Notes

UI: Added Evaluation Studio and Organizations drill-through links to convergence posture cards (amber: Audit & Compliance, cyan: Telemetry & Capture). Added Monitoring drill-through to telemetry card. Docs: Updated platform-settings.mdx with Adjacent Relationships section documenting Evaluation Studio (compliance context affects data governance constraints for experiments), Organizations (shared platform-admin context), and Monitoring (alert/guardrail operational health). Most target cells were already STRONG from prior WUs (Budgets, Chargeback, Org profile, Workspaces, Guardrails, Monitoring, Governance pack). Actual cell changes: Evaluation studio N/A→P (compliance context linkage), Platform settings self P→S (Organizations cross-navigation).

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Platform: Platform settings | FinOps: Budgets | 07x05 | PARTIAL | STRONG |
| Platform: Platform settings | FinOps: Chargeback | 07x05 | PARTIAL | STRONG |
| Platform: Platform settings | Org: Organization profile | 07x01 | PARTIAL | STRONG |
| Platform: Platform settings | Org: Workspaces | 07x01 | PARTIAL | STRONG |
| Platform: Platform settings | Gateway: Guardrails | 07x02 | PARTIAL | STRONG |
| Platform: Platform settings | Observe: Monitoring | 07x03 | PARTIAL | STRONG |
| Platform: Platform settings | Safety: Governance pack | 07x04 | STRONG | STRONG |
| Platform: Platform settings | Build: Evaluation studio | 07x06 | N/A | PARTIAL |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - Platform settings row
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - Platform settings cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Platform Settings as the single home for platform defaults, compliance, retention, backup, and ops posture.
- **UI**: Tighten convergence across settings tabs and improve cross-feature posture summaries.
- **Docs**: Unify the platform-settings story instead of leaving it scattered across sub-area docs.
- **Postman**: Keep absorbed platform-default and compliance flows aligned under one owner surface.
- **Scripts/Examples**: Add a platform-settings scenario linking compliance, retention, budget-breach hooks, and monitoring posture.

## Acceptance Criteria

1. Platform Settings is re-audited as the converged admin console
2. Governance, runtime, billing, and monitoring relationships are explicitly covered
3. The current `N/A` relationship to Evaluation Studio is re-reviewed and updated appropriately
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
