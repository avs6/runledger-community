# WU-004: Provider Profiles Org & Access Links

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - A (Provider & Routing)
- **Target**: 02-GATEWAY-AND-ROUTING/Provider profiles (`/provider-profiles`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-21 (pre-closed by status cleanup — all 5 target cells already STRONG or N/A)

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Provider profiles | Org: Organization profile | 02×01 | PARTIAL | STRONG |
| Gateway: Provider profiles | Org: Onboarding | 02×01 | PARTIAL | STRONG |
| Gateway: Provider profiles | Org: Users | 02×01 | PARTIAL | STRONG |
| Gateway: Provider profiles | Org: Access groups | 02×01 | PARTIAL | STRONG |
| Gateway: Provider profiles | Org: API keys | 02×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Provider profiles × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Provider profiles
- `FEATURE-STATUS.md` — 02-A × 01 counts

## Scope

- **Backend**: Provider profiles should expose org-level awareness: which org-level access decisions affect provider availability, how access groups constrain provider access, how API keys map to provider usage. Provider profile list should accept access-group and user filters.
- **UI**: Provider profile detail should show access-group and API-key usage context. Org profile and onboarding should link to provider setup. Provider list should support filtering by access group.
- **Docs**: Document provider profile relationship to org identity primitives.
- **Postman**: Add access-group and user filters to provider profile endpoints.
- **Scripts/Examples**: Add example showing provider profiles filtered by access group and linked to org context.

## Acceptance Criteria

1. Provider profiles accept access-group and user filter parameters
2. Provider detail shows access-group and API-key usage context
3. Org profile links to provider posture summary
4. Onboarding includes provider setup guidance
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
