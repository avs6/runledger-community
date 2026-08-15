# WU-002: Interactive Build × Observe Bridge

- **Status**: NOT_STARTED
- **Bundle**: 06-Build & Improve - A (Interactive Build Surfaces)
- **Target**: 06-BUILD-AND-IMPROVE/Playground, Prompt detail and versions
- **Created**: 2026-08-15
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Playground | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Playground | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Playground | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Playground | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Playground | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Playground | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Playground | Observe: Cost and savings | 06×03 | PARTIAL | STRONG |
| Build: Prompt detail | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Prompt detail | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Prompt detail | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Prompt detail | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Prompt detail | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Prompt detail | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Prompt detail | Observe: Cost and savings | 06×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Playground/Prompt detail × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Playground/Prompt detail
- `FEATURE-STATUS.md` — 06-A × 03 counts

## Scope

- **Backend**: Playground sessions should link to observable runs, request flows, and cost data. Prompt detail should expose runtime performance, model usage, and cost/savings impact for each version. Observe surfaces should be reachable from build context.
- **UI**: Playground should show recent runs, request flow traces, and cost/savings for sessions. Prompt detail should display version-level analytics, model usage trends, and cost impact. Deep links to Observe surfaces from playground and prompt views.
- **Docs**: Document the build-to-observe feedback loop for playground and prompt workflows.
- **Postman**: Add observability context to playground and prompt detail endpoints.
- **Scripts/Examples**: Add example viewing prompt version performance and playground session cost impact.

## Acceptance Criteria

1. Playground sessions link to runs, request flow, and cost/savings data
2. Prompt detail shows version-level analytics and model usage trends
3. Deep links to Observe surfaces available from build context
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
