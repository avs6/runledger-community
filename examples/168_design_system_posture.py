"""Inspect the design system posture for a workspace.

Shows token system inventory, dark mode configuration, scope visual language,
layout shells, density modes, and status semantics.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/design-system-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Design System Posture ===\n")

ts = d["token_system"]
print(f"Token categories: {', '.join(ts['categories'])}")
print(f"Color tokens:     {ts['color_tokens']}")
print(f"Spacing scale:    {ts['spacing_scale']}")
print(f"Typography:       {len(ts['typography_stacks'])} stacks")
for s in ts["typography_stacks"]:
    print(f"  - {s}")
print(f"Elevation levels: {ts['elevation_levels']}")
print(f"Default radius:   {ts['radius_default']}")
print(f"Chart palette:    {ts['chart_palette_size']} colors")

dm = d["dark_mode"]
print(f"\nDark mode:")
print(f"  Strategy:        {dm['strategy']}")
print(f"  Palette:         {dm['palette']}")
print(f"  Legacy overrides: {dm['legacy_overrides']}")
print(f"  Contrast target: {dm['contrast_ratio_target']}")

sv = d["scope_visual_language"]
print(f"\nScope visual language:")
for level in sv["scope_levels"]:
    color = sv["scope_colors"].get(level, "?")
    print(f"  {level:16s} → {color}")
print(f"  Access groups:   {sv['access_groups']}")
print(f"  API keys:        {sv['api_keys']}")

ls = d["layout_shells"]
print(f"\nLayout shells: {', '.join(ls['shells'])}")
print(f"  Sidebar:         {ls['sidebar_pattern']}")
print(f"  Max width:       {ls['content_max_width']}")
print(f"  Breakpoints:     {len(ls['responsive_breakpoints'])}")

dn = d["density_modes"]
print(f"\nDensity modes: {', '.join(dn['available'])}")
print(f"  Default row:     {dn['default_row_height']}")
print(f"  Compact row:     {dn['compact_row_height']}")
print(f"  Compact surfaces: {', '.join(dn['compact_surfaces'])}")

ss = d["status_semantics"]
print(f"\nOperational states:")
for state, color in ss["operational_states"].items():
    print(f"  {state:10s} → {color}")

print(f"\nSeverity levels:")
for level in ss["severity_levels"]:
    color = ss["severity_colors"].get(level, "?")
    print(f"  {level:10s} → {color}")

print(f"\nRuntime states:")
for state, color in ss["runtime_states"].items():
    print(f"  {state:12s} → {color}")
