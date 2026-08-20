# WU-012: Prompt Detail Runtime Loop Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - A (Interactive Build Surfaces)
- **Target**: 06-BUILD-AND-IMPROVE/prompt-detail
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Prompt detail and versions | Org: AI hub | 06x01 | PARTIAL | STRONG |
| Build: Prompt detail and versions | Gateway: Provider profiles | 06x02 | PARTIAL | STRONG |
| Build: Prompt detail and versions | Gateway: Model gateway | 06x02 | PARTIAL | STRONG |
| Build: Prompt detail and versions | FinOps: Chargeback | 06x05 | PARTIAL | STRONG |
| Build: Prompt detail and versions | Observe: Runs list | 06x03 | PARTIAL | STRONG |
| Build: Prompt detail and versions | Observe: Request flow | 06x03 | PARTIAL | STRONG |
| Build: Prompt detail and versions | Build: Optimization opportunities | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Prompt detail and versions row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Prompt detail cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Prompt Detail as the runtime-aware version and promotion surface.
- **UI**: Tighten run, request, provider, and optimization context around prompt versions.
- **Docs**: Describe prompt detail as part of the execution and improvement loop.
- **Postman**: Keep version, promotion, and linked-runtime flows aligned.
- **Scripts/Examples**: Add a prompt-version scenario that links promotion to observed runtime and cost deltas.

## Acceptance Criteria

1. Prompt Detail is re-audited as a runtime-loop surface
2. Execution, observability, and optimization relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
