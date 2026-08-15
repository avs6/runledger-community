# WU-007: API Explorer and Generated Swagger UI

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - C (Pipeline, API, and Embedded Product Surfaces)
- **Target**: 08-PLANNED-ARCHITECTURE/API explorer and generated Swagger UI
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| API explorer and generated Swagger UI | PARTIAL | PARTIAL | PARTIAL | PARTIAL | LEGACY | MISSING | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. Postman is marked LEGACY — the goal is to collapse manual Postman-first maintenance into generated OpenAPI/Swagger.

## Cross-Feature Dependencies

- All feature families — API explorer covers the full platform API surface
- `02-GATEWAY-AND-ROUTING` — data-plane vs control-plane endpoint ownership
- `01-ORG-AND-ACCESS` — authenticated sessions respecting org/workspace/role context

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — API explorer row
- `FEATURE-STATUS.md` — 08-C delivery counts

## Scope

- **Backend**: Strengthen generated OpenAPI output to become the canonical API reference. Add endpoint ownership badges (control plane, data plane, observability, admin). Add API change log tracking by release. Support authenticated API-console sessions respecting user context.
- **UI**: First-class generated Swagger surface with in-product exploration. Interactive try-it-out functionality. Endpoint ownership badges. API change log view. SDK snippet generation for Python, TypeScript, and curl.
- **Docs**: Collapse manual Postman-first maintenance into generated OpenAPI/Swagger. Add API recipes for common multi-step workflows. Add API workflow collections aligned with blueprint bundles.
- **Postman**: Transition from manual Postman maintenance to generated OpenAPI as the source of truth. Postman collections should be generated rather than hand-maintained.
- **Scripts/Examples**: Add examples seeded from main labs and simulation scripts rather than static placeholders.

## Acceptance Criteria

1. API explorer is generated, interactive, and in-product at `/api-docs`
2. Endpoint ownership badges distinguish control plane, data plane, and observability
3. Manual Postman drift reduced through generated OpenAPI as source of truth
4. Authenticated API sessions respect user org/workspace/role context
5. FEATURE-STATUS.md dashboard updated
