# WU-005: Investigation Safety & Governance Traceability

- **Status**: COMPLETED
- **Bundle**: 03-Observe - B (Investigation)
- **Target**: 03-OBSERVE/Runs, Run detail, Request flow, Request explorer
- **Created**: 2026-08-14
- **Completed**: 2026-08-24

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Runs list | Safety: Tool registry | 03×04 | PARTIAL | STRONG |
| Observe: Runs list | Safety: Tool policies | 03×04 | PARTIAL | STRONG |
| Observe: Runs list | Safety: Security | 03×04 | PARTIAL | STRONG |
| Observe: Runs list | Safety: Alert rules | 03×04 | PARTIAL | STRONG |
| Observe: Runs list | Safety: Audit log | 03×04 | PARTIAL | STRONG |
| Observe: Runs list | Safety: Governance pack | 03×04 | PARTIAL | STRONG |
| Observe: Runs list | Safety: Tags | 03×04 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Tool registry | 03×04 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Tool policies | 03×04 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Security | 03×04 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Alert rules | 03×04 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Audit log | 03×04 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Governance pack | 03×04 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Tags | 03×04 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Tool registry | 03×04 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Tool policies | 03×04 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Security | 03×04 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Alert rules | 03×04 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Audit log | 03×04 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Governance pack | 03×04 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Tags | 03×04 | PARTIAL | STRONG |
| Observe: Request explorer | Safety: Tool registry | 03×04 | PARTIAL | STRONG |
| Observe: Request explorer | Safety: Tool policies | 03×04 | PARTIAL | STRONG |
| Observe: Request explorer | Safety: Security | 03×04 | PARTIAL | STRONG |
| Observe: Request explorer | Safety: Alert rules | 03×04 | PARTIAL | STRONG |
| Observe: Request explorer | Safety: Audit log | 03×04 | PARTIAL | STRONG |
| Observe: Request explorer | Safety: Governance pack | 03×04 | PARTIAL | STRONG |
| Observe: Request explorer | Safety: Tags | 03×04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Investigation × Safety cells
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Investigation features
- `FEATURE-STATUS.md` — 03-B × 04 counts

## Scope

- **Backend**: Investigation surfaces should carry governance context: tool registry and policy outcomes per request, security event correlation, alert rule firing status, audit log linkage, governance pack evidence references, tag-based filtering. Request flow and explorer should accept governance-dimension filters.
- **UI**: Run detail and request flow should show inline tool policy outcomes and security events. Investigation surfaces should link to audit log entries and governance pack evidence. Tag-based filtering should be available on runs and request explorer.
- **Docs**: Document governance-aware investigation workflows.
- **Postman**: Add governance context to investigation endpoint responses.
- **Scripts/Examples**: Add example tracing a request through tool policy evaluation and audit log.

## Acceptance Criteria

1. Run detail shows tool policy outcomes and security events
2. Request flow shows governance context inline
3. Request explorer filters by tags and governance dimensions
4. Investigation surfaces link to audit log and governance pack
5. Alert rule firing status visible in relevant investigation views
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
