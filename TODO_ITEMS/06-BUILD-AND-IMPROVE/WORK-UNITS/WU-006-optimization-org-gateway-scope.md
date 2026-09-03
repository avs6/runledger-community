# WU-006: Optimization × Org & Gateway Scope

- **Status**: COMPLETED
- **Bundle**: 06-Build & Improve - D (Optimization and Decision Support)
- **Target**: 06-BUILD-AND-IMPROVE/Optimization opportunities, Optimization simulator, Model scorecards
- **Created**: 2026-08-15
- **Completed**: 2026-09-02

## Completion Notes

- Backend: `OptimizationOrgGatewayPosture` Pydantic schema + `GET /analytics/optimization-org-gateway-posture` endpoint querying WorkspaceUser, ApiKey, HubModel, GatewayRoute, GuardrailRule, ResponseCacheConfig, GatewayPassThroughEndpoint
- TypeScript: `OptimizationOrgGatewayPosture` interface + `getOptimizationOrgGatewayPosture` API function
- UI: Blue "Organization & Access Context" card + violet "Gateway & Routing Context" card on Optimization Opportunities, Optimization Simulator, Model Scorecards pages with drill-through links to Organization, API Keys, AI Hub, Model Gateway, Routes, Guardrails, Response Cache, Rate Limits
- Docs: Added "Organization, Gateway & Observe Context" sections to optimization.mdx, optimization-simulator.mdx, model-scorecards.mdx
- Postman: Added "Optimization Org Gateway Posture" entry
- Example: `examples/135_optimization_org_gateway_posture.py`

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Optimization opportunities | Org: Workspaces | 06×01 | PARTIAL | STRONG |
| Build: Optimization opportunities | Org: API keys | 06×01 | PARTIAL | STRONG |
| Build: Optimization opportunities | Org: AI hub | 06×01 | PARTIAL | STRONG |
| Build: Optimization opportunities | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Optimization opportunities | Gateway: Guardrails | 06×02 | PARTIAL | STRONG |
| Build: Optimization opportunities | Gateway: Response cache | 06×02 | PARTIAL | STRONG |
| Build: Optimization opportunities | Gateway: Rate limits | 06×02 | PARTIAL | STRONG |
| Build: Optimization simulator | Org: Workspaces | 06×01 | PARTIAL | STRONG |
| Build: Optimization simulator | Org: API keys | 06×01 | PARTIAL | STRONG |
| Build: Optimization simulator | Org: AI hub | 06×01 | PARTIAL | STRONG |
| Build: Optimization simulator | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Optimization simulator | Gateway: Guardrails | 06×02 | PARTIAL | STRONG |
| Build: Optimization simulator | Gateway: Response cache | 06×02 | PARTIAL | STRONG |
| Build: Optimization simulator | Gateway: Rate limits | 06×02 | PARTIAL | STRONG |
| Build: Model scorecards | Org: Workspaces | 06×01 | PARTIAL | STRONG |
| Build: Model scorecards | Gateway: Model gateway | 06×02 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Opt opps/Opt sim/Scorecards × Org/Gateway cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of optimization surfaces
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of optimization surfaces
- `FEATURE-STATUS.md` — 06-D × 01/02 counts

## Scope

- **Backend**: Optimization opportunities should be scoped to workspace, API-key, and AI hub model catalog. Simulator should consume provider profiles, guardrails, cache, and rate-limit posture for accurate simulations. Model scorecards should show workspace-level model performance and gateway model routing context.
- **UI**: Optimization opportunities should show workspace scope and API-key filtering. Simulator should display provider, guardrail, cache, and rate-limit configuration context for scenario modeling. Model scorecards should show workspace-scoped performance and model gateway routing associations.
- **Docs**: Document optimization workspace scope and gateway-aware simulation.
- **Postman**: Add org and gateway scope context to optimization and scorecard endpoints.
- **Scripts/Examples**: Add example running optimization simulator with explicit provider and guardrail context.

## Acceptance Criteria

1. Optimization opportunities scoped to workspace and API-key identity
2. Simulator consumes provider, guardrail, cache, and rate-limit posture
3. Model scorecards show workspace scope and gateway model routing
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
