"""
Smoke-test the core access-management foundation end to end.

Covers:
  - users
  - workspaces
  - access groups
  - API keys (create, update, rotate, revoke)

Required:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
"""

from __future__ import annotations

import os
import runpy
from pathlib import Path


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "examples" / "41_access_foundation.py"
    os.chdir(repo_root)
    runpy.run_path(str(script_path), run_name="__main__")
