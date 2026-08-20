# WU-003: Access Groups as Observe Investigation Dimension

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/Access groups (`/access-groups`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-16

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Access groups | Observe: Runs list | 01×03 | GAP | STRONG |
| Org: Access groups | Observe: Run detail | 01×03 | GAP | STRONG |
| Org: Access groups | Observe: Request flow | 01×03 | GAP | STRONG |
| Org: Access groups | Observe: Request explorer | 01×03 | GAP | STRONG |
| Org: Access groups | Observe: Workspace dashboard | 01×03 | PARTIAL | STRONG |
| Org: Access groups | Observe: Analytics overview | 01×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Access groups × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Access groups
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Access groups row (Cohesion column)
- `FEATURE-STATUS.md` — 01-B × 03 counts

## Scope

- **Backend**: Runs, request flows, and request explorer should accept access-group as a filter dimension. Runtime telemetry events should carry access-group context where available.
- **UI**: Runs list, run detail, request flow, and request explorer should expose access-group filter/facet. Workspace dashboard and analytics overview should support access-group drill-down.
- **Docs**: Document access-group-scoped investigation workflows.
- **Postman**: Add access-group filter to runs, request flow, and request explorer endpoints.
- **Scripts/Examples**: Add example investigating runs filtered by access group.

## Acceptance Criteria

1. Runs list and run detail can filter by access group
2. Request flow and request explorer expose access-group dimension
3. Workspace dashboard supports access-group drill-down
4. Analytics overview recognizes access-group scope
5. Access group detail page links to its observability footprint
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated

## Completion Notes

- Added `access_group_id` investigation scope support across runs list/export, run detail, run graph, request flow, request-flow focus, request explorer, and analytics overview.
- Added access-group observe deep-links from `/access-groups` into scoped Analytics Overview, Runs, Request Flow, and Request Explorer.
- Updated docs, Postman requests, example coverage, and smoke coverage to reflect access-group-scoped Observe investigation workflows.
