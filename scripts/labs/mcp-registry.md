# MCP Registry

Validate that **MCP Registry** is the single control-plane home for MCP server
lifecycle management.

Recommended workspace: `LocalAIAgentStack / Codex`, `Claude Desktop`, or `LiteLLM Gateway`.

## What to Confirm

- Setup guidance is present for all supported clients
- Server create, edit, deactivate, and re-activate flows work
- Discovered tool/resource/prompt inventory is visible
- Permission-policy create and revoke flows work
- Tool-call testing and call history work

## Steps

### Open MCP Registry

Open **MCP** from the left navigation. Verify it lands on **MCP Registry**.

### Setup & Connect

Open the **Setup & Connect** tab and confirm copyable guidance for:

- Claude Desktop
- Claude Code
- Cursor
- Windsurf
- Codex
- Direct HTTP MCP
- stdio bridge

### Seed Default Servers

Use **Populate Default Servers**. Verify seeded entries such as:

- GitHub MCP Server
- PostgreSQL MCP Server
- Brave Search MCP Server

### Create a Custom Server

Create a server:

- Name: `Workspace File MCP`
- Transport: `stdio`
- Command: `npx`
- Args: `-y @modelcontextprotocol/server-filesystem ./workspace`
- Description: `Workspace-scoped file access`

Verify it appears in the inventory.

### Edit the Server

Change one or more of: description, command arguments, auth type, env JSON.
Verify the detail panel reflects saved changes.

### Discovered Inventory

Select a server and inspect discovered tools, resources, and prompts.

### Permission Policies

Open **Permissions & Policies** and create a policy:

- Scope type: `workspace`
- Scope id: the active workspace id
- Allowed tools: one or two tool names from the selected server

### Test a Tool Call

Open **Discovered Tools**, pick one, and execute a test call.
Verify it succeeds or returns a governed state, and a record appears in **Tool Calls Log**.

### Deactivate & Re-Activate

- Deactivate the custom server
- Enable **Show inactive**
- Re-activate the same server

Verify lifecycle state changes are visible in the inventory.
