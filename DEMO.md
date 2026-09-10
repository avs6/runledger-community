# RunLedger Demo Playbook

All commands run from the repo root: `C:\Users\Abi\Desktop\github\runledger-community`

---

## Prerequisites

- Docker Desktop running
- `uv` on PATH (installed at `C:\Users\Abi\AppData\Local\com.LangflowDesktop\uv\uv.exe`)

---

## 1. Start the Stack

```powershell
docker compose up -d
```

Wait ~30s for containers to become healthy:

```powershell
docker compose ps
```

---

## 2. Seed the Full Demo (optional — only needed on first run or after a reset)

```powershell
uv run --python 3.13 --with httpx scripts/core/full_simulate.py --traffic-multiplier 5
```

This takes 2–3 minutes and creates both orgs, all workspaces, ~8,000 runs with spans, tool calls, outcomes, budgets, alerts, forecasts, guardrails, agents, workflows, and more.

> **Warning:** This resets all data. If you just want to add more traffic on top of existing data, pass `--no-clean`:
>
> ```powershell
> uv run --python 3.13 --with httpx scripts/core/full_simulate.py --traffic-multiplier 5 --no-clean
> ```

---

## 3. Generate Continuous Live Traffic

### HomeLab / AgentTest

```powershell
uv run --python 3.13 scripts/localai/generate_agent_traffic.py --state-file scripts/.homelab-runledger.json --workspace AgentTest --source homelab --batches 999999 --batch-size 25 --sleep 2.0
```

### LocalAIAgentStack (all 8 workspaces in parallel)

Open separate PowerShell tabs for each, or run them with `Start-Process`:

```powershell
# SDK agent traffic
uv run --python 3.13 scripts/localai/generate_agent_traffic.py --state-file scripts/.localai-runledger.json --workspace PythonAgents --source python --batches 999999 --batch-size 25 --sleep 2.0
uv run --python 3.13 scripts/localai/generate_agent_traffic.py --state-file scripts/.localai-runledger.json --workspace "LiteLLM Gateway" --source litellm --batches 999999 --batch-size 25 --sleep 2.0
uv run --python 3.13 scripts/localai/generate_agent_traffic.py --state-file scripts/.localai-runledger.json --workspace Codex --source codex --batches 999999 --batch-size 25 --sleep 2.0
uv run --python 3.13 scripts/localai/generate_agent_traffic.py --state-file scripts/.localai-runledger.json --workspace HermesAgent --source hermes --batches 999999 --batch-size 25 --sleep 2.0
uv run --python 3.13 scripts/localai/generate_agent_traffic.py --state-file scripts/.localai-runledger.json --workspace "Claude Desktop" --source claude --batches 999999 --batch-size 25 --sleep 2.0

# OTLP trace traffic
uv run --python 3.13 scripts/localai/generate_otlp_traffic.py --state-file scripts/.localai-runledger.json --workspace OpenWebUI --source openwebui --batches 999999 --traces 40 --sleep 2.0
uv run --python 3.13 scripts/localai/generate_otlp_traffic.py --state-file scripts/.localai-runledger.json --workspace Langgraph --source langgraph --batches 999999 --traces 40 --sleep 2.0
uv run --python 3.13 scripts/localai/generate_otlp_traffic.py --state-file scripts/.localai-runledger.json --workspace OpenAICodes --source openai-codes --batches 999999 --traces 40 --sleep 2.0
```

Press **Ctrl+C** in any tab to stop that stream.

---

## Organizations & Credentials

### HomeLab (Starter plan — 1 workspace)

| | |
|---|---|
| **Dashboard** | http://localhost:3201 |
| **Admin login** | `admin@homelab.com` / `runledger` |
| **Users** | `user1@homelab.com`, `user2@homelab.com` (password: `runledger`) |

| Workspace | Workspace ID | API Key |
|---|---|---|
| AgentTest | `f87ea6c4-8c08-4acd-abf9-7893b9732d3e` | `rl_test_OKlri_Gfmzp14RjIYCGuI_03LIclUV_JVq3P4G7dZ9Y` |

State file: `scripts/.homelab-runledger.json`

### LocalAIAgentStack (Enterprise plan — 8 workspaces)

| | |
|---|---|
| **Dashboard** | http://localhost:3201 |
| **Admin login** | `admin@localstack.com` / `runledger` |
| **Users** | `user1@localstack.com`, `user2@localstack.com` (password: `runledger`) |

| Workspace | Workspace ID | API Key |
|---|---|---|
| LiteLLM Gateway | `8f085705-08c7-4567-8e5c-0dee454b6d20` | `rl_test_bg3LiMNdeZe7bU6kdX9jE_jFE1-T2o1lV--7aGTsv5Q` |
| OpenWebUI | `0ae53c5a-cac3-4c91-9d25-c37a1b9d098f` | `rl_test_O-vNKQR4vDFytuCmgfBi2UW3yk2C3Fgoj6UIkaJp5fw` |
| Codex | `ef2afd37-9892-42ee-9815-fd6a69dd205e` | `rl_test_tvGRqxmPl9J8wilLYmou5NvtXj3NB3QFUGKXXycF9XI` |
| Langgraph | `80bef9d2-5b1e-49e1-b7d2-5e156fa957dd` | `rl_test_kdmbQS5iyELuqU4PDQf8wyYhF-X2COWNk_M8MAf9n3s` |
| HermesAgent | `e7d6f9ef-6416-4ed8-b804-6848be2ecd7f` | `rl_test_lV-B_W92y0Gjg0iCxDAl0mEDbn4jd2VFYJLEdenWzTE` |
| Claude Desktop | `c756cd67-545f-40f5-8d4b-c848d44baffe` | `rl_test_Uj30HCDg_hM7HNlHYoZtTj5zY5VqWJ62vKujUGkVzIQ` |
| OpenAICodes | `de33801d-ff6b-4bc2-8863-ca9867afba50` | `rl_test_Mzs-epqa07u19nB1OyK5IfnpJRt_dIKAG0ncmTHWJfA` |
| PythonAgents | `abd4db8e-5835-4547-84a7-2ec5dbf01de1` | `rl_test_a5pbpZzKpzE0A8Bq-Zx61LHy-QmPWQrPUFGGGHbGxaY` |

State file: `scripts/.localai-runledger.json`

### Platform Admin

| | |
|---|---|
| **Email** | `admin@runledger.local` |
| **Password** | `runledger` |

---

## Quick Reference

| Task | Command |
|---|---|
| Start stack | `docker compose up -d` |
| Stop stack | `docker compose stop` |
| Full reset + seed | `uv run --python 3.13 --with httpx scripts/core/full_simulate.py --traffic-multiplier 5` |
| Add traffic (no reset) | `uv run --python 3.13 --with httpx scripts/core/full_simulate.py --traffic-multiplier 5 --no-clean` |
| Continuous HomeLab traffic | See Section 3 above |
| Rebuild containers | `docker compose build --no-cache runledger-web runledger-api` |
| Rebuild + restart | `docker compose up -d --build runledger-web runledger-api` |
| View logs | `docker compose logs -f runledger-api runledger-web` |

---

## Notes

- API keys survive container restarts (`docker compose stop` / `docker compose up -d`). They are stored in Postgres which persists in a Docker volume.
- Running `full_simulate.py` **without** `--no-clean` truncates all data and mints new API keys — the keys in this file and the state files become stale. Either pass `--no-clean`, or re-mint keys from Settings > API Keys in the dashboard and update the state files.
- The traffic generator scripts (`generate_agent_traffic.py`, `generate_otlp_traffic.py`) use only stdlib — no `httpx` needed. The `--with httpx` flag is only required for `full_simulate.py`.
