# WU-015: Onboarding Cross-Suite Readiness Refresh

- **Status**: DONE
- **Bundle**: 01-Org & Access - Bundle C (Onboarding and Connected Setup)
- **Target**: 01-ORG-AND-ACCESS/Onboarding (`/onboarding`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Onboarding | FinOps: Budgets | 01x05 | PARTIAL | STRONG |
| Org: Onboarding | FinOps: Budget detail | 01x05 | PARTIAL | PARTIAL |
| Org: Onboarding | Gateway: Provider profiles | 01x02 | PARTIAL | STRONG |
| Org: Onboarding | Gateway: Model gateway | 01x02 | PARTIAL | STRONG |
| Org: Onboarding | Gateway: Guardrails | 01x02 | PARTIAL | STRONG |
| Org: Onboarding | Observe: Analytics overview | 01x03 | PARTIAL | STRONG |
| Org: Onboarding | Observe: Runs list | 01x03 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Tool registry | 01x04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Tool policies | 01x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Onboarding row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Onboarding cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Onboarding
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Onboarding
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Onboarding
- `05-FINOPS/COHESION-MATRIX.md` — their view of Onboarding
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 1.8 if support surfaces improve

## Scope

- **Backend**: Add explicit setup-readiness and integration-status coverage where onboarding still relies on thin or indirect status sources.
- **UI**: Turn onboarding into a real cross-suite readiness surface for runtime, safety, spend, observe, MCP, and capability setup.
- **Docs**: Align onboarding docs with its role as the primary setup shell.
- **Postman**: Cover onboarding readiness/status endpoints and any demo or checklist contracts.
- **Scripts/Examples**: Add setup validation or readiness-check automation.

## Acceptance Criteria

1. Onboarding clearly introduces runtime, spend, observe, and governance posture rather than only connection copy.
2. Operators can confirm setup readiness and jump into owner surfaces from one place.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
