# WU-010: Documentation IA and Hierarchy

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - D (Design System, Documentation Architecture, and Repo Systemization)
- **Target**: 08-PLANNED-ARCHITECTURE/Documentation IA, hierarchy, and diagrams
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Documentation IA, hierarchy, and diagrams | PARTIAL | N/A | N/A | PARTIAL | N/A | N/A | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. This is a docs-architecture concern affecting all feature families.

## Cross-Feature Dependencies

- All feature families — docs landing map should mirror major feature families and bundles
- `08-C` help hub — docs hierarchy feeds the in-app contextual help
- All blueprints — blueprint-to-doc crosswalks for audit traceability

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — documentation IA row
- `FEATURE-STATUS.md` — 08-D delivery counts

## Scope

- **Backend**: Docs navigation structure and taxonomy metadata. Docs health checks that flag broken conceptual links when features move or collapse. Blueprint-to-doc crosswalks for systematic audit.
- **UI**: N/A (docs are a separate surface, not in-app UI).
- **Docs**: Feature-oriented navigation reorganized by product workflow and architecture domains. Docs landing map mirroring major feature families and bundle blueprints. Mandatory Mermaid architecture blocks for every major subsystem and bundle. Customer-facing progressive disclosure separating onboarding, operator tasks, and deep architecture. Architecture overview maps explaining the product from install through runtime through governance through FinOps. Richer hierarchical explanation of how the platform is used end to end.
- **Postman**: N/A.
- **Scripts/Examples**: N/A.

## Acceptance Criteria

1. Docs hierarchy is feature-oriented rather than file-oriented
2. Landing map mirrors major feature families and bundle structure
3. Mermaid architecture diagrams present for every major subsystem
4. Progressive disclosure separates onboarding, operations, and deep architecture
5. FEATURE-STATUS.md dashboard updated
