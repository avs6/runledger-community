# FinOps — Cohesion Matrix

Last updated: 2026-08-15

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
| FinOps | Budgets | `PARTIAL` | `N/A` | `PARTIAL` | `GAP` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Strongest current relationship is workspace ownership; access-group scope is now real, while API-key and org-level budget posture are still weaker than they should be. |
| FinOps | Budget detail | `GAP` | `N/A` | `PARTIAL` | `GAP` | `PARTIAL` | `GAP` | `GAP` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Budget detail is now real, but cross-links into org rollups, access-group posture, API-key-native ownership, and onboarding guidance are still much thinner than the main budget shell itself. |
| FinOps | Budget overrides | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Overrides now live inside the main budget workflow, but they still are not deeply integrated with broader org and identity operating surfaces. |
| FinOps | Budget notifications | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Notification delivery is real, but it still is not surfaced as a first-class org or identity workflow beyond workspace-owned budget operations. |
| FinOps | Billing periods | `PARTIAL` | `N/A` | `PARTIAL` | `GAP` | `PARTIAL` | `PARTIAL` | `GAP` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Billing consumes workspace spend well and has real org relevance, but access-group, API-key, and user-facing ownership dimensions remain relatively thin. |
| FinOps | Billing period detail | `GAP` | `N/A` | `N/A` | `GAP` | `PARTIAL` | `GAP` | `GAP` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Billing detail is operationally real, but it still is not a strong drillback into org, access-group, API-key, or model-catalog context. |
| FinOps | Chargeback | `PARTIAL` | `N/A` | `N/A` | `GAP` | `PARTIAL` | `GAP` | `GAP` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Chargeback now aligns well to workspaces and modern runtime dimensions, but access-group and API-key-native attribution are still future deepening work. |
| FinOps | Ledger | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger belongs more to platform compliance than to daily org operations; its strongest org/access relationship is still workspace scope underneath, but org-level readiness and evidence posture make the relationship at least partial rather than non-applicable. |

### 11.2b FinOps x Gateway & Routing

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | Budgets now support provider pricing posture and cache savings indirectly, while model quotas and rate limits remain adjacent technical controls rather than a unified FinOps control plane. |
| FinOps | Budget detail | `PARTIAL` | `PARTIAL` | `N/A` | `GAP` | `GAP` | Budget detail can explain spend policy, but it still does not reconcile cache posture or technical throttles and quota tiers as a first-class operator drillback. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Budget overrides can resemble runtime throttle or fallback actions, but FinOps still does not expose clear override history or review flows for quota-tier and model-limit changes. |
| FinOps | Budget notifications | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Notifications should eventually reflect gateway-side quota or route pressure events more explicitly. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | Billing periods inherit both cache-aware costing and quota-enforced traffic effects, but they still do not surface technical throttles as a first-class FinOps control. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | Billing detail carries cached-token, traffic, and savings effects, yet it still lacks a strong drillback into rate-limit configuration and quota posture. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | Chargeback can attribute cached-token savings and avoided spend indirectly, but Response Cache is still upstream context rather than an explicit chargeback management loop. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | Ledger is downstream evidence, not an active gateway operating surface, but rate-limit and quota posture can still feed that evidence chain indirectly. |

### 11.2c FinOps x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-------------------|------------------|-----------------|------------------------|-------------|------------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Observe already consumes spend data broadly, but budget policy is still not the clear source of truth for many of those views. |
| FinOps | Budget detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budget detail is now real, but the observability drillback into budget context is still thinner than it should be across the main investigative surfaces. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Overrides should become more visible in investigative surfaces so operators can explain spend exceptions. |
| FinOps | Budget notifications | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notification history belongs in the broader observe-and-act story but is not yet visible there as a first-class investigative workflow. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Billing already has strong economics cohesion, especially with economics and billing-summary-style surfaces. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Richer drilldowns are present, but they still are not tied tightly enough to scope-level reconciliation and operator actions. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Chargeback fits naturally into the economics and analytics layer, but its business-dimension model still needs hardening. |
| FinOps | Ledger | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | Ledger should be referenced by observe surfaces, but not owned by them. |

### 11.2d FinOps x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| FinOps | Budgets | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Governance evidence exists, but budget policy lifecycle is still not tightly integrated with approvals, alerts, and tagging. |
| FinOps | Budget detail | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budget detail is operationally real now, but it still is not a fully governed review surface with rich traceability. |
| FinOps | Budget overrides | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Overrides are the clearest place where approval-driven governance should exist and still are only partially integrated there. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notification and evidence paths are stronger than the main budget workflow today. |
| FinOps | Billing periods | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Billing has useful evidence hooks, but not a deeply governed operator story yet. |
| FinOps | Billing period detail | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Reconciliation detail can support governance, but the user flow still feels finance-only rather than policy-aware. |
| FinOps | Chargeback | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tagging and evidence are important here, but the overall governance relationship is still moderate rather than strong. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | Ledger is primarily a compliance evidence surface, so governance-pack cohesion is one of the strongest relationships in the matrix. |

### 11.2e FinOps x Build & Improve

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | FinOps should increasingly act as a feedback loop into optimization, workflows, and prompt/model improvement rather than sitting as a separate finance island. |
| FinOps | Budget detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Budget detail now exists, but it still does not yet drive improvement work across the build surfaces as strongly as it could. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Override decisions should eventually be visible as explicit engineering or evaluation exceptions. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Notifications should feed operators and builders when spend issues affect workflow improvement loops. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Billing and optimization already want to work together; the product should lean into that relationship more intentionally. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Reconciliation detail should become a stronger input into experimentation and optimization decisions. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Chargeback is most cohesive when tied to workflows and improvement programs rather than only to flat finance reports. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger is largely outside the day-to-day build loop except as downstream evidence, with only a light tie to optimization/replay feedback loops. |

### 11.2f FinOps x Platform and Utility

| Row Major Feature | Row Subfeature | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|-------------------|-------------------|---------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `PARTIAL` | FinOps should surface clearly at both org and platform scope, but platform ownership is still under-structured outside the main workspace budget shell. |
| FinOps | Budget detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | Platform operators still lack a strong detail view for cross-org spend governance. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `PARTIAL` | Override governance should eventually include platform-level review and reporting. |
| FinOps | Budget notifications | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notifications need stronger platform-level visibility and administration. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | Billing already has platform relevance, but the user workflow is not fully unified yet. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | Platform-side billing drilldowns should become more operational and less passive. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | Chargeback belongs at both org and platform layers, but the allocation model needs deepening. |
| FinOps | Ledger | `PARTIAL` | `STRONG` | `PARTIAL` | Ledger is the clearest FinOps-to-platform-settings relationship in the current product. |

### 11.2g FinOps x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| FinOps | Budgets | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budgets is the intended FinOps control-plane anchor and now has real internal ties to detail, overrides, and notifications, though the downstream billing and allocation links are still looser. |
| FinOps | Budget detail | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budget detail now exists and gives the FinOps domain a real internal drillback, but it still is not the fully connective tissue the bundle blueprint ultimately wants. |
| FinOps | Budget overrides | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Overrides are real and now live inside the main budget lifecycle, though they still are not as deeply governed as the rest of the control plane should become. |
| FinOps | Budget notifications | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notification behavior exists and is tied to budgets, but it still is not tightly embedded into the day-to-day FinOps operator experience. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `STRONG` | Billing is internally one of the most cohesive FinOps blocks today, especially across period detail, chargeback handoff, and ledger closure. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | Billing detail is structurally sound and closely tied to the rest of the downstream FinOps flow, even though its ties back into budget governance remain more moderate. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `N/A` | `STRONG` | Chargeback belongs inside FinOps and now has real ties into billing and closure, but it still behaves more like an adjacent allocation engine than a fully woven control-plane feature. |
| FinOps | Ledger | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | Ledger closes the loop for evidence and verification and is now strongly connected to billing and chargeback, even though the upstream budget-to-closure chain is still not seamless. |

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
