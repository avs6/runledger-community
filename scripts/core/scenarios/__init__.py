"""
Scenario registry.

Each scenario is a Python module under this package that defines a self-contained
simulation using local Ollama models:

    NAME = "coding-assistant"
    DESCRIPTION = "Local coding assistant on Ollama …"
    def run(sim):    # sim is a scenarios._base.Sim
        ws = sim.workspace("My Org", "My Workspace")
        ...

Add new scenarios under ``scenarios/ollama/``. ``discover()`` walks the tree
recursively (sorted by dotted path).
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


# Subpackages that are NOT auto-run scenarios (safety net — labs/ was moved to
# scripts/labs/ but the guard stays in case anything is added here by mistake).
_SKIP_PACKAGES = {"labs"}


def discover(category: str | None = "ollama") -> list[ModuleType]:
    """Return scenario modules, scoped to a category folder.

    The default is ``"ollama"`` (local Ollama traffic). Pass ``"all"`` or ``None``
    to run every bundled scenario.
    """
    mods: list[ModuleType] = []
    category_filter = None if category in (None, "", "all") else category
    for info in sorted(
        pkgutil.walk_packages(__path__, prefix=f"{__name__}."), key=lambda m: m.name
    ):
        parts = info.name.split(".")
        short = parts[-1]
        if info.ispkg or short.startswith("_"):
            continue
        # Skip anything living under a non-scenario subpackage (e.g. scenarios.labs.*).
        if _SKIP_PACKAGES.intersection(parts):
            continue
        if category_filter and category_filter not in parts:
            continue
        mod = importlib.import_module(info.name)
        if hasattr(mod, "run") and hasattr(mod, "NAME"):
            mods.append(mod)
    return mods
