# WU-020: Tags Taxonomy Attribution Refresh

- **Status**: COMPLETED
- **Bundle**: 04-Safety - C (Data Protection, Security, and Taxonomy)
- **Target**: 04-SAFETY-AND-GOVERNANCE/tags
- **Created**: 2026-08-16
- **Completed**: 2026-08-31

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tags | FinOps: Budget detail | 04x05 | PARTIAL | STRONG |
| Safety: Tags | FinOps: Chargeback | 04x05 | PARTIAL | STRONG |
| Safety: Tags | Org: Organization profile | 04x01 | PARTIAL | STRONG |
| Safety: Tags | Org: Workspaces | 04x01 | PARTIAL | STRONG |
| Safety: Tags | Gateway: Provider profiles | 04x02 | STRONG | STRONG |
| Safety: Tags | Observe: Runs list | 04x03 | PARTIAL | STRONG |
| Safety: Tags | Observe: Request flow | 04x03 | PARTIAL | STRONG |
| Safety: Tags | Safety: Tool policies | 04x04 | PARTIAL | STRONG |
| Safety: Tags | Safety: Audit log | 04x04 | PARTIAL | STRONG |
| Safety: Tags | Safety: Governance pack | 04x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` - Tags row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - Tags cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - org and workspace classification view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - provider attribution and routing-context view
- `03-OBSERVE/COHESION-MATRIX.md` - run and request attribution view
- `05-FINOPS/COHESION-MATRIX.md` - budget detail and chargeback attribution view

## Scope

- **Backend**: Re-audit Tags as the shared taxonomy and attribution layer across governance, runtime, observability, and FinOps surfaces.
- **UI**: Show where tags drive grouping, attribution, filtering, and evidence packaging across the suite.
- **Docs**: Position Tags as a cross-suite classification primitive rather than a local metadata helper.
- **Postman**: Keep taxonomy, auto-tagging, and downstream usage expectations aligned.
- **Scripts/Examples**: Add examples showing tag propagation into provider analytics, request review, and chargeback attribution.

## Acceptance Criteria

1. Tags are re-audited as a shared attribution primitive
2. Runtime, observability, and FinOps relationships are explicitly covered
3. Policy, audit, and governance-pack relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
