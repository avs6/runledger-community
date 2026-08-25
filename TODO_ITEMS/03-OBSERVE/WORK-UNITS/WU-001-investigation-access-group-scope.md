# WU-001: Investigation Surfaces Access-Group Scope

- **Status**: COMPLETED
- **Bundle**: 03-Observe - B (Investigation)
- **Target**: 03-OBSERVE/Runs list, Run detail, Request flow, Request explorer
- **Created**: 2026-08-14
- **Completed**: 2026-08-22

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Runs list | Org: Access groups | 03×01 | GAP | STRONG |
| Observe: Run detail | Org: Access groups | 03×01 | GAP | STRONG |
| Observe: Request flow | Org: Access groups | 03×01 | GAP | STRONG |
| Observe: Request explorer | Org: Access groups | 03×01 | GAP | STRONG |
| Observe: Analytics overview | Org: Access groups | 03×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Runs/Run detail/Request flow/Request explorer × Access groups cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of these Observe features
- `03-OBSERVE/GAP-MATRIX.md` — Runs list, Run detail, Request flow, Request explorer rows
- `FEATURE-STATUS.md` — 03-B × 01 counts

## Scope

- **Backend**: Runs list, run detail, request flow, and request explorer should accept access-group as a filter/facet dimension. Access-group identity should be carried on runtime telemetry events where available. Analytics overview should support access-group drill-down.
- **UI**: Investigation surfaces should expose an access-group filter chip. Run detail should show access-group provenance. Request flow and request explorer should facet by access group. Analytics overview should show access-group breakdowns.
- **Docs**: Document access-group-scoped investigation workflows.
- **Postman**: Add access-group filter to runs, request flow, and request explorer endpoints.
- **Scripts/Examples**: Add example investigating runs filtered by access group.

## Acceptance Criteria

1. Runs list and run detail accept access-group filter
2. Request flow and request explorer expose access-group dimension
3. Analytics overview supports access-group drill-down
4. Access-group identity carried on runtime events where available
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
