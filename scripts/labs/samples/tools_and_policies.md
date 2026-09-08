# Tool Registry — tool names & policies to try

The Tool Registry governs which tools your agents may call. Each tool gets a **policy**:

| Policy | Effect |
|---|---|
| `allow` | Tool runs; nothing recorded |
| `audit` | Tool runs, but every call is logged as a security event |
| `block` | With **runtime enforcement ON**, the call is refused before it runs (SDK raises `ToolBlockedError`) |

Register these on the **Tool Registry** page (Tool Registry → New), using the names and
policies below.

| Tool name | Policy | Runtime enforcement | Why |
|---|---|---|---|
| `search_kb` | `allow` | off | Safe read — let it run freely |
| `lookup_order` | `audit` | off | Reads customer data — log every use |
| `refund_customer` | `block` | **on** | Moves money — must be refused unless a human approves |
| `delete_account` | `block` | **on** | Destructive — always blocked |

---

## See a policy act — no script needed

The gateway/SDK resolves a tool's policy via `GET /tools/check/{tool_name}`. Check one
directly with your workspace key:

```bash
curl -s -H "Authorization: Bearer $RUNLEDGER_API_KEY" \
  http://localhost:8201/tools/check/refund_customer
```

- `refund_customer` (block + enforcement) → **HTTP 403** and a security event is written.
- `search_kb` (allow) → `{"allowed": true, ...}`.

🔎 Observe: on the Tool Registry page, blocked attempts show under **security events**
(`tool_runtime_blocked`). In a real agent instrumented with `tool_enforcement=True`, that
403 becomes a `ToolBlockedError` raised *before* the tool executes — so a risky action
never happens.

> This is the enforcement half of governance; the **Approvals** module is the
> human-in-the-loop half — route a blocked/risky action to a person to approve or deny.
