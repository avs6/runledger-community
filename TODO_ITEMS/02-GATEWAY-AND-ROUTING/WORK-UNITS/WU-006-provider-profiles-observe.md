# WU-006: Provider Profiles Observe Visibility

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - A (Provider & Routing)
- **Target**: 02-GATEWAY-AND-ROUTING/Provider profiles (`/provider-profiles`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-22

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Provider profiles | Observe: Analytics overview | 02×03 | PARTIAL | STRONG |
| Gateway: Provider profiles | Observe: Runs list | 02×03 | PARTIAL | STRONG |
| Gateway: Provider profiles | Observe: Run detail | 02×03 | PARTIAL | STRONG |
| Gateway: Provider profiles | Observe: Request flow | 02×03 | PARTIAL | STRONG |
| Gateway: Provider profiles | Observe: Request explorer | 02×03 | PARTIAL | STRONG |
| Gateway: Provider profiles | Observe: Analytics economics | 02×03 | PARTIAL | STRONG |
| Gateway: Provider profiles | Observe: Cost and savings | 02×03 | PARTIAL | STRONG |
| Gateway: Provider profiles | Observe: Engineering | 02×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Provider profiles × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Provider profiles
- `FEATURE-STATUS.md` — 02-A × 03 counts

## Scope

- **Backend**: Observe investigation surfaces should accept provider-profile as a filter dimension: runs, request flows, and request explorer should filter by provider. Analytics overview, economics, cost/savings, and engineering should surface provider-level breakdowns.
- **UI**: Observe surfaces should expose provider-profile filter/facet. Provider profile detail should link to its observability footprint (runs, cost, engineering).
- **Docs**: Document provider-scoped investigation workflows.
- **Postman**: Add provider-profile filter to runs, request flow, analytics, and engineering endpoints.
- **Scripts/Examples**: Add example investigating traffic and cost by provider profile.

## Acceptance Criteria

1. Runs and request flow/explorer accept provider-profile filter
2. Analytics overview and economics show provider-level breakdown
3. Cost and savings surfaces support provider-level attribution
4. Provider profile detail links to its observability footprint
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
