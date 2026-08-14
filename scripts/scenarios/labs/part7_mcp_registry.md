# Part 7B - MCP Registry

*Prerequisite: Part 1 completed.*

Use this lab after you have workspace keys and at least one admin-capable session.

Recommended workspace:

- `LocalAIAgentStack / Codex`
- `LocalAIAgentStack / Claude Desktop`
- `LocalAIAgentStack / LiteLLM Gateway`

## Goal

Validate that **MCP Registry** is the single control-plane home for MCP setup and server lifecycle management.

You should confirm:

- setup guidance is present
- server create, edit, deactivate, and re-activate flows work
- discovered tool/resource/prompt inventory is visible
- permission-policy create and revoke flows work
- tool-call testing and call history work

## Manual steps

### 1. Open the consolidated MCP surface

1. Open **MCP** from the left navigation.
2. Verify it lands on **MCP Registry** setup instead of a separate legacy management page.

### 2. Review Setup & Connect

Open the **Setup & Connect** tab and confirm you can see copyable guidance for:

- Claude Desktop
- Claude Code
- Cursor
- Windsurf
- Codex
- Direct HTTP MCP
- stdio bridge

### 3. Seed default servers

Use **Populate Default Servers**.

Verify the workspace now has seeded server entries such as:

- GitHub MCP Server
- PostgreSQL MCP Server
- Brave Search MCP Server

### 4. Create a custom server

Create a custom MCP server entry with values like:

- Name: `Workspace File MCP`
- Transport: `stdio`
- Command: `npx`
- Args: `-y @modelcontextprotocol/server-filesystem ./workspace`
- Description: `Workspace-scoped file access`

Verify it appears in the inventory list and can be selected for detail review.

### 5. Edit the server

Edit the custom server and change one or more of:

- description
- command arguments
- auth type
- env JSON

Verify the detail panel reflects the saved changes.

### 6. Review discovered inventory

Select a seeded or custom server and inspect:

- discovered tools
- discovered resources
- discovered prompts

Verify the detail panel behaves like a real registry page rather than a static card list.

### 7. Create a permission policy

Open **Permissions & Policies** and create a policy for one active server.

Use:

- Scope type: `workspace`
- Scope id: the active workspace id
- Allowed tools: one or two tool names from the selected server

Verify the policy appears in the list.

### 8. Run a test tool call

Open **Discovered Tools**, pick one tool, and execute a test call.

Verify:

- the call succeeds or returns a governed/pending state
- a new record appears in **Tool Calls Log**

### 9. Deactivate and re-activate

Go back to **MCP Servers**:

- deactivate the custom server
- enable **Show inactive**
- re-activate the same server

Verify the lifecycle state changes are visible in the inventory.

## Automated companion

Run the matching smoke test:

```bash
uv run python scripts/runledger/exercise_mcp_registry.py
```
