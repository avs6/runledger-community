# WU-012: Gateway Internal & Platform Cohesion

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - A/B/C/D (cross-bundle)
- **Target**: 02-GATEWAY-AND-ROUTING (internal family + Platform cohesion)
- **Created**: 2026-08-14
- **Completed**: 2026-08-22

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Provider profiles | Gateway: Guardrails | 02×02 | PARTIAL | STRONG |
| Gateway: Provider profiles | Gateway: Response cache | 02×02 | PARTIAL | STRONG |
| Gateway: Provider profiles | Gateway: Rate limits | 02×02 | PARTIAL | STRONG |
| Gateway: Model gateway | Gateway: Guardrails | 02×02 | PARTIAL | STRONG |
| Gateway: Model gateway | Gateway: Response cache | 02×02 | PARTIAL | STRONG |
| Gateway: Model gateway | Gateway: Rate limits | 02×02 | PARTIAL | STRONG |
| Gateway: Response cache | Gateway: Model scorecards | 02×06 | PARTIAL | STRONG |
| Gateway: Rate limits | Build: Replay lab | 02×06 | PARTIAL | STRONG |
| Gateway: Rate limits | Build: Replay experiment detail | 02×06 | PARTIAL | STRONG |
| Gateway: Rate limits | Build: Optimization opportunities | 02×06 | PARTIAL | STRONG |
| Gateway: Rate limits | Build: Optimization simulator | 02×06 | PARTIAL | STRONG |
| Gateway: Provider profiles | Platform: All organizations | 02×07 | PARTIAL | STRONG |
| Gateway: Provider profiles | Platform: Platform settings | 02×07 | PARTIAL | STRONG |
| Gateway: Model gateway | Platform: All organizations | 02×07 | PARTIAL | STRONG |
| Gateway: Model gateway | Platform: Platform settings | 02×07 | PARTIAL | STRONG |
| Gateway: Guardrails | Platform: Platform settings | 02×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — internal and Platform cells
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Gateway
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Rate limits (Build cells)
- `FEATURE-STATUS.md` — 02-Self, 02×07, 02-C×06 counts

## Scope

- **Backend**: Tighten internal gateway family cohesion: provider profiles should link to guardrail, cache, and rate-limit behavior that applies to their routes. Gateway control plane should present a unified view of all runtime controls. Platform admin should see cross-org gateway posture. Rate limits should feed into optimization and replay for experimentation context.
- **UI**: Gateway should present provider, route, guardrail, cache, and throttle controls as one coherent operator experience. Platform settings should include gateway posture defaults. Provider detail should show linked guardrail, cache, and throttle configs.
- **Docs**: Document the gateway family as one cohesive runtime system.
- **Postman**: Add internal cross-linking to gateway endpoints.
- **Scripts/Examples**: Add example walking through the full gateway operator experience from provider to route to cache to throttle.

## Acceptance Criteria

1. Provider profiles link to their guardrail, cache, and rate-limit configs
2. Gateway presents a unified runtime control experience
3. Platform admin sees cross-org gateway posture
4. Rate-limit context flows into optimization and replay
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
