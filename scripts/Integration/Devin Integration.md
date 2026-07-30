# Devin Integration

## Goal

Connect Devin to RunLedger so hosted autonomous development work is tracked as real agentic usage: sessions, repos, task outcomes, cost attribution, budget checks, and optimization feedback.

Devin should use its own RunLedger workspace once the demo moves beyond early testing:

- RunLedger workspace: `Devin`
- API key: `RUNLEDGER_KEY_DEVIN`

## Best Integration Paths

| Path | Use It For | Notes |
|---|---|---|
| Devin API wrapper | Create sessions, record task metadata, track status, attach repo/issue/outcome | Best first integration because Devin exposes API/service-user automation |
| Webhook bridge | Convert external tickets/events into Devin sessions and RunLedger runs | Good for demoing lifecycle automation |
| RunLedger Gateway | Inline token/cost enforcement only if the Devin execution path can be configured to use an OpenAI-compatible model endpoint | Treat as optional until provider routing support is confirmed |
| MCP | Give Devin-adjacent workflows access to RunLedger budget, analytics, optimization, and experiment tools | Useful if the local client or bridge can call MCP tools |
| OTLP/wrapper spans | Capture orchestration spans around Devin tasks | Useful even when token-level usage is not exposed |

## Recommended Architecture

```text
Ticket / manual request / local script
        |
        v
RunLedger Devin Bridge
  - budget pre-check
  - create RunLedger run
  - call Devin API
  - poll or receive webhook status
  - record outcome
        |
        v
Devin session
        |
        v
RunLedger
  - task cost estimate or imported usage
  - repo/task metadata
  - success/failure/outcome
  - budget and alert events
```

## Environment

```env
RUNLEDGER_BASE_URL=http://localhost:8201
RUNLEDGER_KEY_DEVIN=rl_...
DEVIN_API_BASE_URL=https://api.devin.ai
DEVIN_API_KEY=cog_...
```

For automation, use a Devin service user token rather than a human user token. Devin's API docs describe service users as separate from human users and intended for API automation.

## Bridge Flow

1. Receive a request from a local CLI, issue tracker, or demo script.
2. Call RunLedger to check the `Devin` workspace budget and policy.
3. Create a RunLedger run with `agent_client=devin`.
4. Call Devin API to create the Devin session.
5. Store the Devin session ID in RunLedger metadata.
6. Poll Devin or process the completion webhook.
7. Record outcome, repo, branch/PR, elapsed time, and any available usage/cost.
8. Close the RunLedger run.

## Example Run Metadata

```json
{
  "agent_client": "devin",
  "workspace": "Devin",
  "repo": "runledger-community",
  "task_type": "code_change",
  "task_id": "ticket-1234",
  "session_id": "devin-session-id",
  "spawned_by": "automation",
  "control_path": "api_wrapper",
  "budget_policy": "devin-daily-cap",
  "result": "success"
}
```

## FinOps And Observability

RunLedger should show:

- Devin sessions by repo, task type, requester, and status.
- Cost per successful task, even if cost is estimated or imported later.
- Time-to-completion and failure reasons.
- Budget alerts before starting expensive autonomous sessions.
- Outcomes such as PR opened, tests passed, review required, abandoned, or reverted.

## Control Points

- Pre-launch budget check in the bridge.
- Workspace budgets in RunLedger Finance.
- Alert Rules for daily Devin spend, failed sessions, and long-running tasks.
- Optional Gateway route caps if Devin can be pointed at RunLedger Gateway.
- Optional MCP policy tools if a local Devin/Cascade surface can call RunLedger.

## Demo Scenario

Use a ticket such as:

```text
Fix a failing simulation scenario and open a PR.
```

Expected RunLedger story:

- RunLedger records the Devin run before the session starts.
- The bridge links the Devin session ID.
- The run closes with outcome `PR opened` or `blocked`.
- Finance shows estimated cost per completed task.

## Limitations

If Devin's hosted model calls cannot be routed through RunLedger Gateway, RunLedger cannot enforce exact token spend inline. The bridge still provides practical FinOps by controlling session launch, recording elapsed work, importing available usage, and comparing outcomes across agents.

## Official Docs Consulted

- Devin API overview: https://docs.devin.ai/api-reference/overview
- Devin webhook/API automation example: https://docs.devin.ai/use-cases/gallery/api-webhook-custom-ticketing
