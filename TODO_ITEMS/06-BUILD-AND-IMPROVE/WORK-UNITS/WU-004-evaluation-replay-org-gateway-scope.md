# WU-004: Evaluation & Replay × Org & Gateway Scope

- **Status**: COMPLETED
- **Bundle**: 06-Build & Improve - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/Evaluation studio, Experiments, Replay lab
- **Created**: 2026-08-15
- **Completed**: 2026-09-02

## Completion Notes

- Backend: `EvalReplayOrgGatewayPosture` Pydantic schema + `GET /analytics/eval-replay-org-gateway-posture` endpoint querying WorkspaceUser, AccessGroup, ApiKey, HubModel, GatewayRoute, GuardrailRule, ResponseCacheConfig, RoutingPolicy
- TypeScript: `EvalReplayOrgGatewayPosture` interface + `getEvalReplayOrgGatewayPosture` API function
- UI: Blue "Organization & Access Context" card + violet "Gateway & Routing Context" card on Evaluation Studio, Experiments, Replay Lab pages with drill-through links to Organization, Access Groups, API Keys, AI Hub, Model Gateway, Routes, Guardrails, Response Cache
- Docs: Added "Organization, Gateway & Observe Context" sections to evaluations.mdx and replay-lab.mdx
- Postman: Added "Eval Replay Org Gateway Posture" entry
- Example: `examples/133_eval_replay_org_gateway_posture.py`

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Evaluation studio | Org: Access groups | 06×01 | PARTIAL | STRONG |
| Build: Evaluation studio | Org: API keys | 06×01 | PARTIAL | STRONG |
| Build: Evaluation studio | Org: AI hub | 06×01 | PARTIAL | STRONG |
| Build: Evaluation studio | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Evaluation studio | Gateway: Model gateway | 06×02 | PARTIAL | STRONG |
| Build: Evaluation studio | Gateway: Guardrails | 06×02 | PARTIAL | STRONG |
| Build: Experiments | Org: Workspaces | 06×01 | PARTIAL | STRONG |
| Build: Experiments | Org: API keys | 06×01 | PARTIAL | STRONG |
| Build: Experiments | Org: AI hub | 06×01 | PARTIAL | STRONG |
| Build: Experiments | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Experiments | Gateway: Model gateway | 06×02 | PARTIAL | STRONG |
| Build: Experiments | Gateway: Guardrails | 06×02 | PARTIAL | STRONG |
| Build: Replay lab | Org: Workspaces | 06×01 | PARTIAL | STRONG |
| Build: Replay lab | Org: API keys | 06×01 | PARTIAL | STRONG |
| Build: Replay lab | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Replay lab | Gateway: Model gateway | 06×02 | PARTIAL | STRONG |
| Build: Replay lab | Gateway: Guardrails | 06×02 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Eval studio/Experiments/Replay × Org/Gateway cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Eval studio/Experiments/Replay
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Eval studio/Experiments/Replay
- `FEATURE-STATUS.md` — 06-C × 01/02 counts

## Scope

- **Backend**: Evaluation studio should consume access-group, API-key, and AI hub context for scoped evaluations. Experiments should respect workspace scope and API-key identity. Replay should inherit workspace scope and API-key context from source runs. Provider profiles, model gateway, and guardrail configuration should be available as evaluation and replay runtime context.
- **UI**: Evaluation studio should show access-group and API-key scope. Experiments should display workspace context and model/provider configuration. Replay should show source workspace, API-key, and gateway configuration. Provider, model, and guardrail context should be visible during evaluation and replay sessions.
- **Docs**: Document evaluation and replay workspace/gateway scope integration.
- **Postman**: Add org and gateway scope context to evaluation, experiment, and replay endpoints.
- **Scripts/Examples**: Add example running scoped evaluation with explicit workspace, API-key, and provider context.

## Acceptance Criteria

1. Evaluation studio shows access-group, API-key, and AI hub scope
2. Experiments display workspace and model/provider configuration
3. Replay inherits and shows source workspace and gateway context
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
