# Part 7 · Settings & Administration

*Prerequisite: Part 1 done. These are the **Settings** sidebar pages — mostly per-workspace
configuration, so switch to the team you're configuring first.*

Part 1 already covered **API Keys** (Module 3) and Part 2 covered **Alert Rules**. This part
walks the rest of the Settings sidebar.

---

## 7.1 · OTLP

**Goal:** point any OpenTelemetry app at RunLedger.

Open **Settings → OTLP**. It shows the ingestion endpoint (`/v1/traces`) and how to send
spans. You already exercised this in **Part 1, Lab 02** (out-of-band OTLP). The stack also
runs an OTel Collector on `:4318` if you'd rather fan many services through a collector.

🔎 Nothing to configure for the basics — the page is the "how to connect" reference. Confirm
your Lab 02 traces show up on the Runs page.

---

## 7.2 · MCP

**Goal:** let an MCP client (e.g. Claude Desktop) use RunLedger's tools.

Open **Settings → MCP**. RunLedger exposes its cognitive layer + analytics as **MCP tools**
(memory, knowledge graph, skills, etc.). The page shows the MCP endpoint and how to connect a
client with your workspace key. See [`examples/21_mcp_example.py`](../../../../examples/21_mcp_example.py)
for a client walkthrough.

🔎 This is how agents *outside* RunLedger reuse its shared memory/skills — workspace-scoped,
same key model as everything else.

---

## 7.3 · Integrations

**Goal:** wire up Slack so alerts have somewhere to go.

1. Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) in your Slack.
2. Open **Settings → Integrations**, paste the webhook URL, and **Test** it — a message should
   land in your channel.
3. Now the Alert Rules from Part 2 can notify Slack when they fire.

🔎 Integrations turn RunLedger from a dashboard you check into a system that pings you.

---

## 7.4 · Data Capture (privacy modes)

**Goal:** control how much of each prompt/response RunLedger stores.

Open **Settings → Data Capture**. Set the **privacy mode**:

| Mode | Stores |
|---|---|
| `metadata_only` (default) | tokens/latency/cost only — no prompt or response text |
| `errors_only` | payloads only for failed runs |
| `sampled` | a percentage of payloads (set the sample rate) |
| `full` | every prompt and response |

**See it change:**
1. Leave it on `metadata_only`, generate traffic, open a run → **no** prompt/response text.
   ```bash
   LAB_FEATURE_TAG=capture-test LAB_RUNS=10 python traffic_gen.py
   ```
2. Switch to `full`, generate more traffic, open a new run → the prompt and response **are**
   captured.

🔎 This is the privacy dial: richer debugging vs. storing less sensitive data. It's
per-workspace, so different teams can have different postures.

---

## 7.5 · Compliance

**Goal:** see your governance posture in one place.

Open **Settings → Compliance**. It surfaces the controls you configure elsewhere — the Data
Capture policy (7.4), gateway **PII redaction** (Part 5), **audit logs** (Part 2), and
**retention** (7.6) — so you can show an auditor "here's what we capture, redact, log, and for
how long."

🔎 Compliance isn't a separate switch; it's the summary view of the guardrails you've set.

---

## 7.6 · Data Retention

**Goal:** automatically delete old data — and prove what a purge would remove first.

1. Open **Settings → Data Retention** → create a policy: e.g. `max_age_days = 90` for runs.
2. Run a **dry-run purge** — it reports what *would* be deleted without touching anything.
3. When you're comfortable, disable dry-run to let it (and the scheduled purge) enforce.

🔎 Retention is how you keep storage bounded and honour data-minimisation promises. Always
dry-run first.

---

## 7.7 · Email

**Goal:** choose which notifications land in your inbox.

Open **Settings → Email**. Set the **report frequency** (`daily`/`weekly`/`monthly`/`never`)
and toggle categories: alerts, approvals, reconciliation, budget alerts, billing closed,
score regressions, dispute flags.

🔎 Pair this with Integrations (7.3): Slack for real-time pings, email for the digest.

---

✅ **End of Part 7.** You've configured the full Settings surface — ingestion, MCP, Slack,
privacy/capture, compliance posture, retention, and email. Combined with Parts 1–6, that's
every page in the dashboard exercised.
