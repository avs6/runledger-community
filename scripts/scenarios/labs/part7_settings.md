# Part 7 - Control Plane & Platform Settings

*Prerequisite: Part 1 done. Control Plane pages are org-admin visible, with API Keys also available to workspace admins for their active workspace. Settings is platform-admin-only.*

Part 1 already covered **API Keys** (Module 3) and Part 2 covered **Alert Rules**. This part walks the rest of the moved Control Plane pages plus the platform-only Settings pages.

Use this role split while working through the page:

| Sidebar area | Pages | Role |
|---|---|---|
| Control Plane | API Keys, Alert Rules, MCP, Integrations, Data Capture, OTLP | Org admin; API Keys also works for workspace admins on their active workspace |
| Settings | Compliance, Data Retention, Email | Platform admin only |

---

## 7.1 - OTLP

**Goal:** point any OpenTelemetry app at RunLedger.

Open **Control Plane -> OTLP**. It shows the ingestion endpoints, OTEL-derived trend charts, top `service.name` values, and semantic attribution coverage. You already exercised this in **Part 1, Lab 02** (out-of-band OTLP). The stack also runs an OTel Collector on `:4318` if you'd rather fan many services through a collector, and that collector expects the same workspace API key as a Bearer token on inbound OTLP traffic.

Nothing to configure for the basics - the page is the "how to connect" reference. Confirm your Lab 02 traces show up on the Runs page.

---

## 7.2 - MCP

**Goal:** let an MCP client (e.g. Claude Desktop) use RunLedger's tools.

Open **Control Plane -> MCP**. RunLedger exposes its cognitive layer + analytics as **MCP tools** (memory, knowledge graph, skills, etc.). The page shows the MCP endpoint and how to connect a client with your workspace key. See [`examples/21_mcp_example.py`](../../../../examples/21_mcp_example.py) for a client walkthrough.

Use the key for the workspace you want the MCP calls attributed to. For this workbook, use the
**AI Test Team** key first so the MCP optimization exercises line up with Part 4.

After connecting, try these tools:

| Tool | Try this |
|---|---|
| `select_tools` | Pass the query and tool list from Part 4.6; confirm it keeps only the relevant tools. |
| `compile_context` | Pass a duplicated or oversized `messages` array; confirm the token report shows savings. |
| `flywheel_analyze` | Pass sample segment observations; confirm it recommends the cheapest config above the quality floor. |
| `memory_store` / `memory_recall` | Store "Acme uses Qdrant for semantic cache" and recall it from another MCP client. |
| `kg_add_entity` / `kg_neighbors` | Add `svc-api -> qdrant` and query neighbors. |
| `skill_list` / `skill_get` | Confirm skills are visible for skill-injection workflows. |

If an MCP client is not handy, use the generated Postman collection's direct service folders:
**Context Compiler Service**, **Router Service**, **Flywheel Service**, **Memory Service**,
**Knowledge Graph**, and **Skill Registry**. That is the same optimization layer behind the MCP gateway.

---

## 7.3 - Integrations

**Goal:** wire up Slack so alerts have somewhere to go.

1. Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) in your Slack.
2. Open **Control Plane -> Integrations**, paste the webhook URL, and **Test** it - a message should land in your channel.
3. Now the Alert Rules from Part 2 can notify Slack when they fire.

---

## 7.4 - Data Capture & Capture Policy Studio

**Goal:** control how much of each prompt/response RunLedger stores.

Open **Control Plane -> Data Capture**. Set the **privacy mode**:

| Mode | Stores |
|---|---|
| `metadata_only` (default) | tokens/latency/cost only - no prompt or response text |
| `errors_only` | payloads only for failed runs |
| `sampled` | a percentage of payloads (set the sample rate) |
| `full` | every prompt and response |

**Data Capture Policy Studio** — scope capture rules per workspace, feature, or model:

1. Open the **Scoped Policies** tab on the Data Capture page.
2. Add a scope: e.g. `feature_tag = support-chat` → `full` capture (you want every support
   interaction stored for compliance), but `feature_tag = internal-test` → `metadata_only`.
3. Test PII redaction: paste a sample prompt containing an email or phone number and click
   **Test PII** — the preview shows what would be redacted before storage.
4. Review the **retention preview** to see how the current capture policy affects storage
   volume over time.

---

## 7.5 - Compliance *(platform admin only)*

Open **Settings -> Compliance** as a platform admin. It summarizes Data Capture policy, gateway PII redaction, audit logs, and retention posture.

---

## 7.6 - Data Retention *(platform admin only)*

Open **Settings -> Data Retention** as a platform admin. Create a policy, dry-run a purge, then enable enforcement when comfortable.

---

## 7.7 - Email *(platform admin only)*

Open **Settings -> Email** as a platform admin. Set report frequency and notification categories.

---

End of Part 7: org admins exercise Control Plane; platform admins exercise Settings.
