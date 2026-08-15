# WU-011: Repo Naming and Historical Cleanup

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - D (Design System, Documentation Architecture, and Repo Systemization)
- **Target**: 08-PLANNED-ARCHITECTURE/Broader repo naming and historical cleanup review
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Broader repo naming and historical cleanup | PARTIAL | N/A | PARTIAL | PARTIAL | N/A | PARTIAL | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. This is a cross-cutting repo-systemization concern.

## Cross-Feature Dependencies

- All feature families — naming and terminology consistency affects every subsystem
- `06-BUILD-AND-IMPROVE` — build/evaluation terminology alignment
- `04-SAFETY-AND-GOVERNANCE` — governance vocabulary consistency
- `02-GATEWAY-AND-ROUTING` — gateway naming post-Rust migration

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — repo naming cleanup row
- `FEATURE-STATUS.md` — 08-D delivery counts

## Scope

- **Backend**: Scrub leftover phase-oriented naming, stale migration language, and history-shaped labels across tests and backend code. Align function/variable/module naming with product terminology. Add repo vocabulary linting or review guidance to flag reintroduction of deprecated concepts.
- **UI**: N/A.
- **Docs**: Remove stale phase-era language from docs. Align doc structure with product terminology. Add subsystem ownership maps for contributors and AI agents. Add historical-cleanup checklists reusable after future migrations.
- **Postman**: N/A.
- **Scripts/Examples**: Scrub scripts and examples of history-shaped naming. Align script names and example scenarios with product terminology. Add generated support matrices showing which docs, scripts, examples, and API collections cover each major feature family.

## Acceptance Criteria

1. Phase-oriented naming and stale migration language removed from tests/scripts/docs
2. Repo terminology is product-centered rather than history-shaped
3. Subsystem ownership maps available for contributors
4. Vocabulary guidance exists to prevent reintroduction of deprecated concepts
5. FEATURE-STATUS.md dashboard updated
