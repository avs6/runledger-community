"""
Scenario registry.

Each scenario is a Python module — anywhere under this package, including in
**category subfolders** — that defines a self-contained simulation:

    NAME = "saas-support"
    DESCRIPTION = "A SaaS support-bot org …"
    def run(sim):    # sim is a scenarios._base.Sim
        ws = sim.workspace("Acme SaaS", "Support Bot")
        ...

Organize scenarios however you like — e.g. ``scenarios/ollama/…`` and
``scenarios/hosted/…``. Add a new folder with an ``__init__.py`` and drop scenario
files in; ``discover()`` walks the whole tree recursively (sorted by dotted path).
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


# Subpackages that are NOT auto-run scenarios. ``labs/`` is a manual, hands-on
# workbook whose agent scripts import optional heavy deps (openai, opentelemetry)
# and are meant to be run by hand — never swept up by the simulator.
_SKIP_PACKAGES = {"labs"}


def discover() -> list[ModuleType]:
    """Return every scenario module under this package (recursively), sorted by path."""
    mods: list[ModuleType] = []
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
        mod = importlib.import_module(info.name)
        if hasattr(mod, "run") and hasattr(mod, "NAME"):
            mods.append(mod)
    return mods
