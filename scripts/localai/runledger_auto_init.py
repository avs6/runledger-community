"""RunLedger Auto-Initialization Hook for Python Subagents.

When set as PYTHONSTARTUP environment variable, any Python process spawned by
Claude Desktop or background agents automatically initializes RunLedger telemetry.
"""

import os
import sys

# Auto-detect RunLedger Environment
runledger_base_url = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8201")
runledger_api_key = os.environ.get("RUNLEDGER_API_KEY", "rl_test_4-yqcUFLlwV380G5WUWDCRrOJkbwHi67-aHv3sGDZbI")

if runledger_api_key:
    os.environ["RUNLEDGER_BASE_URL"] = runledger_base_url
    os.environ["RUNLEDGER_API_KEY"] = runledger_api_key
    # Instruct OpenAI-compatible clients to route inline through gateway
    if "OPENAI_BASE_URL" not in os.environ:
        os.environ["OPENAI_BASE_URL"] = f"{runledger_base_url}/gateway"
