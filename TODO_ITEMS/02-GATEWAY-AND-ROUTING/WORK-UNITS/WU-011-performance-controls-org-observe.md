# WU-011: Performance Controls Org & Scope Links

- **Status**: NOT_STARTED
- **Bundle**: 02-Gateway & Routing - C (Performance Controls)
- **Target**: 02-GATEWAY-AND-ROUTING/Response cache, Rate limits (`/gateway`)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Response cache | Org: Workspaces | 02×01 | PARTIAL | STRONG |
| Gateway: Response cache | Org: API keys | 02×01 | PARTIAL | STRONG |
| Gateway: Rate limits | Org: Organization profile | 02×01 | PARTIAL | STRONG |
| Gateway: Rate limits | Org: Workspaces | 02×01 | PARTIAL | STRONG |
| Gateway: Rate limits | Org: Access groups | 02×01 | PARTIAL | STRONG |
| Gateway: Response cache | Platform: Platform settings | 02×07 | PARTIAL | STRONG |
| Gateway: Rate limits | Platform: All organizations | 02×07 | PARTIAL | STRONG |
| Gateway: Rate limits | Platform: Platform settings | 02×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Response cache/Rate limits × Org/Platform cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Response cache/Rate limits
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Response cache/Rate limits
- `FEATURE-STATUS.md` — 02-C × 01/07 counts

## Scope

- **Backend**: Cache profiles should be workspace-aware and API-key-aware. Rate limits should expose org-level and access-group-level posture. Platform settings should include cache and throttle configuration defaults.
- **UI**: Cache and rate-limit sections in gateway should show workspace and API-key scope. Rate-limit overview should support access-group drill-down. Org profile should summarize throttle posture. Platform settings should expose cache/throttle defaults.
- **Docs**: Document workspace and access-group scoping for cache and rate-limit controls.
- **Postman**: Add workspace/access-group filters to cache and rate-limit endpoints.
- **Scripts/Examples**: Add example configuring cache profiles by workspace and viewing rate-limit posture by access group.

## Acceptance Criteria

1. Cache profiles are workspace-aware and API-key-aware
2. Rate-limit overview supports access-group drill-down
3. Org profile summarizes throttle posture
4. Platform settings expose cache/throttle configuration defaults
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
