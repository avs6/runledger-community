# WU-009: Onboarding Setup Completeness and Handoffs

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - C (Onboarding & Setup)
- **Target**: 01-ORG-AND-ACCESS/Onboarding (`/onboarding`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-20

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Onboarding | FinOps: Budgets | 01×05 | PARTIAL | STRONG |
| Org: Onboarding | FinOps: Budget notifications | 01×05 | PARTIAL | STRONG |
| Org: Onboarding | FinOps: Billing periods | 01×05 | PARTIAL | STRONG |
| Org: Onboarding | Gateway: Provider profiles | 01×02 | PARTIAL | STRONG |
| Org: Onboarding | Gateway: Model gateway | 01×02 | PARTIAL | STRONG |
| Org: Onboarding | Gateway: Guardrails | 01×02 | PARTIAL | STRONG |
| Org: Onboarding | Gateway: Rate limits | 01×02 | PARTIAL | STRONG |
| Org: Onboarding | Observe: Workspace dashboard | 01×03 | PARTIAL | STRONG |
| Org: Onboarding | Observe: Analytics overview | 01×03 | PARTIAL | STRONG |
| Org: Onboarding | Observe: Monitoring | 01×03 | PARTIAL | STRONG |
| Org: Onboarding | Safety: MCP servers | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Search tools | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Tool registry | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Tool policies | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Policy dry run | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Approvals | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Data capture | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Security | 01×04 | PARTIAL | STRONG |
| Org: Onboarding | Safety: Tags | 01×04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Onboarding × FinOps/Gateway/Observe/Safety cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Onboarding
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Onboarding
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Onboarding
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Onboarding
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Onboarding row
- `FEATURE-STATUS.md` — 01-C × 02/03/04/05 counts

## Scope

- **Backend**: Onboarding should expose a setup readiness model that checks: budget configured, provider connected, guardrails active, monitoring set up, governance policies in place. Returns a structured readiness summary with next-step recommendations.
- **UI**: Onboarding checklist should include setup steps for budgets, providers, guardrails, monitoring, and governance with "set up now" links that navigate to the owning surface. Progress model should persist and adapt.
- **Docs**: Document the onboarding readiness model and its coverage across feature families.
- **Postman**: Add onboarding readiness summary endpoint.
- **Scripts/Examples**: Add example exercising onboarding readiness checks and following setup handoffs.

## Acceptance Criteria

1. Onboarding shows a structured checklist covering FinOps, Gateway, Observe, and Safety setup
2. Each checklist item links to the owning surface for setup completion
3. Readiness model adapts based on what is already configured
4. Backend readiness endpoint provides machine-readable setup status
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
