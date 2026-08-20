# RunLedger TODO

Fresh roadmap containing only remaining work.

Last normalized: August 6, 2026.

Status key: `[~]` = partial, `[ ]` = pending, `[>]` = moved.

Effort key: `S` = small, `M` = medium, `L` = large, `XL` = very large.

Impact key: `M` = medium, `H` = high.

## Phase Tracker

| Done | Phase | Effort | Impact | Current State |
|---|---|---:|---:|---|

| [~] | Phase 1 - Security And Compliance | XL | H | OIDC, IP ACL, and key-management foundations exist; deeper enterprise security and compliance work remains. |

## Phase 1 - Security And Compliance

Status: partial

This phase stays later in the roadmap intentionally. The foundation is present, but the remaining work is primarily enterprise hardening rather than core product closure.

### JWT, OIDC, And SSO

- [~] Expand gateway JWT and OIDC beyond the current provider and claim-mapping foundation:
  - multi-IdP support
  - deeper discovery and session controls
- [ ] Add SSO and SAML support.
- [ ] Add JWT-based short-lived key generation and session UI.

### SCIM

- [ ] Add SCIM 2.0 user and group endpoints.
- [ ] Add Okta and Azure AD SCIM integrations.
- [ ] Add automatic team-membership sync.

### IP ACLs

- [~] Expand IP ACL enforcement from the current workspace-level tooling to key, team, and global scopes.

### Key Lifecycle

- [~] Expand key lifecycle beyond the current ownership and history UI:
  - automated rotation with schedule, grace period, notification, and emergency revocation
  - expiry workflows and bulk actions

### Secret Managers

- [ ] Add secret manager backends:
  - AWS Secrets Manager and KMS
  - HashiCorp Vault
  - Azure Key Vault
  - Google Cloud Secret Manager
  - CyberArk Conjur
- [ ] Add startup-time secret resolution and rotation refresh.
- [ ] Add secret-management UI.

### Compliance

- [ ] Add log export to cloud storage.
- [ ] Add data residency controls.
- [ ] Add richer audit log export and retention.
- [ ] Add immutable append-only admin audit trail.
- [ ] Add per-team callback routing.
- [ ] Add required request-parameter enforcement.
- [ ] Add white-label customization.

### Acceptance Cleanup

- [ ] Ensure JWT and OIDC work with major IdPs.
- [ ] Ensure SCIM auto-sync works with Okta and Azure AD.
- [ ] Ensure IP ACLs apply at key, team, and workspace scope.
- [ ] Ensure automated rotation works with grace periods.
- [ ] Ensure at least two secret-manager integrations work end to end.
- [ ] Ensure audit logs capture all admin actions immutably.



## Phase Tracker

| Done | Phase | Effort | Impact | Current State |
|---|---|---:|---:|---|

| [~] | Phase 2 - Demo, Storytelling, And Launch Readiness | L | H | Demo mode, labs, simulator, and product surfaces exist; story polish and sales/demo assets remain. |


## Phase 2 - Demo, Storytelling, And Launch Readiness

Status: partial

### Demo Data

### Release And Process

### Assets


  ### Internal Only Do not Commit. 
  - competitive landscape
  - investor deck
  - [ ] Create feature demo deck.
  - [ ] Export deck and script assets as PPTX, PDF, and Markdown.