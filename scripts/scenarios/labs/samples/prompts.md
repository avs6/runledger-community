# Sample prompts — paste these into the **Prompts** page

Create each prompt in the dashboard (Prompts → New Prompt), then add the version
content below. `{{variables}}` are filled at render time. Where two versions are
shown, add v1 to **staging** first, then **promote** to production — that's how you
demo the version history + promote flow.

---

## Prompt 1 — `support-agent`

- **Name:** `support-agent`
- **Description:** Customer-support system prompt
- **Default environment:** production

**Version 1 — environment `staging`, model hint `llama3.2`**

Commit message: `initial support prompt`

```
You are a support agent for {{company}}. Be {{tone}} and concise.
Only answer using known facts; if unsure, offer to escalate to a human.
Never invent policy details.
```

Variables: `company` (string), `tone` (string, e.g. "friendly")

**Version 2 — environment `staging`, model hint `llama3.2`**

Commit message: `add refund guardrail`

```
You are a support agent for {{company}}. Be {{tone}} and concise.
Only answer using known facts; if unsure, offer to escalate to a human.
Never invent policy details. For refunds, always state the 5 business-day window.
```

➡️ Then **promote** the version you prefer from `staging` to `production`. Runs that
use the production prompt will roll up under it on the Prompts detail page (run count,
avg cost, avg score per version).

---

## Prompt 2 — `ticket-summarizer`

- **Name:** `ticket-summarizer`
- **Description:** Summarize a support thread into one line
- **Default environment:** production

**Version 1 — environment `production`, model hint `llama3.2`**

Commit message: `v1`

```
Summarize the following support conversation in one sentence,
capturing the customer's core issue and whether it was resolved.

Conversation:
{{conversation}}
```

Variables: `conversation` (string)

---

## How the traffic generator uses a prompt

The agent can fetch a rendered prompt by name (the SDK's `get_prompt`), so once
`support-agent` is in **production**, real runs link to that version. In the workbook
you'll generate traffic tagged for the team, then watch the per-version metrics fill in.
