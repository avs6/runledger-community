# WU-016: Security Scope Runtime Evidence Refresh

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - C (Data Protection, Security, and Taxonomy)
- **Target**: 04-SAFETY-AND-GOVERNANCE/security
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Security | FinOps: Chargeback | 04x05 | PARTIAL | STRONG |
| Safety: Security | FinOps: Ledger | 04x05 | PARTIAL | STRONG |
| Safety: Security | Org: Organization profile | 04x01 | PARTIAL | STRONG |
| Safety: Security | Org: Users | 04x01 | PARTIAL | STRONG |
| Safety: Security | Org: Workspaces | 04x01 | PARTIAL | STRONG |
| Safety: Security | Gateway: Provider profiles | 04x02 | PARTIAL | STRONG |
| Safety: Security | Gateway: Model gateway | 04x02 | PARTIAL | STRONG |
| Safety: Security | Gateway: Guardrails | 04x02 | STRONG | STRONG |
| Safety: Security | Observe: Monitoring | 04x03 | PARTIAL | STRONG |
| Safety: Security | Safety: Governance pack | 04x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` - Security row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - Security cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - org, user, and workspace security posture view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - provider, gateway, and guardrail posture view
- `03-OBSERVE/COHESION-MATRIX.md` - monitoring and runtime-incident evidence view
- `05-FINOPS/COHESION-MATRIX.md` - chargeback and ledger governance view

## Scope

- **Backend**: Re-audit Security as a cross-cutting posture layer influencing identity, runtime access, incident evidence, and financially accountable operations.
- **UI**: Make security posture easier to connect to workspace scope, runtime controls, and downstream governance evidence.
- **Docs**: Document Security as an always-on operating posture, not just a setup page.
- **Postman**: Keep posture, provider, and ACL flows aligned with the stronger cross-suite interpretation.
- **Scripts/Examples**: Add examples showing how a security posture change affects runtime handling, evidence, and organizational accountability.

## Acceptance Criteria

1. Security is re-audited as a cross-suite posture owner
2. Identity, runtime, and monitoring relationships are explicitly covered
3. Governance-pack and accountability relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
