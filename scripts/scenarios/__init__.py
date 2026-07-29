"""
Scenario registry.

Each ``NN_*.py`` module in this package defines a self-contained simulation scenario:

    NAME = "saas-support"
    DESCRIPTION = "A SaaS support-bot org …"
    def run(sim):    # sim is a scenarios._base.Sim
        ws = sim.workspace("Acme SaaS", "Support Bot")
        ...

`discover()` returns the modules in filename order so the driver can run them all.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def discover() -> list[ModuleType]:
    """Return all scenario modules (NN_*.py) in sorted filename order."""
    mods: list[ModuleType] = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        if hasattr(mod, "run") and hasattr(mod, "NAME"):
            mods.append(mod)
    return mods
