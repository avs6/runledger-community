"""
Shared configuration for the RunLedger lab agents.

Every lab script imports this so the connection details live in one place. Values
come from the `.env` file next to this module (copy `.env.example` → `.env` first).

You normally only need to set two things in `.env`:

    RUNLEDGER_API_KEY   the workspace key you minted in the dashboard (Settings → API Keys)
    OLLAMA_MODEL        a model you've pulled, e.g. `ollama pull llama3.2`

Everything else has sensible defaults for the local Docker stack.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from this folder regardless of where the script is run from.
load_dotenv(Path(__file__).resolve().parent / ".env")

# Force UTF-8 so the ✓/→ console output never crashes on a non-UTF-8 host (Windows cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

# ── RunLedger ────────────────────────────────────────────────────────────────
# The local Docker stack maps the API to host port 8201 (container 8000).
RUNLEDGER_BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
RUNLEDGER_API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

# ── Ollama ───────────────────────────────────────────────────────────────────
# When you (the agent) run on the host, Ollama is at localhost.
# When RunLedger's Gateway (inside Docker) calls Ollama, it must use
# host.docker.internal — see lab_03.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# ── Traffic generator knobs (see traffic_gen.py) ─────────────────────────────
# These let you re-point the SAME agent at any team/workspace and feature without
# editing code — just change .env (or export the var) before a run.
#
#   RUNLEDGER_API_KEY   which team/workspace the traffic lands in (swap = switch team)
#   LAB_FEATURE_TAG     the feature_tag stamped on every run (filter by it in the GUI)
#   LAB_RUNS            how many runs to generate
#   LAB_GATEWAY_ALIAS   if set, calls go THROUGH the gateway alias (exercises routing
#                       policies); if empty, calls go direct to Ollama
#   LAB_SCORE / LAB_OUTCOME   attach quality scores / business outcomes to each run
LAB_FEATURE_TAG = os.getenv("LAB_FEATURE_TAG", "lab-traffic")
LAB_RUNS = int(os.getenv("LAB_RUNS", "25"))
LAB_GATEWAY_ALIAS = os.getenv("LAB_GATEWAY_ALIAS", "").strip()
LAB_SCORE = os.getenv("LAB_SCORE", "true").lower() in ("1", "true", "yes")
LAB_OUTCOME = os.getenv("LAB_OUTCOME", "true").lower() in ("1", "true", "yes")
LAB_BUDGET_CHECK = os.getenv("LAB_BUDGET_CHECK", "false").lower() in ("1", "true", "yes")


def require_key() -> str:
    """Return the workspace API key, or exit with a friendly hint if it's missing."""
    if not RUNLEDGER_API_KEY:
        sys.exit(
            "RUNLEDGER_API_KEY is not set.\n"
            "  1. In the dashboard (http://localhost:3201) open Settings → API Keys → New API Key.\n"
            "  2. Copy the key (shown once) into scripts/scenarios/labs/agents/.env\n"
            "     RUNLEDGER_API_KEY=rl_...\n"
        )
    return RUNLEDGER_API_KEY


def banner(title: str) -> None:
    """Print a labelled banner so it's obvious which lab is running and where its data lands."""
    print("\n" + "═" * 68)
    print(f"  {title}")
    print("═" * 68)
    print(f"  RunLedger : {RUNLEDGER_BASE_URL}")
    print(f"  Ollama    : {OLLAMA_BASE_URL}  (model: {OLLAMA_MODEL})")
    key = RUNLEDGER_API_KEY
    print(f"  API key   : {(key[:14] + '…') if key else '(not set)'}")
    print("─" * 68)


def dashboard_url() -> str:
    """Best-effort dashboard URL derived from the API base URL (8201 → 3201)."""
    return RUNLEDGER_BASE_URL.replace("8201", "3201").replace("8000", "3000")
