# WU-002: Budget Control × Gateway & Routing

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budgets, Budget detail, Budget overrides
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budgets | Gateway: Provider profiles | 05×02 | GAP | STRONG |
| FinOps: Budget detail | Gateway: Provider profiles | 05×02 | GAP | STRONG |
| FinOps: Budget detail | Gateway: Model gateway | 05×02 | GAP | STRONG |
| FinOps: Budget detail | Gateway: Response cache | 05×02 | GAP | STRONG |
| FinOps: Budget detail | Gateway: Rate limits | 05×02 | GAP | STRONG |
| FinOps: Budget overrides | Gateway: Provider profiles | 05×02 | GAP | STRONG |
| FinOps: Budgets | Gateway: Model gateway | 05×02 | PARTIAL | STRONG |
| FinOps: Budgets | Gateway: Response cache | 05×02 | PARTIAL | STRONG |
| FinOps: Budgets | Gateway: Rate limits | 05×02 | PARTIAL | STRONG |
| FinOps: Budget overrides | Gateway: Model gateway | 05×02 | PARTIAL | STRONG |
| FinOps: Budget overrides | Gateway: Rate limits | 05×02 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budgets/Budget detail/Overrides × Gateway cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Budget surfaces
- `FEATURE-STATUS.md` — 05-A × 02 counts

## Scope

- **Backend**: Make provider profiles a first-class budget scope for provider financial envelopes. Budget detail must show route-level, provider-level, cache, and rate-limit cost context. Overrides must support provider-scoped exceptions. Clarify ownership: gateway owns technical quotas, FinOps owns spend governance.
- **UI**: Budget creation must support provider-profile scope. Budget detail must show provider, route, cache, and rate-limit cost breakdown with gateway cross-links. Override creation must support provider-scoped exceptions. Gateway surfaces should link to applicable budgets.
- **Docs**: Document the gateway-FinOps ownership split and provider budget workflows.
- **Postman**: Add provider and gateway context to budget endpoints.
- **Scripts/Examples**: Add example creating a provider-scoped budget and viewing cache/rate-limit cost impact.

## Acceptance Criteria

1. Provider profiles are first-class budget scopes
2. Budget detail shows provider, route, cache, and rate-limit cost context
3. Gateway surfaces cross-link to applicable budgets
4. Override creation supports provider-scoped exceptions
5. Gateway/FinOps ownership distinction is clear in UI
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
