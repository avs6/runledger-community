# RunLedger V2 Implementation Plan

Detailed 6-month implementation plan for building RunLedger into the AI spend system of record and control plane.

Date: 2026-03-21
Source context: [vc_feedback.md](C:/Users/Abi/Desktop/github/runledger/vc_feedback.md)

---

## Purpose

This plan does not replace [IMPLEMENTATION.md](C:/Users/Abi/Desktop/github/runledger/IMPLEMENTATION.md).

It is a second implementation plan optimized for a different reality:

- the current product already has meaningful breadth
- the main strategic risk is not lack of features, but lack of moat concentration
- the next 6 months should be spent turning RunLedger from "good AI observability product" into "hard-to-replace finance and control platform for AI"

The central thesis of this plan is:

- traces are useful but not defensible
- finance-grade reconciliation, chargeback, budget enforcement, routing control, and outcome visibility are defensible
- packaging and enterprise readiness must be built in parallel, not later

---

## Planning Assumptions

This plan assumes:

- 6 months of focused effort
- the existing codebase remains the foundation
- no rewrite
- current backend, web app, Python SDK, TypeScript SDK, gateway, billing, and analytics surfaces are preserved and extended

This plan does not assume unlimited scope. The goal is concentration, not feature sprawl.

---

## Strategic Outcome At The End Of 6 Months

At the end of this plan, RunLedger should be able to credibly claim:

1. It is the system of record for AI spend across providers.
2. It can reconcile internal usage to provider invoices and explain deltas.
3. It can tie spend to business outcomes and ROI.
4. It can actively control runtime behavior through budgets, routing, and policy enforcement.
5. It can onboard enterprise buyers through SSO, SCIM, auditability, approvals, and warehouse exports.
6. It has a clean open-core packaging model across OSS, SaaS, and enterprise self-hosted.

If those six outcomes are delivered, RunLedger moves from "interesting infra product" to "finance and platform control layer."

---

## Product Principles For This Plan

1. Billing trust over feature count.
2. Control plane over dashboard parity.
3. Cross-provider neutrality over provider-specific lock-in.
4. Enterprise credibility over premature sales motion.
5. Packaging clarity over open-core ambiguity.
6. Outcome relevance over token vanity metrics.

---

## Non-Goals For This 6-Month Plan

These are explicitly deprioritized:

- competing with LangSmith on generic prompt/evals workflow depth
- competing with Langfuse on broad OSS observability mindshare
- competing with LiteLLM or Portkey on maximum provider breadth
- building a full application deployment platform
- chasing every possible framework integration before OTel/OpenInference
- shipping speculative AI assistant features inside the product

---

## Workstreams

There are six primary workstreams across the entire 6 months:

1. Provider Invoice Reconciliation
2. Outcome and ROI Ledger
3. Packaging and Editions
4. OpenTelemetry / OpenInference Ingestion
5. Enterprise Controls and Governance
6. Gateway Expansion and Runtime Control

These workstreams converge into monthly milestones.

---

## Month 1: Foundation Reset And Moat Alignment

### Goal

Realign the product, architecture, and packaging around the moat before adding more surface area.

### Deliverables

#### 1. Architecture and packaging freeze

Ship a written architecture decision record covering:

- what belongs in OSS
- what belongs in SaaS
- what belongs in Enterprise Self-Hosted
- what belongs in Hybrid/BYOC
- what APIs and services are shared across all editions
- what features are enforced through server-side gating

Required outputs:

- edition matrix
- licensing boundary doc
- feature-gate implementation plan
- migration impact report

#### 2. Finance moat schema design

Finalize schema additions for:

- provider invoices
- provider invoice lines
- reconciliation matches
- reconciliation mismatch reasons
- dispute packages
- outcomes
- outcome values
- ROI rollups
- approval workflows
- identity federation metadata
- provisioning audit trails

Required outputs:

- approved schema spec
- indexed query plan
- retention policy impact analysis

#### 3. OTel / OpenInference ingestion design

Define:

- supported semantic conventions
- normalization path into `agent_runs`, `spans`, `provider_calls`, and `tool_calls`
- deduplication keys
- required metadata mapping
- partial data handling
- ingestion performance budget

#### 4. Enterprise control model design

Finalize:

- RBAC matrix
- role to permission mapping
- SSO architecture
- SCIM scope
- approvals model
- audit coverage requirements
- data retention and deletion policy behavior

#### 5. Targeted provider strategy

Lock the 6-month provider list:

- Azure OpenAI
- AWS Bedrock
- Vertex AI
- OpenRouter

Define the minimum viable support per provider:

- usage normalization
- pricing normalization
- request ID capture
- invoice/export ingestion path
- gateway routing support

### Exit criteria

- all core design docs approved
- first migrations scaffolded
- edition boundaries signed off
- release plan decomposed into concrete implementation backlogs

---

## Month 2: Provider Invoice Reconciliation MVP

### Goal

Ship the first true moat release: external provider invoice reconciliation.

### Deliverables

#### 1. Invoice import pipelines

Support first-party import for:

- OpenAI usage export
- Anthropic usage export
- Azure OpenAI billing/usage export where available

Capabilities:

- CSV and JSON ingestion
- import validation
- duplicate import protection
- period and currency metadata
- source file fingerprinting
- import job status tracking

#### 2. Reconciliation engine v1

Matching logic:

- exact request ID match where available
- fallback matching by provider, model, timestamp window, token counts, and cost
- confidence scores for fuzzy matches
- explicit unmatched and ambiguous buckets

Outputs:

- matched total
- unmatched total
- overcount/undercount buckets
- delta by provider and model
- reason taxonomy for mismatches

#### 3. Finance UI for reconciliation

New UI surfaces:

- invoice import list
- invoice detail page
- reconciliation summary
- mismatch drilldown
- dispute candidate table
- exportable evidence pack

#### 4. Signed dispute package export

Export a signed package including:

- invoice line metadata
- matched internal calls
- unmatched calls
- delta summary
- hashes and signatures
- generated timestamp

#### 5. Reconciliation API

New or extended APIs:

- create invoice import
- list imports
- get import detail
- run reconciliation
- fetch reconciliation report
- export dispute package

### Exit criteria

- at least one provider can be imported and reconciled end-to-end
- users can inspect deltas and export evidence
- reconciliation is no longer only internal-table consistency

---

## Month 3: Outcome And ROI Ledger

### Goal

Make RunLedger valuable to product and finance leaders, not only infrastructure users.

### Deliverables

#### 1. Outcome model and APIs

Add first-class outcomes:

- `outcome_type`
- `success`
- `value_usd`
- labels and dimensions
- linkage to `run_id`, `session_id`, `end_user_id`, and feature

Support:

- SDK submission
- API submission
- bulk backfill
- event joins to costs and scores

#### 2. ROI rollups

Build rollups for:

- cost per outcome
- cost per successful outcome
- outcome value by workflow
- ROI by feature, app, tenant, and end user segment
- score-to-outcome and cost-to-outcome comparisons

#### 3. ROI dashboards

New surfaces:

- cost per outcome trend
- ROI summary cards
- best and worst workflows by unit economics
- regression alerts on cost per success
- outcome funnel view by feature/app

#### 4. Alerting on business efficiency

Add alert rule types for:

- cost per success spike
- success rate drop
- ROI degradation
- outcome value decline

#### 5. Prompt and routing tie-ins

Expose joins showing:

- prompt version to outcome rate
- route choice to outcome quality
- budget action to outcome impact

### Exit criteria

- users can tie spend to business outcomes
- dashboards support cost-per-success and ROI views
- routing and prompt experiments can be interpreted through business metrics

---

## Month 4: Enterprise Controls And Adoption Layer

### Goal

Remove major blockers to enterprise adoption and self-hosted credibility.

### Deliverables

#### 1. SSO / Identity

Ship:

- OIDC SSO
- SAML support for major IdPs
- JIT provisioning
- role mapping
- login policy controls

#### 2. SCIM provisioning

Support:

- user create
- user deactivate
- group and role mapping
- workspace or org assignment
- provisioning audit logs

#### 3. Approvals workflow

Required approval support for:

- budget increases
- prompt promotion to production
- enabling FULL payload capture
- allowing privileged tools
- enabling certain gateway routes or external providers

#### 4. Audit coverage completion

Audit every sensitive action including:

- auth and provisioning events
- budget and chargeback changes
- gateway route and policy changes
- invoice import and reconciliation actions
- prompt promotion
- payload viewing/export
- retention and deletion changes

#### 5. OTel / OpenInference MVP

Ship a usable ingestion bridge with:

- HTTP ingest endpoint
- mapping to internal trace model
- basic SDK examples
- validation and error reporting
- synthetic load tests

### Exit criteria

- an enterprise buyer can onboard with SSO
- users can be provisioned by SCIM
- sensitive actions require approvals
- existing OTel/OpenInference users can adopt without replacing all instrumentation

---

## Month 5: Packaging, Editions, And Go-To-Market Readiness

### Goal

Make the product commercially legible and operationally shippable.

### Deliverables

#### 1. Edition enforcement

Implement server-side feature gates and edition-aware UX for:

- OSS
- SaaS
- Enterprise Self-Hosted
- optional Hybrid/BYOC path

Enforce:

- which APIs are available
- which UI modules render
- which exports and integrations are enabled
- which governance controls require enterprise licensing

#### 2. OSS trim and polish

Define OSS as:

- SDKs
- ingestion
- traces
- basic analytics
- dev/local gateway

Remove or gate:

- finance moat features
- advanced control-plane features
- enterprise governance features

#### 3. SaaS control-plane experience

Polish hosted-product flows around:

- onboarding
- API key creation
- invoice import
- ROI setup
- alerts
- gateway route setup
- billing and finance exports

#### 4. Self-hosted and hybrid packaging

Ship:

- deployment profiles
- environment variable reference
- external dependency diagram
- backup and restore guidance
- upgrade path guidance
- support boundaries

#### 5. Warehouse and finance integrations

Ship first practical integrations:

- signed billing-close webhook
- daily export to object storage
- Snowflake-ready export format
- BigQuery-ready export format
- QuickBooks or Netsuite starter export

### Exit criteria

- a user can clearly understand what is OSS vs SaaS vs Enterprise
- the paid moat is enforced in product behavior
- documentation matches actual implementation

---

## Month 6: Scale, Hardening, And Launch Preparation

### Goal

Make the new RunLedger trustworthy at higher scale and ready for market push.

### Deliverables

#### 1. Scalability and performance hardening

Run and fix:

- reconciliation load tests
- OTel ingest load tests
- gateway throughput tests
- ROI rollup performance tests
- large-tenant partition and index tests
- export pipeline stress tests

Required benchmarks:

- invoice import at enterprise-sized monthly volumes
- reconciliation job completion within acceptable SLAs
- OTel ingest under burst traffic
- gateway route selection without unacceptable latency overhead

#### 2. Reliability and operations

Ship:

- retry and idempotency guarantees for new ingestion jobs
- dead-letter handling for imports
- replay tooling for failed reconciliation runs
- alerting for rollup failures and drift
- admin diagnostics pages

#### 3. Security review and hardening

Complete:

- auth review
- permission review
- export access review
- payload and privacy review
- approval bypass review
- self-hosted secret management review

#### 4. Customer-facing release assets

Prepare:

- demo workspace with seeded finance and ROI data
- sample invoice files
- reconciliation walkthrough
- ROI walkthrough
- self-hosted enterprise walkthrough
- migration guide from generic observability tools

#### 5. Positioning launch

Update product messaging to consistently say:

- AI spend system of record
- chargeback and finance controls
- invoice reconciliation
- budget-aware runtime control
- outcome and ROI visibility

### Exit criteria

- the platform is ready for external launch around the finance/control-plane narrative
- the core moat features are usable, testable, documented, and benchmarked

---

## Detailed Milestone Table

| Month | Milestone | Primary Outcome |
|-------|-----------|-----------------|
| 1 | Moat Alignment | Packaging, architecture, and scope frozen around finance/control-plane thesis |
| 2 | Reconciliation MVP | External provider invoice reconciliation working end-to-end |
| 3 | ROI Release | Cost linked to outcomes and business value |
| 4 | Enterprise Adoption Layer | SSO, SCIM, approvals, OTel/OpenInference usable |
| 5 | Packaging Release | OSS, SaaS, and Enterprise boundaries enforced and documented |
| 6 | Hardening and Launch | Performance, reliability, security, demos, and positioning ready |

---

## Architecture Additions

### New data entities

Expected additions include:

- `provider_invoices`
- `provider_invoice_lines`
- `reconciliation_matches`
- `reconciliation_issues`
- `dispute_packages`
- `outcomes`
- `outcome_rollups_daily`
- `approval_requests`
- `approval_decisions`
- `sso_configs`
- `scim_provisioning_logs`

### New services

Expected new service modules include:

- invoice import service
- reconciliation matching service
- dispute package service
- ROI calculation service
- OTel/OpenInference translation service
- identity federation service
- provisioning service
- approvals orchestration service
- edition enforcement service

### New workers

Expected new worker families include:

- invoice import parser
- reconciliation batch runner
- ROI rollup job
- warehouse export job
- retention sweeper
- provisioning sync job

---

## Testing Strategy

### Unit tests

Add coverage for:

- request ID matching
- fuzzy reconciliation logic
- outcome and ROI calculations
- approval policy resolution
- OTel/OpenInference transformation
- edition gating logic

### Integration tests

Add coverage for:

- invoice import to reconciliation flow
- SDK to ROI dashboards flow
- gateway to outcome joins
- SSO and SCIM admin flows
- self-hosted deployment validation

### Load tests

Required:

- 10 million line invoice import simulation
- burst OTel ingest simulation
- multi-tenant gateway routing stress
- warehouse export backpressure simulation

### Security tests

Required:

- permission boundary tests
- approval bypass tests
- export authorization tests
- payload access restrictions
- SSO assertion validation

---

## Documentation Plan

By the end of Month 5, documentation should be fully restructured into:

1. Product overview
2. Edition matrix
3. Finance workflows
4. Runtime control workflows
5. Instrumentation guides
6. OTel/OpenInference migration guide
7. Enterprise deployment guide
8. Warehouse export guide
9. Reconciliation guide
10. ROI and outcomes guide

Docs should be treated as product surface, not cleanup work.

---

## Launch Metrics

At the end of 6 months, success should be measured by product capability, not just shipped tickets.

### Product metrics

- provider invoice reconciliation support for at least 2 to 3 major providers
- greater than 90 percent high-confidence match rate in happy-path customer data
- outcome and ROI dashboards live in production
- OTel/OpenInference ingestion adopted in at least one real deployment
- SSO and SCIM validated in enterprise test environments

### Platform metrics

- no critical security gaps in new auth and export surfaces
- reconciliation jobs meet SLA for defined invoice sizes
- gateway policy selection latency remains within target budget
- export jobs and rollups are idempotent and replayable

### Commercial readiness metrics

- clear edition and pricing boundary
- demo environments ready for sales and investor conversations
- migration story against observability-only products documented

---

## Risks And Mitigations

### Risk 1: Overbuilding enterprise before moat completion

Mitigation:

- reconciliation and ROI stay ahead of enterprise polish in priority

### Risk 2: Packaging confusion persists

Mitigation:

- edition enforcement lands before Month 5 is complete
- docs and UI reflect the same commercial boundaries

### Risk 3: Gateway scope explodes

Mitigation:

- support only targeted high-value providers
- do not chase broad provider parity with gateway-first competitors

### Risk 4: OTel ingestion becomes a rewrite

Mitigation:

- normalize into existing data model
- support pragmatic subset first

### Risk 5: New finance workflows become slow or fragile

Mitigation:

- invest in idempotent jobs, replay tooling, and performance testing by Month 6

---

## Recommended Release Narrative

The external release story at the end of this plan should be:

"RunLedger is the AI spend system of record and runtime control plane for production AI products. It reconciles provider invoices, powers internal chargeback, enforces budgets and routing policy, and ties cost to outcomes and ROI."

That narrative is much stronger than a generic observability message and aligns directly with the moat identified in [vc_feedback.md](C:/Users/Abi/Desktop/github/runledger/vc_feedback.md).

---

## Final Recommendation

The company should spend the next 6 months doing fewer things better:

- reconcile real bills
- tie costs to real outcomes
- enforce real controls
- support real enterprise buying requirements
- make the paid moat impossible to confuse with OSS

That is the shortest path from a strong codebase to a defensible company.
