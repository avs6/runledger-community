# WU-018: Access Groups Scope Propagation Refresh

- **Status**: DONE
- **Bundle**: 01-Org & Access - Bundle B (Identity and Scope Control)
- **Target**: 01-ORG-AND-ACCESS/Access groups (`/access-groups`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Access groups | FinOps: Budget detail | 01x05 | GAP | PARTIAL |
| Org: Access groups | FinOps: Billing period detail | 01x05 | GAP | PARTIAL |
| Org: Access groups | Observe: Runs list | 01x03 | GAP | PARTIAL |
| Org: Access groups | Observe: Run detail | 01x03 | GAP | PARTIAL |
| Org: Access groups | Observe: Request flow | 01x03 | GAP | PARTIAL |
| Org: Access groups | Observe: Request explorer | 01x03 | GAP | PARTIAL |
| Org: Access groups | Gateway: Provider profiles | 01x02 | PARTIAL | STRONG |
| Org: Access groups | Gateway: Model gateway | 01x02 | PARTIAL | STRONG |
| Org: Access groups | Gateway: Rate limits | 01x02 | PARTIAL | STRONG |
| Org: Access groups | Safety: Tool registry | 01x04 | PARTIAL | STRONG |
| Org: Access groups | Safety: Tool policies | 01x04 | PARTIAL | STRONG |
| Org: Access groups | Safety: Approvals | 01x04 | PARTIAL | STRONG |
| Org: Access groups | Safety: Data capture | 01x04 | PARTIAL | STRONG |
| Org: Access groups | Safety: Audit log | 01x04 | PARTIAL | STRONG |
| Org: Access groups | Build: Playground | 01x06 | PARTIAL | STRONG |
| Org: Access groups | Build: Workflows list | 01x06 | PARTIAL | STRONG |
| Org: Access groups | Build: Evaluation studio | 01x06 | PARTIAL | STRONG |
| Org: Access groups | Build: Optimization simulator | 01x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Access groups row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Access groups cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Access groups
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Access groups
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Access groups
- `05-FINOPS/COHESION-MATRIX.md` — their view of Access groups
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Access groups
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 1.6 if delivery changes

## Scope

- **Backend**: Propagate access-group identity deeper into runtime, observability, spend attribution, and governance evidence.
- **UI**: Make access groups visible as a real scope primitive in investigation, build, and runtime-adjacent surfaces.
- **Docs**: Clarify access groups as a first-class scope/governance concept rather than an optional grouping helper.
- **Postman**: Add missing access-group coverage and any new scope-aware query contracts.
- **Scripts/Examples**: Add an access-group propagation walkthrough across runtime and investigation.

## Acceptance Criteria

1. Access-group scope is visible in runtime, observe, governance, and build owner surfaces where it materially belongs.
2. Access groups can be used as an investigation and attribution dimension rather than only an admin CRUD object.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
