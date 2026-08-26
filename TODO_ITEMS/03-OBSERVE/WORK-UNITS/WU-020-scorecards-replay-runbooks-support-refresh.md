# WU-020: Scorecards Replay and Runbooks Support Refresh

- **Status**: COMPLETED
- **Bundle**: 03-Observe - Bundles C/D (cross-bundle support strengthening)
- **Target**: 03-OBSERVE/Model scorecards + Replay lab + Runbooks
- **Created**: 2026-08-16
- **Completed**: 2026-08-25

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Model scorecards | Org: Workspaces | 03x01 | PARTIAL | STRONG |
| Observe: Replay lab | Gateway: Model gateway | 03x02 | PARTIAL | STRONG |
| Observe: Runbooks | Gateway: Model gateway | 03x02 | PARTIAL | STRONG |
| Observe: Runbooks | Safety: Audit log | 03x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Model scorecards / Replay lab / Runbooks rows
- `03-OBSERVE/COHESION-MATRIX.md` — related cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Model scorecards
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Replay lab / Runbooks
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Runbooks
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.14 / 3.15 / 3.16 if delivery surfaces change

## Scope

- **Backend**: Fill support and evidence gaps that keep scorecards, replay, and runbooks from reading as fully cohesive operator tools.
- **UI**: Improve drill-through and export/support completeness where the implementation is ahead of the delivery story.
- **Docs**: Tighten route ownership and support guidance for scorecards, replay, and runbooks.
- **Postman**: Add or correct any missing requests, especially where UI contracts are ahead of backend support.
- **Scripts/Examples**: Add dedicated walkthroughs or fix missing support-path assertions.

## Acceptance Criteria

1. Scorecards, Replay, and Runbooks have support surfaces that match their shipped behavior.
2. Missing or overstated support behavior is corrected, especially where UI and backend are misaligned.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
