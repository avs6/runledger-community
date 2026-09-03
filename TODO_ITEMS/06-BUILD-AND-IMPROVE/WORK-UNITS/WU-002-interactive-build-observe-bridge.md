# WU-002: Interactive Build × Observe Bridge

- **Status**: COMPLETED
- **Bundle**: 06-Build & Improve - A (Interactive Build Surfaces)
- **Target**: 06-BUILD-AND-IMPROVE/Playground, Prompt detail and versions
- **Created**: 2026-08-15
- **Completed**: 2026-09-02

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

## Completion Notes (2026-09-02)

- Backend: Added `PlaygroundObservePosture` schema and `GET /analytics/playground-observe-posture` endpoint returning runs context (30d/total), request flow context (provider calls, tokens), model usage context (distinct models), and cost/savings context (total cost, cache configs, estimated savings). Added `PromptDetailObservePosture` schema and `GET /analytics/prompt-detail-observe-posture` endpoint returning analytics context (prompts, versions, runs), model usage, cost (total/avg), and request context.
- UI: Added cyan "Observe & Runtime Context" posture card to Playground page with runs, provider calls, distinct models, cost, and drill-through links to Analytics Overview, Runs, Request Flow, Request Explorer, Model Usage, Cost & Savings. Added cyan "Observe & Analytics Context" posture card to Prompt detail page with same drill-through links.
- Docs: Added "Observe-Aware Experimentation" section to playground.mdx and "Observe & Analytics Context" section to prompts.mdx with curl examples.
- Postman: Added "Playground Observe Posture" and "Prompt Detail Observe Posture" entries.
- Examples: Added `130_playground_observe_posture.py` and `131_prompt_detail_observe_posture.py`.
- Audit: Updated 06-BUILD COHESION-MATRIX (Playground/Prompt detail × 7 Observe columns P→S each = 14 cells), 03-OBSERVE COHESION-MATRIX paired view, GAP-MATRIX notes, and FEATURE-STATUS counts.
