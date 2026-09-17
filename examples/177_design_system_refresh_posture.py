"""Inspect the design system refresh posture for a workspace.

Shows token architecture, dark mode coverage, component coverage,
scope visual language, density modes, and status semantics.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/design-system-refresh-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Design System Refresh Posture ===\n")

ts = d["token_system"]
print(f"CSS variables:      {ts['css_variables']}")
print(f"Root tokens:        {ts['root_tokens']}")
print(f"Color scales:       {len(ts['color_scales'])} ({', '.join(ts['color_scales'][:6])}...)")
print(f"Border radius:      {ts['border_radius']}")
print(f"Spacing scale:      {ts['spacing_scale']}")

dm = d["dark_mode"]
print(f"\nDark mode:")
print(f"  Strategy:         {dm['strategy']}")
print(f"  Coverage:         {dm['coverage']}")
print(f"  Token override:   {dm['token_override']}")

cc = d["component_coverage"]
print(f"\nComponent coverage:")
print(f"  Posture cards:    {cc['posture_cards']}")
print(f"  Data tables:      {cc['data_tables']}")
print(f"  Themed sections:  {len(cc['themed_sections'])}")
for section in cc["themed_sections"]:
    print(f"    • {section}")

sv = d["scope_visual_language"]
print(f"\nScope visual language:")
print(f"  Workspace color:  {sv['workspace_color']}")
print(f"  Access group:     {sv['access_group_color']} ({sv['total_access_groups']} groups)")
print(f"  API key:          {sv['api_key_color']} ({sv['total_api_keys']} keys)")

dd = d["density_modes"]
print(f"\nDensity modes:")
for mode, spec in dd.items():
    print(f"  {mode:16s} {spec}")

ss = d["status_semantics"]
print(f"\nStatus semantics:")
for category, values in ss.items():
    print(f"  {category}: {', '.join(values)}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (30d):    {oc['requests_30d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
