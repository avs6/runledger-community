# WU-017: Pipeline Studio Concept Refresh

- **Status**: NOT_STARTED
- **Bundle**: 08-Architecture - C (Pipeline, API, and Embedded Product Surfaces)
- **Target**: 08-PLANNED-ARCHITECTURE/pipeline-studio
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

This planned-architecture family does not yet have a dedicated `COHESION-MATRIX.md`.
Close this work through `GAP-MATRIX.md`, `BLUEPRINT.md`, and the paired matrices below.

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` - pipeline studio row
- `08-PLANNED-ARCHITECTURE/BLUEPRINT.md` - Bundle C pipeline-surface framing
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit the conceptual APIs and model needed for a workflow-centered pipeline studio.
- **UI**: Define the new visualization and authoring surface without splitting into separate diagram and builder products.
- **Docs**: Tighten the product concept so it is grounded in existing runtime and workflow primitives.
- **Postman**: Identify what generated or future API coverage would be required once the surface exists.
- **Scripts/Examples**: Add concept-level scenarios showing how pipeline views would connect routing, governance, and FinOps.

## Acceptance Criteria

1. Pipeline Studio is re-audited as one coherent future surface
2. Product-model and cross-feature implications are explicitly covered
3. Paired matrices and blueprint references are updated consistently
4. FEATURE-STATUS.md is updated
