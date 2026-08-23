# WU-013: Provider Profiles Runtime FinOps and Governance Refresh

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - Bundle A (Provider Catalog and Routing Control Plane)
- **Target**: 02-GATEWAY-AND-ROUTING/Provider profiles (`/provider-profiles`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-22

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Provider profiles | FinOps: Budget notifications | 02x05 | N/A | PARTIAL |
| Gateway: Provider profiles | FinOps: Ledger | 02x05 | N/A | PARTIAL |
| Gateway: Provider profiles | Org: Users | 02x01 | GAP | PARTIAL |
| Gateway: Provider profiles | Org: Access groups | 02x01 | GAP | PARTIAL |
| Gateway: Provider profiles | Observe: Workspace dashboard | 02x03 | N/A | PARTIAL |
| Gateway: Provider profiles | Observe: Monitoring | 02x03 | N/A | PARTIAL |
| Gateway: Provider profiles | Safety: MCP servers | 02x04 | N/A | PARTIAL |
| Gateway: Provider profiles | Safety: Search tools | 02x04 | N/A | PARTIAL |
| Gateway: Provider profiles | Safety: Data capture | 02x04 | N/A | PARTIAL |
| Gateway: Provider profiles | Build: Playground | 02x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/GAP-MATRIX.md` — Provider profiles row
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Provider profiles cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Provider profiles
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Provider profiles
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Provider profiles
- `05-FINOPS/COHESION-MATRIX.md` — their view of Provider profiles
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Provider profiles
- `02-GATEWAY-AND-ROUTING/DELIVERY-STATUS.md` — 4.2 if delivery surfaces change

## Scope

- **Backend**: Strengthen provider-profile summary data for budgeting, evidence, runtime capability posture, and workspace/user scope visibility.
- **UI**: Make provider profiles a real runtime catalog with drill-through into spend, usage, and governance-adjacent surfaces.
- **Docs**: Clarify provider profiles as pricing-aware runtime inventory, not just CRUD metadata.
- **Postman**: Add any new provider-summary or evidence-oriented requests.
- **Scripts/Examples**: Add a provider-profile flow covering sync, pricing, budget posture, and runtime consumption.

## Acceptance Criteria

1. Provider profiles expose real downstream runtime, spend, and governance posture.
2. Operators can move from a provider profile into the relevant owner surfaces for budgets, usage, and evidence.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
