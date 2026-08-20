# WU-006: Investigation Gateway & Runtime Context

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - B (Investigation)
- **Target**: 03-OBSERVE/Runs, Run detail, Request flow, Request explorer
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Runs list | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Runs list | Gateway: Guardrails | 03×02 | PARTIAL | STRONG |
| Observe: Runs list | Gateway: Response cache | 03×02 | PARTIAL | STRONG |
| Observe: Runs list | Gateway: Rate limits | 03×02 | PARTIAL | STRONG |
| Observe: Run detail | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Run detail | Gateway: Guardrails | 03×02 | PARTIAL | STRONG |
| Observe: Run detail | Gateway: Response cache | 03×02 | PARTIAL | STRONG |
| Observe: Run detail | Gateway: Rate limits | 03×02 | PARTIAL | STRONG |
| Observe: Request flow | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Request flow | Gateway: Guardrails | 03×02 | PARTIAL | STRONG |
| Observe: Request flow | Gateway: Response cache | 03×02 | PARTIAL | STRONG |
| Observe: Request flow | Gateway: Rate limits | 03×02 | PARTIAL | STRONG |
| Observe: Request explorer | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Request explorer | Gateway: Guardrails | 03×02 | PARTIAL | STRONG |
| Observe: Request explorer | Gateway: Response cache | 03×02 | PARTIAL | STRONG |
| Observe: Request explorer | Gateway: Rate limits | 03×02 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Investigation × Gateway cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Investigation features
- `FEATURE-STATUS.md` — 03-B × 02 counts

## Scope

- **Backend**: Investigation surfaces should expose full gateway runtime context: which provider profile served the request, which route was selected, whether guardrails fired, whether cache hit/miss occurred, whether rate limiting applied. Filters for provider, guardrail outcome, and cache/throttle status.
- **UI**: Run detail and request flow should show provider profile, route decision, guardrail outcome, cache status, and throttle status inline. Request explorer should filter by these gateway dimensions. Investigation surfaces should link to provider profile, guardrails, and gateway config.
- **Docs**: Document gateway-aware investigation workflows.
- **Postman**: Add gateway runtime context to investigation endpoint responses.
- **Scripts/Examples**: Add example investigating a request through provider, route, guardrail, cache, and throttle context.

## Acceptance Criteria

1. Run detail shows provider profile, route, guardrail, cache, and throttle context
2. Request flow shows gateway runtime decisions inline
3. Request explorer filters by provider, guardrail outcome, cache status, throttle status
4. Investigation surfaces link to gateway config surfaces
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
