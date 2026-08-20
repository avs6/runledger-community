# WU-011: Internal Cohesion Tightening

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - A/B/C/D (Cross-bundle)
- **Target**: 04-SAFETY-AND-GOVERNANCE/all features
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tool registry | Safety: Approvals | 04×04 | PARTIAL | STRONG |
| Safety: Tool registry | Safety: Security | 04×04 | PARTIAL | STRONG |
| Safety: Tool registry | Safety: Audit log | 04×04 | PARTIAL | STRONG |
| Safety: Tool registry | Safety: Governance pack | 04×04 | PARTIAL | STRONG |
| Safety: Tool registry | Safety: Tags | 04×04 | PARTIAL | STRONG |
| Safety: Tool policies | Safety: Approvals | 04×04 | PARTIAL | STRONG |
| Safety: Tool policies | Safety: Security | 04×04 | PARTIAL | STRONG |
| Safety: Tool policies | Safety: Audit log | 04×04 | PARTIAL | STRONG |
| Safety: Tool policies | Safety: Governance pack | 04×04 | PARTIAL | STRONG |
| Safety: Tool policies | Safety: Tags | 04×04 | PARTIAL | STRONG |
| Safety: Approvals | Safety: Security | 04×04 | PARTIAL | STRONG |
| Safety: Approvals | Safety: Audit log | 04×04 | PARTIAL | STRONG |
| Safety: Approvals | Safety: Governance pack | 04×04 | PARTIAL | STRONG |
| Safety: Data capture | Safety: Tool registry | 04×04 | PARTIAL | STRONG |
| Safety: Data capture | Safety: Tool policies | 04×04 | PARTIAL | STRONG |
| Safety: Data capture | Safety: Approvals | 04×04 | PARTIAL | STRONG |
| Safety: Data capture | Safety: Security | 04×04 | PARTIAL | STRONG |
| Safety: Data capture | Safety: Audit log | 04×04 | PARTIAL | STRONG |
| Safety: Data capture | Safety: Governance pack | 04×04 | PARTIAL | STRONG |
| Safety: Security | Safety: Audit log | 04×04 | PARTIAL | STRONG |
| Safety: Security | Safety: Governance pack | 04×04 | PARTIAL | STRONG |
| Safety: Alert rules | Safety: Tool registry | 04×04 | PARTIAL | STRONG |
| Safety: Alert rules | Safety: Tool policies | 04×04 | PARTIAL | STRONG |
| Safety: Alert rules | Safety: Approvals | 04×04 | PARTIAL | STRONG |
| Safety: Alert rules | Safety: Security | 04×04 | PARTIAL | STRONG |
| Safety: Alert rules | Safety: Audit log | 04×04 | PARTIAL | STRONG |
| Safety: Alert rules | Safety: Governance pack | 04×04 | PARTIAL | STRONG |
| Safety: Audit log | Safety: Tags | 04×04 | PARTIAL | STRONG |
| Safety: Governance pack | Safety: Tags | 04×04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — all self-referential cells
- `FEATURE-STATUS.md` — 04 × self counts

## Scope

- **Backend**: Strengthen internal cross-linking: tool registry/policies should link to approval paths and audit evidence. Data capture should link to tool governance and security. Alert rules should feed into approval triggers and audit evidence. Security events should flow into audit log and governance pack. Tags should be usable across all governance surfaces as a classification dimension.
- **UI**: Each governance surface should show explicit links to related governance surfaces. Tool governance should show approval and audit context. Data capture should show related security and tool policy context. Alert rules should link to approval and evidence outcomes. Audit log and governance pack should show which governance surfaces contributed.
- **Docs**: Document the internal governance workflow across all safety surfaces.
- **Postman**: Add cross-governance linkage to all safety endpoints.
- **Scripts/Examples**: Add example walking through the full governance lifecycle: tool registration, policy creation, alert rule, approval, audit, evidence export.

## Acceptance Criteria

1. Tool governance links to approval paths and audit evidence
2. Data capture links to tool governance and security context
3. Alert rules feed into approvals and audit evidence
4. Security events flow into audit log and governance pack
5. Tags usable as classification across all governance surfaces
6. All listed cohesion cells updated to target state
7. FEATURE-STATUS.md dashboard updated
