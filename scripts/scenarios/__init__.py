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


def discover() -> list[ModuleType]:
    """Return every scenario module under this package (recursively), sorted by path."""
    mods: list[ModuleType] = []
    for info in sorted(
        pkgutil.walk_packages(__path__, prefix=f"{__name__}."), key=lambda m: m.name
    ):
        short = info.name.rsplit(".", 1)[-1]
        if info.ispkg or short.startswith("_"):
            continue
        mod = importlib.import_module(info.name)
        if hasattr(mod, "run") and hasattr(mod, "NAME"):
            mods.append(mod)
    return mods
