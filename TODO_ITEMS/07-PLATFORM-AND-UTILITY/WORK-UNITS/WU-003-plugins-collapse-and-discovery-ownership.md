# WU-003: Plugins collapse and discovery ownership cleanup

- **Status**: COMPLETED
- **Bundle**: Platform & Utility - Utility Route Collapse and Discovery Ownership
- **Target**: 07-PLATFORM-AND-UTILITY/Plugins (`/plugins`)
- **Created**: 2026-08-15
- **Completed**: 2026-09-03

## Completion Notes

No backend changes needed — plugin CRUD already complete. Docs: Created `docs/administration/plugins.mdx` documenting collapsed ownership model, backend API table, ownership boundaries (Onboarding owns discovery, Evaluation studio consumes connections, MCP governance uses CRUD). Postman: Added Plugins folder with 7 requests (Create, List, Get, Update, Deactivate, Executions, Seed Defaults). Example 159 covers full plugin lifecycle. All target cohesion cells updated per scope.

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Plugins | Onboarding | 07x01 | STRONG | STRONG |
| Plugins | Evaluation studio | 07x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - Plugins row
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - Plugins cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - their view of onboarding-owned plugin discovery
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - their view of plugin connections inside builder workflows
- `07-PLATFORM-AND-UTILITY/DELIVERY-STATUS.md` - plugin collapse support coverage

## Scope

- **Backend**: Preserve plugin-management APIs and logs without implying `/plugins` is still a first-class product owner.
- **UI**: Keep `/plugins` compatibility-only, improve redirect and handoff messaging, and ensure discovery/setup lives inside onboarding and any relevant builder entry points.
- **Docs**: Remove stale references that describe `/plugins` as an active admin destination and document onboarding as the discovery owner.
- **Postman**: Keep plugin CRUD and execution-log coverage current while clearly framing them as backend capabilities rather than proof of a top-level route owner.
- **Scripts/Examples**: Refresh setup and plugin-connection examples so they start in onboarding or builder workflows instead of a ghost `/plugins` page.

## Acceptance Criteria

1. `/plugins` remains intentionally collapsed and does not drift back into a ghost admin route.
2. Onboarding is explicit as the user-facing discovery owner for plugin and tool setup.
3. Any builder-facing plugin entry points are linked intentionally rather than through stale platform-admin references.
4. Support surfaces reflect the collapsed ownership model consistently.
5. All listed cohesion cells updated to target state.
6. All paired feature files updated.
7. `FEATURE-STATUS.md` dashboard updated.
