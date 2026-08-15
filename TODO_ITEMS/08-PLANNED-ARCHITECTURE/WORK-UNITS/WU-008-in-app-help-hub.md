# WU-008: In-App Customer Documentation and Help Hub

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - C (Pipeline, API, and Embedded Product Surfaces)
- **Target**: 08-PLANNED-ARCHITECTURE/In-app customer documentation and help hub
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| In-app customer documentation and help hub | MISSING | MISSING | MISSING | PARTIAL | N/A | MISSING | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. This is a net-new surface — all delivery cells except Docs are MISSING.

## Cross-Feature Dependencies

- All feature families — contextual help must be route-aware across all surfaces
- `01-ORG-AND-ACCESS` — onboarding and first-time setup guidance
- `02-GATEWAY-AND-ROUTING` — gateway setup and troubleshooting guidance
- `03-OBSERVE` — telemetry pipeline setup guidance

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — in-app help hub row
- `FEATURE-STATUS.md` — 08-C delivery counts

## Scope

- **Backend**: Build help-hub metadata for task-aware content linking. Create content index or navigation schema for searchable in-app knowledge. Support context-sensitive doc anchors keyed to routes and tabs.
- **UI**: Top-right help drawer or hub with contextual, task-oriented help. Task-aware content that changes based on current route, tab, and user role. Embedded "why this exists" panels on complex admin pages. Guided setup tours for first platform bootstrap, org onboarding, telemetry pipeline, and gateway route creation. Searchable knowledge hub indexing docs, labs, examples, and troubleshooting.
- **Docs**: Customer-facing docs and task guidance embedded inside the product. Progressive disclosure separating first-time onboarding, operator tasks, and deep architecture.
- **Postman**: N/A.
- **Scripts/Examples**: Add examples of contextual help integration and task walkthrough authoring.

## Acceptance Criteria

1. Help hub feels intentional rather than scattered help links
2. Contextual help changes based on current route and user role
3. Guided setup tours available for key onboarding workflows
4. Searchable knowledge hub indexes docs, labs, and troubleshooting
5. FEATURE-STATUS.md dashboard updated
