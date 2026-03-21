"""
Example 21 — MCP tool-call tracking with RunLedger.

This example shows two things:
  1. How to use the RunLedger MCP server from Claude Desktop.
  2. How to track MCP tool calls from the SDK side when your agent uses an
     mcp.ClientSession directly.

────────────────────────────────────────────────────────────────────────────────
Part A: Claude Desktop config
────────────────────────────────────────────────────────────────────────────────
Add the following to ~/.config/claude/claude_desktop_config.json (macOS/Linux)
or %APPDATA%\\Claude\\claude_desktop_config.json (Windows):

    {
      "mcpServers": {
        "runledger": {
          "command": "python",
          "args": ["-m", "runledger_api.mcp_server"],
          "env": {
            "RUNLEDGER_API_KEY": "rl_live_...",
            "RUNLEDGER_BASE_URL": "http://localhost:8000"
          }
        }
      }
    }

After restarting Claude Desktop you'll have access to RunLedger tools:
  - list_runs, get_run, get_analytics_summary, get_spend_by_model
  - list_budgets, check_budget
  - list_alert_rules, get_alert_history
  - list_prompts, get_prompt
  - get_cost_regressions, get_sessions

And a resource: runledger://workspace/stats

────────────────────────────────────────────────────────────────────────────────
Part B: SDK-side MCP tool-call tracking
────────────────────────────────────────────────────────────────────────────────
When your own agent code uses mcp.ClientSession to call tools, wrap the session
with rl.instrument_mcp(session) to automatically capture every tool call as a
tool_call event in RunLedger.

Requirements:
    pip install "mcp>=1.9.0"

Run:
    python examples/21_mcp_example.py
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

load_dotenv("examples/.env")

from runledger_sdk import RunLedger  # noqa: E402


async def main() -> None:
    rl = RunLedger()

    # ── Attempt to connect to a local MCP server ───────────────────────────
    # This demonstrates the pattern; adjust the command/args for your own
    # MCP server.  The example gracefully skips if mcp is not installed.
    try:
        from mcp import ClientSession, StdioServerParameters  # noqa: PLC0415
        from mcp.client.stdio import stdio_client  # noqa: PLC0415
    except ImportError:
        print("mcp package not installed. Run: pip install 'mcp>=1.9.0'")
        print("Showing SDK instrumentation pattern only.\n")
        _show_pattern(rl)
        return

    # Example: connect to a filesystem MCP server (npx @modelcontextprotocol/server-filesystem)
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
    )

    print("Connecting to MCP server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("MCP session initialised.")

            # Instrument the session — all tool calls are now tracked
            rl.instrument_mcp(session)

            with rl.context(end_user_id="user_42", feature_tag="mcp-demo"):
                # List available tools
                tools_result = await session.list_tools()
                print(f"Available tools: {[t.name for t in tools_result.tools]}")

                # Call a read tool (tracked as tool_type='read')
                if any(t.name == "list_directory" for t in tools_result.tools):
                    result = await session.call_tool("list_directory", {"path": "."})
                    print("Directory listing:", result.content[:1] if result.content else "(empty)")

    rl.flush()
    print("Tool calls tracked in RunLedger.")


def _show_pattern(rl: RunLedger) -> None:
    """Print the instrumentation pattern without requiring a live MCP server."""
    print(
        "Pattern for SDK-side MCP tracking:\n"
        "\n"
        "    from mcp import ClientSession\n"
        "    from runledger_sdk import RunLedger\n"
        "\n"
        "    rl = RunLedger(api_key='rl_live_...')\n"
        "\n"
        "    async with ClientSession(read_stream, write_stream) as session:\n"
        "        await session.initialize()\n"
        "        rl.instrument_mcp(session)   # <-- one line\n"
        "\n"
        "        with rl.context(end_user_id='u123', feature_tag='my-agent'):\n"
        "            result = await session.call_tool('search', {'query': 'hello'})\n"
        "\n"
        "    rl.flush()\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
