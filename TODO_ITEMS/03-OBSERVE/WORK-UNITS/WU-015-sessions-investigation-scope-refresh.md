# WU-015: Sessions Investigation Scope Refresh

- **Status**: COMPLETED
- **Bundle**: 03-Observe - Bundle B (Request, Run, and Session Investigation)
- **Target**: 03-OBSERVE/Sessions list + Session detail (`/sessions`, `/sessions/{session_id}`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-25

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Sessions list | Org: Users | 03x01 | N/A | PARTIAL |
| Observe: Sessions list | Org: API keys | 03x01 | N/A | PARTIAL |
| Observe: Sessions detail | Org: Users | 03x01 | N/A | PARTIAL |
| Observe: Sessions detail | Org: API keys | 03x01 | N/A | PARTIAL |
| Observe: Sessions detail | FinOps: Budgets | 03x05 | N/A | PARTIAL |
| Observe: Sessions detail | FinOps: Chargeback | 03x05 | N/A | PARTIAL |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Sessions list / Session detail rows
- `03-OBSERVE/COHESION-MATRIX.md` — session-related cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Sessions
- `05-FINOPS/COHESION-MATRIX.md` — their view of Sessions
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.4 / 3.5 if delivery surfaces change

## Scope

- **Backend**: Strengthen session-level identity and spend-attribution context.
- **UI**: Make sessions easier to interpret through user, key, and cumulative cost context.
- **Docs**: Clarify sessions as a conversation-level investigation surface, not just a convenience ledger.
- **Postman**: Add any missing session-detail or export examples that emphasize attribution context.
- **Scripts/Examples**: Add a session-led investigation walkthrough.

## Acceptance Criteria

1. Session surfaces expose practical identity and cost context where product-relevant.
2. Operators can investigate a conversation without losing scope and attribution posture.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
