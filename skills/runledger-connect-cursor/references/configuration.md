# Cursor Configuration Notes

Generate Cursor rules:

```bash
python skills/shared/scripts/install_agent_instructions.py --client cursor --repo /path/to/repo
```

Recommended MCP connection:

```text
RunLedger MCP URL: http://localhost:8206/mcp
RunLedger API URL: http://localhost:8201
```

Where Cursor supports custom model endpoints, configure the model client to use RunLedger Gateway for inline budget, routing, caching, and policy control.

Validate with:

```bash
python skills/shared/scripts/runledger_smoke.py --client cursor --task "cursor setup smoke"
```
