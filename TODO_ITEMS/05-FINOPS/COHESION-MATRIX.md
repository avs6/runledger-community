# FinOps — Cohesion Matrix

Last updated: PENDING AUDIT

This file tracks how FinOps features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

This first populated matrix follows the diagram pattern more closely while staying readable in Markdown:

- left side = audited major feature plus its subfeatures
- top side = major/minor features from the other feature families
- cells = current cohesion state for the relationship
- because Markdown tables cannot merge header cells like the sketch, each column is labeled as `Major Feature: Minor Feature`
- because one true mega-table would be too wide to audit properly, the full column set is split into aligned sub-matrices by feature family

Current row major feature under audit: `FinOps`

### 11.2a FinOps x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| FinOps | Budgets | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | Strongest current relationship is workspace ownership; biggest missing relationships are access-group and API-key budget scope. |
| FinOps | Budget detail | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | The missing true detail page blocks useful cross-links into org rollups, key ownership, and model-catalog context. |
| FinOps | Budget overrides | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | Overrides exist, but they are not yet integrated with the main org and access-control operating model. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Notification delivery is real, but it is not yet surfaced as part of the main org-facing FinOps workflow. |
| FinOps | Billing periods | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | Billing already consumes workspace spend well, but attribution and ownership dimensions remain thin. |
| FinOps | Billing period detail | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | Detail view is informative, but not yet a strong operational bridge back into the access and catalog surfaces. |
| FinOps | Chargeback | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | Chargeback is directionally aligned to workspaces, but still needs stronger access-group and API-key attribution. |
| FinOps | Ledger | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger belongs more to platform compliance than to daily org operations. |

### 11.2b FinOps x Gateway & Routing

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------|
| FinOps | Budgets | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | FinOps and Gateway are related today, but spend policy still is not clearly the canonical owner across provider, cache, and throttling controls. |
| FinOps | Budget detail | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | The current detail experience is too shallow to show route, provider, or quota-aware spend analysis. |
| FinOps | Budget overrides | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | Overrides can influence runtime behavior, but the product does not yet expose that relationship cleanly. |
| FinOps | Budget notifications | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | Notifications should eventually reflect gateway-side quota or route pressure events more explicitly. |
| FinOps | Billing periods | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | Billing can already consume gateway-shaped spend, but the operator surface does not make that relationship rich enough. |
| FinOps | Billing period detail | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | Detail view needs clearer route, provider, and quota breakdowns if reconciliation is going to be trusted. |
| FinOps | Chargeback | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | Chargeback is moving in the right direction, but it still lacks stronger gateway-native business attribution. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger is downstream evidence, not an active gateway operating surface. |

### 11.2c FinOps x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-------------------|------------------|-----------------|------------------------|-------------|------------|---------|
| FinOps | Budgets | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Observe already consumes spend data broadly, but budget policy is still not the clear source of truth for many of those views. |
| FinOps | Budget detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | The missing real budget detail page is the biggest cohesion blocker between FinOps and Observability. |
| FinOps | Budget overrides | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | Overrides should become more visible in investigative surfaces so operators can explain spend exceptions. |
| FinOps | Budget notifications | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | Notification history belongs in the broader observe-and-act story but is not yet visible there. |
| FinOps | Billing periods | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Billing already has strong economics cohesion, especially with the economics and billing-summary surfaces. |
| FinOps | Billing period detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Richer drilldowns are present, but still not tied tightly enough to scope-level reconciliation and operator actions. |
| FinOps | Chargeback | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | Chargeback fits naturally into the economics/analytics layer, but its business-dimension model still needs hardening. |
| FinOps | Ledger | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | Ledger should be referenced by observe surfaces, but not owned by them. |

### 11.2d FinOps x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| FinOps | Budgets | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Governance evidence exists, but budget policy lifecycle is still not tightly integrated with approvals, alerts, and tagging. |
| FinOps | Budget detail | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Detail is too weak to support meaningful governance review or traceability. |
| FinOps | Budget overrides | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Overrides are the clearest place where approval-driven governance should exist and currently does not. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Notification and evidence paths are stronger than the main budget workflow today. |
| FinOps | Billing periods | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Billing has useful evidence hooks, but not a deeply governed operator story yet. |
| FinOps | Billing period detail | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Reconciliation detail can support governance, but the user flow still feels finance-only rather than policy-aware. |
| FinOps | Chargeback | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | Tagging and evidence are important here, but the overall governance relationship is still moderate rather than strong. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | Ledger is primarily a compliance evidence surface, so governance-pack cohesion is one of the strongest relationships in the matrix. |

### 11.2e FinOps x Build & Improve

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|---------|
| FinOps | Budgets | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | FinOps should increasingly act as a feedback loop into optimization, workflows, and prompt/model improvement rather than sitting as a separate finance island. |
| FinOps | Budget detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | Without a real detail page, FinOps cannot meaningfully guide improvement work across the build surfaces. |
| FinOps | Budget overrides | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | Override decisions should eventually be visible as explicit engineering or evaluation exceptions. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | Notifications should feed operators and builders when spend issues affect workflow improvement loops. |
| FinOps | Billing periods | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | Billing and optimization already want to work together; the product should lean into that relationship more intentionally. |
| FinOps | Billing period detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | Reconciliation detail should become a stronger input into experimentation and optimization decisions. |
| FinOps | Chargeback | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | Chargeback is most cohesive when tied to workflows and improvement programs rather than only to flat finance reports. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger is largely outside the day-to-day build loop except as downstream evidence. |

### 11.2f FinOps x Platform and Utility

| Row Major Feature | Row Subfeature | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|-------------------|-------------------|---------|---------|
| FinOps | Budgets | `PENDING` | `PENDING` | `N/A` | FinOps should surface clearly at both org and platform scope, but platform ownership is still under-structured. |
| FinOps | Budget detail | `PENDING` | `PENDING` | `N/A` | Platform operators still lack a strong detail view for cross-org spend governance. |
| FinOps | Budget overrides | `PENDING` | `PENDING` | `N/A` | Override governance should eventually include platform-level review and reporting. |
| FinOps | Budget notifications | `PENDING` | `PENDING` | `N/A` | Notifications need stronger platform-level visibility and administration. |
| FinOps | Billing periods | `PENDING` | `PENDING` | `N/A` | Billing already has platform relevance, but the user workflow is not fully unified yet. |
| FinOps | Billing period detail | `PENDING` | `PENDING` | `N/A` | Platform-side billing drilldowns should become more operational and less passive. |
| FinOps | Chargeback | `PENDING` | `PENDING` | `N/A` | Chargeback belongs at both org and platform layers, but the allocation model needs deepening. |
| FinOps | Ledger | `PENDING` | `PENDING` | `N/A` | Ledger is the clearest FinOps-to-platform-settings relationship in the current product. |

### 11.2g FinOps x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| FinOps | Budgets | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Budgets is the intended FinOps control-plane anchor, but too many internal relationships are still weak or indirect. |
| FinOps | Budget detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | The missing true detail surface is the biggest internal cohesion break inside FinOps. |
| FinOps | Budget overrides | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Overrides are real, but they still feel like a side-table instead of a first-class budget lifecycle feature. |
| FinOps | Budget notifications | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | Notification behavior exists, but it is still not tightly embedded into the day-to-day FinOps operator experience. |
| FinOps | Billing periods | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Billing is internally the most cohesive FinOps block today, but it still does not fully connect back to budget governance. |
| FinOps | Billing period detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Billing detail is structurally sound, but its ties to the rest of the FinOps control plane remain moderate. |
| FinOps | Chargeback | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Chargeback belongs inside FinOps, but it still behaves more like an adjacent report than a deeply integrated allocation engine. |
| FinOps | Ledger | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Ledger closes the loop for evidence and verification, but it is not yet woven tightly into the upstream operating flows. |

### 11.2h Matrix Reading Notes

- `FinOps -> Budgets x Workspaces = STRONG`
  Means the current implementation already has a meaningful real relationship there.
- `FinOps -> Budgets x Access groups = GAP`
  Means the relationship should exist, but the current product and runtime do not yet expose it strongly enough.
- `FinOps -> Budget detail x Provider profiles = GAP`
  Means the detail experience is too weak to expose a relationship that Bundle A should eventually support.
- `FinOps -> Billing periods x Analytics economics = STRONG`
  Means the relationship is already real in the shipped suite, even if the operator workflow still needs tightening.
- `FinOps -> Chargeback x Workflow detail = STRONG`
  Means the product direction is clearest when financial attribution is tied back to workflows rather than to legacy organizational abstractions.
- `FinOps -> Budgets x Budget detail = GAP`
  Means the main control-plane feature still lacks the internal detail experience needed to make the rest of FinOps cohesive.

### 11.2i FinOps Bundle A Audit Findings

These findings should directly shape `Bundle A - Spend Control Plane`:

1. `Budgets` must become access-aware.
   Current code and UI treat workspace as the main real scope, but the next implementation pass should explicitly support access groups and API keys as first-class budget scopes.
2. `Budgets` must become gateway-aware but not gateway-owned.
   Gateway quota tiers and model quotas are related, but spend governance should remain owned by FinOps while cross-linking clearly into Gateway technical controls.
3. `Budget detail` is the biggest current cohesion gap.
   Without a true detail page, budgets cannot meaningfully connect to organization rollups, access scopes, API keys, provider profiles, approvals, or policy history.
4. `Budget overrides` must be approval-aware.
   The current lifecycle is useful, but it behaves like a detached exception table instead of a governed override workflow.
5. `Budget notifications` should be pulled into the main Spend Control Plane.
   The backend is already stronger than the UI here, so this is a high-value cohesion win for Bundle A.
6. `Provider profiles` and `Tags / workflows` are missing as first-class budget dimensions.
   These are essential if FinOps is going to become one of the strongest feature families instead of remaining workspace-only.
7. `Audit log` and `Governance pack` already provide the right evidence direction.
   Bundle A should lean into these instead of inventing separate evidence flows.
8. `Organization profile` should consume budget rollups, but Bundle A should remain the canonical spend-policy owner.
   This keeps FinOps cohesive without scattering budget editing into org admin pages.
