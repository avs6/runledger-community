# WU-001: Interactive Build × Org & Gateway Scope

- **Status**: NOT_STARTED
- **Bundle**: 06-Build & Improve - A (Interactive Build Surfaces)
- **Target**: 06-BUILD-AND-IMPROVE/Playground, Prompts list
- **Created**: 2026-08-15
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Playground | Org: Workspaces | 06×01 | PARTIAL | STRONG |
| Build: Playground | Org: API keys | 06×01 | PARTIAL | STRONG |
| Build: Playground | Org: AI hub | 06×01 | PARTIAL | STRONG |
| Build: Playground | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Playground | Gateway: Guardrails | 06×02 | PARTIAL | STRONG |
| Build: Playground | Gateway: Response cache | 06×02 | PARTIAL | STRONG |
| Build: Playground | Gateway: Rate limits | 06×02 | PARTIAL | STRONG |
| Build: Prompts list | Org: Workspaces | 06×01 | PARTIAL | STRONG |
| Build: Prompts list | Org: AI hub | 06×01 | PARTIAL | STRONG |
| Build: Prompts list | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Prompts list | Gateway: Model gateway | 06×02 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Playground/Prompts × Org/Gateway cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Playground/Prompts
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Playground/Prompts
- `FEATURE-STATUS.md` — 06-A × 01/02 counts

## Scope

- **Backend**: Playground should consume workspace, API-key, and AI hub model catalog context. Provider profiles, guardrails, cache, and rate-limit posture should be available as build-time configuration context. Prompts should show workspace scope and gateway model/provider awareness.
- **UI**: Playground should display active workspace, API-key identity, and AI hub model context. Provider, guardrail, cache, and rate-limit configuration should be visible during experimentation. Prompts list should show workspace scope and model/provider associations.
- **Docs**: Document playground gateway-aware experimentation and prompt workspace scope.
- **Postman**: Add workspace and gateway context to playground and prompt endpoints.
- **Scripts/Examples**: Add example using playground with explicit workspace/API-key/provider context.

## Acceptance Criteria

1. Playground shows workspace, API-key, and AI hub context
2. Gateway configuration (provider, guardrails, cache, rate limits) visible during experimentation
3. Prompts list shows workspace scope and model/provider associations
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
