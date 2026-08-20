# WU-005: All Organizations Posture Refresh

- **Status**: NOT_STARTED
- **Bundle**: 07-Platform - A (Platform Lifecycle Control Plane)
- **Target**: 07-PLATFORM-AND-UTILITY/all-organizations
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Platform: All organizations | FinOps: Budgets | 07x05 | PARTIAL | STRONG |
| Platform: All organizations | FinOps: Billing periods | 07x05 | PARTIAL | STRONG |
| Platform: All organizations | Org: Onboarding | 07x01 | PARTIAL | STRONG |
| Platform: All organizations | Org: API keys | 07x01 | PARTIAL | STRONG |
| Platform: All organizations | Gateway: Model gateway | 07x02 | PARTIAL | STRONG |
| Platform: All organizations | Observe: Monitoring | 07x03 | PARTIAL | STRONG |
| Platform: All organizations | Safety: Audit log | 07x04 | PARTIAL | STRONG |
| Platform: All organizations | Build: Evaluation studio | 07x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - All organizations row
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - All organizations cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit All Organizations as the platform lifecycle owner with stronger downstream posture summaries.
- **UI**: Tighten visibility into onboarding readiness, budget posture, runtime posture, and org-level evidence signals.
- **Docs**: Position the org lifecycle surface as a platform-admin control plane with clear downstream handoffs.
- **Postman**: Keep org lifecycle and related posture-summary flows aligned.
- **Scripts/Examples**: Add a platform-admin scenario linking org creation to onboarding, runtime, and billing posture.

## Acceptance Criteria

1. All Organizations is re-audited as the platform lifecycle surface
2. FinOps, runtime, onboarding, and evidence relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
