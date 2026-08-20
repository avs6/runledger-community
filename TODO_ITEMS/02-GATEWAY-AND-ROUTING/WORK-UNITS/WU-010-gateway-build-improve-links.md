# WU-010: Gateway Build & Improve Integration

- **Status**: NOT_STARTED
- **Bundle**: 02-Gateway & Routing - A/B/C (all bundles)
- **Target**: 02-GATEWAY-AND-ROUTING (all features × Build & Improve)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Provider profiles | Build: Playground | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Prompts list | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Prompt detail and versions | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Workflows list | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Workflow detail | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Workflow run detail | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Evaluation studio | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Experiments | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Replay lab | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Replay experiment detail | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Optimization opportunities | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Build: Optimization simulator | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Prompts list | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Prompt detail and versions | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Agents list | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Agent detail | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Evaluation studio | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Experiments | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Replay lab | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Replay experiment detail | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Model scorecards | 02×06 | PARTIAL | STRONG |
| Gateway: Model gateway | Build: Runbooks | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Playground | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Agents list | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Agent detail | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Workflows list | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Workflow detail | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Workflow run detail | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Evaluation studio | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Experiments | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Replay lab | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Replay experiment detail | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Optimization opportunities | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Optimization simulator | 02×06 | PARTIAL | STRONG |
| Gateway: Guardrails | Build: Runbooks | 02×06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — all features × Build cells
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Gateway features
- `FEATURE-STATUS.md` — 02-A/B/C × 06 counts

## Scope

- **Backend**: Build surfaces should inherit gateway context: playground should show which provider/route/guardrails are active, prompts and workflows should carry provider/route context, evaluation and replay should show the gateway path used, optimization should reference provider economics and guardrail cost.
- **UI**: Build surfaces should show gateway context where execution involves routing: active provider, route, guardrails. Evaluation and replay results should link to the gateway configuration that was active. Optimization should reference provider and cache economics.
- **Docs**: Document how gateway context flows into build and experimentation surfaces.
- **Postman**: Add gateway context to execution-facing build endpoints.
- **Scripts/Examples**: Add example running an experiment and viewing the gateway route and guardrail context that applied.

## Acceptance Criteria

1. Playground shows active provider/route/guardrail context
2. Prompts and workflows carry provider/route awareness
3. Evaluation and replay show gateway path used
4. Optimization references provider economics and guardrail cost
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
