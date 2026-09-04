# WU-004: Runtime Scope Model Definition

- **Status**: COMPLETED
- **Bundle**: 08-Planned Architecture - B (Runtime Governance and Policy Enforcement Deepening)
- **Target**: 08-PLANNED-ARCHITECTURE/Scope-aware runtime governance enforcement deepening
- **Created**: 2026-08-15
- **Completed**: 2026-09-03

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Scope-aware runtime governance enforcement | OK | OK | OK | OK | OK | OK | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. Gaps derived from GAP-MATRIX and BLUEPRINT cross-feature integration requirements.

## Cross-Feature Dependencies

- `01-ORG-AND-ACCESS` — workspace, access-group, API-key, and org identity model
- `02-GATEWAY-AND-ROUTING` — runtime enforcement on gateway hot path
- `04-SAFETY-AND-GOVERNANCE` — tool registry and tool policies as control-plane inputs

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — scope-aware governance row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — governance enforcement depth
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — scope identity propagation
- `FEATURE-STATUS.md` — 08-B delivery counts

## Scope

- **Backend**: Formalize workspace, access-group, API-key, and org identity propagation on the runtime path. Define explicit scope context objects that the Rust data plane can consume. Move beyond coarse tool/action matching to incorporate richer scope constraints. Create policy-decision records with scope context.
- **UI**: Policy-decision explanation views showing scope inputs. Scope-aware evidence filters in governance and observability surfaces.
- **Docs**: Document the runtime scope model and how identity propagates through enforcement.
- **Postman**: Add policy-decision explain endpoints.
- **Scripts/Examples**: Add examples demonstrating scope-aware enforcement decisions.

## Acceptance Criteria

1. Runtime scope model formalized with workspace, access-group, API-key, and org identity
2. Scope context objects consumable by Rust data plane
3. Policy decisions reference scope inputs beyond tool/action matching
4. Documentation covers the runtime scope model
5. FEATURE-STATUS.md dashboard updated
