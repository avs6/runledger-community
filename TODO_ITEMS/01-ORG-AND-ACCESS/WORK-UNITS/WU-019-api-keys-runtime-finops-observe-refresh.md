# WU-019: API Keys Runtime FinOps and Observe Refresh

- **Status**: DONE
- **Bundle**: 01-Org & Access - Bundle B (Identity and Scope Control)
- **Target**: 01-ORG-AND-ACCESS/API keys (`/api-keys`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: API keys | FinOps: Budget detail | 01x05 | GAP | PARTIAL |
| Org: API keys | FinOps: Budget overrides | 01x05 | GAP | PARTIAL |
| Org: API keys | Observe: Analytics overview | 01x03 | PARTIAL | STRONG |
| Org: API keys | Observe: Runs list | 01x03 | PARTIAL | STRONG |
| Org: API keys | Observe: Run detail | 01x03 | PARTIAL | STRONG |
| Org: API keys | Observe: Request flow | 01x03 | PARTIAL | STRONG |
| Org: API keys | Observe: Request explorer | 01x03 | PARTIAL | STRONG |
| Org: API keys | Observe: Model usage | 01x03 | PARTIAL | STRONG |
| Org: API keys | Observe: Analytics economics | 01x03 | PARTIAL | STRONG |
| Org: API keys | Observe: Cost and savings | 01x03 | PARTIAL | STRONG |
| Org: API keys | Gateway: Provider profiles | 01x02 | PARTIAL | STRONG |
| Org: API keys | Gateway: Guardrails | 01x02 | PARTIAL | STRONG |
| Org: API keys | Safety: Approvals | 01x04 | PARTIAL | STRONG |
| Org: API keys | Safety: Data capture | 01x04 | PARTIAL | STRONG |
| Org: API keys | Safety: Alert rules | 01x04 | PARTIAL | STRONG |
| Org: API keys | Safety: Audit log | 01x04 | PARTIAL | STRONG |
| Org: API keys | Safety: Governance pack | 01x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — API keys row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — API keys cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of API keys
- `03-OBSERVE/COHESION-MATRIX.md` — their view of API keys
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of API keys
- `05-FINOPS/COHESION-MATRIX.md` — their view of API keys
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 1.5 if delivery changes

## Scope

- **Backend**: Add or normalize API-key usage, budget-tier, runtime-policy, and evidence linkage across core services.
- **UI**: Make `/api-keys` a true operational identity surface with links into usage, spend, alerting, and audit evidence.
- **Docs**: Document API keys as runtime, quota, spend, and evidence scope.
- **Postman**: Extend requests if new key-usage or key-summary endpoints are added.
- **Scripts/Examples**: Add API-key-centric investigation and rotation/evidence examples.

## Acceptance Criteria

1. API keys become a first-class dimension for runtime investigation, spend interpretation, and governance evidence.
2. Operators can move from an API key to its relevant observe, gateway, and governance owner surfaces.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
