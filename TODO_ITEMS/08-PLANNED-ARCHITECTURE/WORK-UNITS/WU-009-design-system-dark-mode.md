# WU-009: Design System and Dark-Mode Refresh

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - D (Design System, Documentation Architecture, and Repo Systemization)
- **Target**: 08-PLANNED-ARCHITECTURE/UI theme refresh and dark-mode redesign
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| UI theme refresh and dark-mode redesign | PARTIAL | PARTIAL | PARTIAL | MISSING | N/A | MISSING | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. This is a cross-app design system concern.

## Cross-Feature Dependencies

- All feature families — design tokens and visual language apply across every surface
- `01-ORG-AND-ACCESS` — scope visual language (platform, org, workspace, access-group, API-key)
- `03-OBSERVE` — data-dense operator pages need density modes
- `07-PLATFORM-AND-UTILITY` — platform admin layout shells

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — UI theme refresh row
- `FEATURE-STATUS.md` — 08-D delivery counts

## Scope

- **Backend**: Define design token schema or config artifacts. Semantic status mappings for platform state, severity, scope, and runtime state.
- **UI**: Cross-app design token system for colors, spacing, typography, elevation, status, severity, and scope indicators. Richer dark-mode palette with better contrast, more intentional accent use, and clearer operational-state differentiation. Consistent layout shells for platform admin, org admin, gateway admin, and observability surfaces. Visual language for scope so platform, org, workspace, access-group, and API-key contexts are instantly recognizable. Data-density modes for heavy operator pages.
- **Docs**: Document the design token system and visual language guidelines.
- **Postman**: N/A.
- **Scripts/Examples**: N/A.

## Acceptance Criteria

1. Design token system covers colors, spacing, typography, status, and scope
2. Dark mode is intentional with proper contrast and accent use
3. Consistent layout shells across admin and operator surfaces
4. Scope contexts (platform, org, workspace, access-group, API-key) are visually distinct
5. FEATURE-STATUS.md dashboard updated
