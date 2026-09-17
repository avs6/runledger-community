"""Inspect the help hub posture for a workspace.

Shows contextual help status, content coverage across feature areas,
section-level help topics, platform readiness, and observe metrics.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/help-hub-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Help Hub Posture ===\n")

hs = d["hub_status"]
print(f"Enabled:            {hs['enabled']}")
print(f"Version:            {hs['version']}")
print(f"Contextual help:    {hs['contextual_help']}")
print(f"Sections:           {hs['total_sections']} ({', '.join(hs['sections'])})")

cc = d["content_coverage"]
print(f"\nContent coverage:")
for guide, covered in cc.items():
    status = "covered" if covered else "missing"
    print(f"  {guide:24s} {status}")

cl = d["contextual_links"]
print(f"\nContextual links:")
for section, info in cl.items():
    print(f"  {info['label']}:")
    print(f"    Pages:  {', '.join(info['pages'][:5])}")
    print(f"    Topics: {', '.join(info['help_topics'][:4])}")

pr = d["platform_readiness"]
print(f"\nPlatform readiness:")
print(f"  API explorer:     {pr['api_explorer']}")
print(f"  Swagger UI:       {pr['swagger_ui']}")
print(f"  Scalar reference: {pr['scalar_reference']}")
print(f"  Pipeline studio:  {pr['pipeline_studio']}")
print(f"  Live pipeline:    {pr['live_pipeline']}")
print(f"  SDK languages:    {', '.join(pr['sdk_languages'])}")
print(f"  API keys:         {pr['api_keys']}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (30d):    {oc['requests_30d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
