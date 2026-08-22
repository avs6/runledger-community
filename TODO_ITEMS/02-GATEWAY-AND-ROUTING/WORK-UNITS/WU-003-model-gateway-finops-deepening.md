# WU-003: Model Gateway FinOps Deepening

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - A (Provider & Routing)
- **Target**: 02-GATEWAY-AND-ROUTING/Model gateway (`/gateway`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Model gateway | FinOps: Budgets | 02×05 | PARTIAL | STRONG |
| Gateway: Model gateway | FinOps: Budget detail | 02×05 | PARTIAL | STRONG |
| Gateway: Model gateway | FinOps: Budget overrides | 02×05 | PARTIAL | STRONG |
| Gateway: Model gateway | FinOps: Budget notifications | 02×05 | PARTIAL | STRONG |
| Gateway: Model gateway | FinOps: Billing periods | 02×05 | PARTIAL | STRONG |
| Gateway: Model gateway | FinOps: Billing period detail | 02×05 | PARTIAL | STRONG |
| Gateway: Model gateway | FinOps: Chargeback | 02×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Model gateway × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Model gateway
- `02-GATEWAY-AND-ROUTING/GAP-MATRIX.md` — Model gateway row
- `FEATURE-STATUS.md` — 02-A × 05 counts

## Scope

- **Backend**: Gateway control plane should expose embedded financial context: route-level and model-level spend posture linked to budgets, budget notification awareness for routes approaching limits, billing period attribution by route/model, chargeback allocation by gateway routing path. Gateway remains the technical owner; FinOps remains the financial owner.
- **UI**: Gateway route and model views should show spend posture badges with drill-through to budget detail. Budget notification awareness should surface in gateway operator views. Route-level billing attribution should be accessible from gateway.
- **Docs**: Document the gateway-to-FinOps operator bridge: where gateway operators see financial context and where they hand off to FinOps surfaces.
- **Postman**: Add route/model spend posture and budget notification endpoints to gateway collection.
- **Scripts/Examples**: Add example showing gateway route spend posture and budget notification awareness.

## Acceptance Criteria

1. Gateway route and model views show spend posture with budget links
2. Budget notification awareness surfaces in gateway operator views
3. Billing and chargeback attribution accessible from gateway context
4. Gateway does not duplicate financial editing — read-only with drill-through
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
