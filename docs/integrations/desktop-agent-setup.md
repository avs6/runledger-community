# Desktop Agent Setup And Validation

RunLedger already ships the product-side pieces for Claude, Codex, Cursor, Devin, and similar desktop-agent integrations.

What remains in real deployments is usually host-side setup:

- adding the MCP server entry in the client
- installing the matching instruction file or skill
- restarting the host application
- validating that the client can see the server and call tools

That is operational setup work, not a remaining product backlog item.

## Use this document for

- Claude Desktop
- Claude Code
- OpenAI Codex
- Cursor
- Windsurf
- Devin-style wrapper or bridge setups

## Shared prerequisites

Before validating any desktop agent:

1. make sure RunLedger API is reachable
2. create or copy a workspace API key
3. confirm the canonical MCP endpoint:

```text
http://localhost:8201/mcp
```

4. optionally confirm the local stdio bridge works:

```powershell
$env:RUNLEDGER_BASE_URL = "http://localhost:8201"
$env:RUNLEDGER_API_KEY = "<workspace-api-key>"
python scripts\runledger\mcp_stdio_bridge.py
```

5. run the connection validator:

```powershell
$env:RUNLEDGER_BASE_URL = "http://localhost:8201"
$env:RUNLEDGER_API_KEY = "<workspace-api-key>"
python scripts\runledger\validate_mcp_connection.py
```

If the validator succeeds, RunLedger is exposing the expected `runledger.*` control-plane tools.

## Shared validation checklist

For every desktop agent, validate the same five things:

1. the client can load the MCP server entry
2. the client can see at least one `runledger.*` tool
3. the workspace API key is being passed correctly
4. a smoke-test task produces telemetry
5. the resulting run appears in `Runs` or `Request Explorer`

## Claude Desktop

1. Add the `runledger` MCP server entry to Claude Desktop config.
2. Point it at `http://localhost:8201/mcp` or the local stdio bridge.
3. Set `RUNLEDGER_API_KEY`.
4. Restart Claude Desktop completely.
5. Open a small test chat and call:
   - `runledger.budget_check`
   - `runledger.record_run_start`
   - `runledger.record_outcome`
6. Confirm the run appears in the dashboard.

If Claude does not show the server after restart, re-check JSON syntax, the workspace key, and whether the app loaded the updated config file.

## Claude Code

1. Add the MCP server with the HTTP transport or stdio bridge.
2. Export `RUNLEDGER_API_KEY`.
3. Run a small task and call the same smoke-test tools.
4. Verify the resulting run in RunLedger.

## OpenAI Codex

1. Add the `runledger` MCP server entry in Codex config.
2. Point it at the canonical `/mcp` endpoint.
3. Set `RUNLEDGER_API_KEY`.
4. Restart Codex or reload its MCP configuration.
5. Ask Codex to run a small instrumented task and confirm:
   - tool visibility
   - successful tool invocation
   - resulting run visibility in the dashboard

If Codex can reach the endpoint but no tools appear, re-run `scripts/runledger/validate_mcp_connection.py` outside the app first. That separates server issues from host-client issues quickly.

## Cursor

1. Add the `runledger` MCP server entry in Cursor settings.
2. Set the workspace API key.
3. Restart Cursor or reload MCP settings.
4. Run a small coding or planning task that touches the RunLedger tools.
5. Confirm the resulting run in RunLedger.

## Windsurf

1. Add the `runledger` server entry in the Windsurf MCP config.
2. Pass the API key through the expected auth path.
3. Restart or reload the tool host.
4. Run a smoke-test task and verify telemetry landed.

## Devin-style bridge setups

Devin-style integrations usually need a wrapper, bridge, or service user rather than a direct desktop config edit.

Validate them in this order:

1. confirm the service user or runner can reach RunLedger
2. confirm the workspace key is injected
3. confirm the bridge can call `runledger.record_run_start`
4. confirm model or tool events can be recorded
5. confirm the final task outcome lands in RunLedger

## Suggested smoke-test task

Use the smallest possible task:

1. call `runledger.budget_check`
2. call `runledger.record_run_start`
3. do one tool call or one model call
4. call `runledger.record_outcome`
5. open the dashboard and confirm the run exists

This is enough to verify:

- auth
- MCP connectivity
- telemetry recording
- dashboard visibility

## Troubleshooting

### Validator works, app does not

This usually means the problem is in the host app config, restart behavior, or environment propagation, not RunLedger itself.

### App sees server, but tools fail

Check:

- workspace API key validity
- auth header or env wiring
- whether the client expects HTTP MCP or only stdio

### Run does not appear in the dashboard

Check:

- the workspace tied to the API key
- whether the smoke-test task actually called `record_run_start`
- whether the dashboard is filtered to another org or workspace

## Related docs

- [MCP integration options](../integration-options-mcp.md)
- [Demo runbook](../demo-runbook.md)
