# WU-006: Identity & Scope in Safety & Governance

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/Users, Access groups, API keys
- **Created**: 2026-08-14
- **Completed**: 2026-08-20

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Users | Safety: Tool registry | 01×04 | STRONG | STRONG |
| Org: Users | Safety: Tool policies | 01×04 | STRONG | STRONG |
| Org: Users | Safety: Approvals | 01×04 | STRONG | STRONG |
| Org: Users | Safety: Data capture | 01×04 | STRONG | STRONG |
| Org: Users | Safety: Security | 01×04 | STRONG | STRONG |
| Org: Users | Safety: Audit log | 01×04 | STRONG | STRONG |
| Org: Users | Safety: Governance pack | 01×04 | STRONG | STRONG |
| Org: Users | Safety: Tags | 01×04 | STRONG | STRONG |
| Org: Access groups | Safety: Tool registry | 01×04 | STRONG | STRONG |
| Org: Access groups | Safety: Tool policies | 01×04 | STRONG | STRONG |
| Org: Access groups | Safety: Approvals | 01×04 | STRONG | STRONG |
| Org: Access groups | Safety: Data capture | 01×04 | STRONG | STRONG |
| Org: Access groups | Safety: Security | 01×04 | STRONG | STRONG |
| Org: Access groups | Safety: Audit log | 01×04 | STRONG | STRONG |
| Org: Access groups | Safety: Governance pack | 01×04 | STRONG | STRONG |
| Org: API keys | Safety: Tool policies | 01×04 | STRONG | STRONG |
| Org: API keys | Safety: Approvals | 01×04 | STRONG | STRONG |
| Org: API keys | Safety: Data capture | 01×04 | STRONG | STRONG |
| Org: API keys | Safety: Security | 01×04 | STRONG | STRONG |
| Org: API keys | Safety: Alert rules | 01×04 | STRONG | STRONG |
| Org: API keys | Safety: Audit log | 01×04 | STRONG | STRONG |
| Org: API keys | Safety: Governance pack | 01×04 | STRONG | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Users/Access groups/API keys × Safety cells
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Users/Access groups/API keys
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Users, Access groups, API keys rows
- `FEATURE-STATUS.md` — 01-B × 04 counts

## Scope

- **Backend**: Governance surfaces should consistently resolve user, access-group, and API-key identity: approvals should show requester identity and access-group membership, audit log should filter by user/access-group/API-key, tool policies and data capture should be scoped by access group, governance pack should include identity-aware evidence.
- **UI**: Approvals, audit log, and policy surfaces should expose user/access-group/API-key filters. Identity detail pages should cross-link to governance activity.
- **Docs**: Document how identity primitives participate in governance workflows.
- **Postman**: Add identity filters to approvals, audit log, tool policies, and governance pack endpoints.
- **Scripts/Examples**: Add example showing governance audit filtered by access group and API key.

## Acceptance Criteria

1. Approvals show requester identity with access-group context
2. Audit log filters by user, access group, and API key
3. Tool policies and data capture can be scoped by access group
4. Governance pack includes identity-aware evidence chains
5. Identity detail pages link to their governance footprint
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated

## Completion Notes

- Backend: Added `requested_by`, `access_group_id`, `api_key_prefix` filters to approvals list; added `access_group_id`, `api_key_prefix` filters to audit log list and export; added `user_id`, `access_group_id`, `api_key_id` filters to governance audit pack and export; added `GET /users/{user_id}/governance` endpoint returning approval/audit summary.
- UI: User detail page now shows governance footprint (approval count, audit event count, recent items) and cross-links to Approvals, Audit Log, Governance Pack. Access groups page now includes Approvals, Audit Log, Governance links per group. API key detail page now includes Approvals, Audit Log, Governance links.
- Docs: Updated approvals.mdx with identity filters section, governance-audit-pack.mdx with identity-scoped evidence section, users.mdx with governance footprint section.
- Postman: Added identity filter params to List Approvals, List Audit Events, Get Governance Audit Pack; added User Governance Summary request.
- Example: Added `examples/52_identity_governance.py` demonstrating identity-scoped governance queries.
