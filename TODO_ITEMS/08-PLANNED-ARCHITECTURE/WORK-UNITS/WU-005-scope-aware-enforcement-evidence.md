# WU-005: Scope-Aware Enforcement and Evidence Loop

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - B (Runtime Governance and Policy Enforcement Deepening)
- **Target**: 08-PLANNED-ARCHITECTURE/Scope-aware runtime governance enforcement deepening
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Scope-aware runtime governance enforcement | PARTIAL | N/A | PARTIAL | PARTIAL | MISSING | MISSING | GAP-MATRIX §9 |

Note: Continues from WU-004 scope model definition. This WU covers enforcement deepening and evidence closure.

## Cross-Feature Dependencies

- `02-GATEWAY-AND-ROUTING` — Rust hot-path enforcement with scope context
- `03-OBSERVE` — scope-aware decisions visible in request analysis and audit evidence
- `04-SAFETY-AND-GOVERNANCE` — governance evidence and violation lineage
- `01-ORG-AND-ACCESS` — scope identity enrichment on enforcement outcomes

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — scope-aware governance row
- `03-OBSERVE/COHESION-MATRIX.md` — governance evidence in observe surfaces
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — enforcement evidence depth
- `FEATURE-STATUS.md` — 08-B delivery counts

## Scope

- **Backend**: Enforce broader scope-aware policies on the hot path using the scope model from WU-004. Expose policy decisions, scope context, and violations in observability and governance evidence surfaces. Create richer violation ingestion and event publishing contracts. Add enriched violation/audit/observability records with scope lineage.
- **UI**: Runtime governance status and friction summaries. Stronger scope-aware evidence filters. Violation lineage views showing scope context. Governance heatmaps by workspace or access group.
- **Docs**: Document scope-aware enforcement outcomes and evidence flow.
- **Postman**: Add violation and enforcement evidence endpoints with scope context.
- **Scripts/Examples**: Add examples inspecting enforcement decisions with scope context and reviewing governance friction by workspace.

## Acceptance Criteria

1. Runtime enforcement incorporates scope-aware policy evaluation
2. Enforcement decisions visible with full scope lineage in observe and governance surfaces
3. Violation records enriched with workspace, access-group, and API-key context
4. Operators can inspect why enforcement happened with scope explanation
5. FEATURE-STATUS.md dashboard updated
