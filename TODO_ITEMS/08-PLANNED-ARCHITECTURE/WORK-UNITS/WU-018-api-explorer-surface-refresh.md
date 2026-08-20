# WU-018: API Explorer Surface Refresh

- **Status**: NOT_STARTED
- **Bundle**: 08-Architecture - C (Pipeline, API, and Embedded Product Surfaces)
- **Target**: 08-PLANNED-ARCHITECTURE/api-explorer
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

This planned-architecture family does not yet have a dedicated `COHESION-MATRIX.md`.
Close this work through `GAP-MATRIX.md`, `BLUEPRINT.md`, and the paired matrices below.

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` - API explorer row
- `08-PLANNED-ARCHITECTURE/BLUEPRINT.md` - Bundle C API-surface framing
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md`
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit generated API exploration as the canonical contract surface instead of a Postman-first fallback.
- **UI**: Define the embedded explorer and route naming expectations for the in-product experience.
- **Docs**: Normalize `/reference` versus planned `/api-docs` direction and reduce ambiguity.
- **Postman**: Reframe Postman as a paired asset rather than the primary discovery surface.
- **Scripts/Examples**: Add API recipe and explorer-usage examples that align with the generated reference story.

## Acceptance Criteria

1. API Explorer is re-audited as a first-class generated surface
2. Route naming, ownership, and product embedding implications are explicitly covered
3. Paired matrices and blueprint references are updated consistently
4. FEATURE-STATUS.md is updated
