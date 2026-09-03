# WU-007: Optimization × Observe Bridge

- **Status**: COMPLETED
- **Bundle**: 06-Build & Improve - D (Optimization and Decision Support)
- **Target**: 06-BUILD-AND-IMPROVE/Optimization opportunities, Optimization simulator, Model scorecards
- **Created**: 2026-08-15
- **Completed**: 2026-09-02

## Completion Notes

- Backend: `OptimizationObservePosture` Pydantic schema + `GET /analytics/optimization-observe-posture` endpoint querying AgentRun, ProviderCall, ResponseCacheConfig for runs/requests/models/cost context
- TypeScript: `OptimizationObservePosture` interface + `getOptimizationObservePosture` API function
- UI: Cyan "Observe & Runtime Context" card on Optimization Opportunities, Optimization Simulator, Model Scorecards pages showing runs 30d, provider calls 30d, distinct models, total cost 30d with drill-through links to Analytics Overview, Runs, Request Flow, Request Explorer, Model Usage
- Docs: Added observe context sections to optimization.mdx, optimization-simulator.mdx, model-scorecards.mdx
- Postman: Added "Optimization Observe Posture" entry
- Example: `examples/136_optimization_observe_posture.py`

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Optimization opportunities | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Optimization opportunities | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Optimization opportunities | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Optimization opportunities | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Optimization opportunities | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Optimization opportunities | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Optimization simulator | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Optimization simulator | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Optimization simulator | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Optimization simulator | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Optimization simulator | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Optimization simulator | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Model scorecards | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Model scorecards | Observe: Runs list | 06×03 | PARTIAL | STRONG |
| Build: Model scorecards | Observe: Run detail | 06×03 | PARTIAL | STRONG |
| Build: Model scorecards | Observe: Request flow | 06×03 | PARTIAL | STRONG |
| Build: Model scorecards | Observe: Request explorer | 06×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Opt opps/Opt sim/Scorecards × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of optimization surfaces
- `FEATURE-STATUS.md` — 06-D × 03 counts

## Scope

- **Backend**: Optimization opportunities should cite source runs, request flows, and model usage as evidence for recommendations. Simulator should consume analytics and run data for accurate what-if modeling. Model scorecards should link to run-level and request-level performance evidence.
- **UI**: Optimization opportunities should show run evidence, request flow traces, and model usage behind each recommendation. Simulator should display analytics context and run data supporting simulated scenarios. Model scorecards should deep-link to runs, request flows, and request explorer for performance drill-in.
- **Docs**: Document the observe-to-optimization evidence chain.
- **Postman**: Add observe evidence context to optimization and scorecard endpoints.
- **Scripts/Examples**: Add example viewing optimization recommendation with linked run evidence and model usage.

## Acceptance Criteria

1. Optimization opportunities cite run evidence and request flow traces
2. Simulator consumes analytics and run data for scenario modeling
3. Model scorecards link to run-level and request-level performance evidence
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
