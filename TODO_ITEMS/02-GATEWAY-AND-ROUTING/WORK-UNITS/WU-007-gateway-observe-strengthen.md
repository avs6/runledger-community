# WU-007: Model Gateway & Performance Controls Observe Strengthening

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - A/C (Provider & Routing, Performance Controls)
- **Target**: 02-GATEWAY-AND-ROUTING/Model gateway, Response cache, Rate limits (`/gateway`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-22

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Model gateway | Observe: Workspace dashboard | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Sessions list | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Session detail | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Model usage | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Analytics economics | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Cost and savings | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Outcomes and ROI | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Analytics users | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Analytics user detail | 02×03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Model scorecards | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Runs list | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Run detail | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Request flow | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Request explorer | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Model usage | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Analytics economics | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Cost and savings | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Engineering | 02×03 | PARTIAL | STRONG |
| Gateway: Response cache | Observe: Monitoring | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Runs list | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Run detail | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Request flow | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Request explorer | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Analytics economics | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Cost and savings | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Engineering | 02×03 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Monitoring | 02×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Model gateway/Response cache/Rate limits × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of these Gateway features
- `FEATURE-STATUS.md` — 02-A/C × 03 counts

## Scope

- **Backend**: Strengthen gateway runtime context in Observe: sessions should carry gateway route context, model usage should show route-level breakdown, economics and cost surfaces should reflect cache and throttle impact, monitoring should surface cache hit rates and throttle events, workspace dashboard should show gateway health summary.
- **UI**: Observe surfaces should show gateway route, cache, and throttle context where relevant. Cache hits/misses should appear in run and request investigation. Throttle events should surface in monitoring and engineering views.
- **Docs**: Document how gateway runtime behavior surfaces across Observe.
- **Postman**: Add gateway route/cache/throttle context to Observe endpoints.
- **Scripts/Examples**: Add example investigating cache and throttle impact across Observe surfaces.

## Acceptance Criteria

1. Sessions carry gateway route context
2. Model usage shows route-level breakdown
3. Cache hits/misses visible in run and request investigation
4. Throttle events surface in monitoring and engineering
5. Economics and cost surfaces reflect cache and throttle impact
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
