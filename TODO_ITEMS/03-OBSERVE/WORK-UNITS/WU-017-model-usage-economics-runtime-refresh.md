# WU-017: Model Usage Economics and Runtime Refresh

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - Bundle C (Economics, Model Intelligence, and Outcomes)
- **Target**: 03-OBSERVE/Model usage (`/model-usage`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Model usage | FinOps: Budgets | 03x05 | PARTIAL | STRONG |
| Observe: Model usage | FinOps: Budget detail | 03x05 | PARTIAL | STRONG |
| Observe: Model usage | Gateway: Guardrails | 03x02 | PARTIAL | STRONG |
| Observe: Model usage | Gateway: Rate limits | 03x02 | PARTIAL | STRONG |
| Observe: Model usage | Org: API keys | 03x01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Model usage row
- `03-OBSERVE/COHESION-MATRIX.md` — Model usage cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Model usage
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Model usage
- `05-FINOPS/COHESION-MATRIX.md` — their view of Model usage
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.12 if delivery surfaces change

## Scope

- **Backend**: Improve model-usage attribution to budgets, keys, guardrails, and throttling.
- **UI**: Make `/model-usage` a clearer explanation layer for runtime-adjusted usage rather than raw token charts only.
- **Docs**: Clarify model usage as the bridge between economics, routing, and policy-adjusted traffic.
- **Postman**: Add any missing model-usage requests or fields tied to budget/policy context.
- **Scripts/Examples**: Add a model-usage workflow that includes budget and runtime-control interpretation.

## Acceptance Criteria

1. Model usage explains how runtime controls and budget posture change observed usage.
2. Operators can move from usage analysis into budgets, gateway, and API-key owner surfaces cleanly.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
