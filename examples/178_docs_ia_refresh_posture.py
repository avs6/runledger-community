"""Inspect the docs IA refresh posture for a workspace.

Shows documentation structure, content inventory, naming audit,
repo hygiene, and observe metrics.
"""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
KEY = os.environ.get("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"} if KEY else {}

r = httpx.get(f"{BASE}/analytics/docs-ia-refresh-posture", headers=HEADERS, timeout=10)
r.raise_for_status()
d = r.json()

print("=== Docs IA Refresh Posture ===\n")

ds = d["docs_structure"]
print(f"Hierarchy:          {ds['hierarchy']}")
print(f"Total sections:     {ds['total_sections']}")
print(f"Sections:           {', '.join(ds['sections'])}")
print(f"Landing map:        {ds['landing_map']}")
print(f"Progressive:        {ds['progressive_disclosure']}")
print(f"Onboarding guide:   {ds['onboarding_guide']}")
print(f"Operator guide:     {ds['operator_guide']}")
print(f"Architecture guide: {ds['architecture_guide']}")

ci = d["content_inventory"]
print(f"\nContent inventory:")
print(f"  API reference:    {ci['api_reference']}")
print(f"  SDK guides:       {', '.join(ci['sdk_guides'])}")
print(f"  Pipeline docs:    {ci['pipeline_docs']}")
print(f"  Governance docs:  {ci['governance_docs']}")
print(f"  FinOps docs:      {ci['finops_docs']}")
print(f"  MCP docs:         {ci['mcp_docs']}")
print(f"  Guardrails docs:  {ci['guardrails_docs']}")
print(f"  Evaluation docs:  {ci['evaluation_docs']}")
print(f"  Help Hub linked:  {ci['help_hub_linked']}")
print(f"  API Explorer:     {ci['api_explorer_linked']}")

na = d["naming_audit"]
print(f"\nNaming audit:")
print(f"  Product centered: {na['product_centered']}")
print(f"  Stale refs clean: {na['stale_phase_refs_removed']}")
print(f"  Migration clean:  {na['migration_language_cleaned']}")
print(f"  Consistent terms: {na['consistent_terminology']}")

rh = d["repo_hygiene"]
print(f"\nRepo hygiene:")
print(f"  Examples aligned: {rh['example_scripts_aligned']}")
print(f"  Postman aligned:  {rh['postman_collection_aligned']}")
print(f"  Mermaid diagrams: {rh['mermaid_diagrams']}")
print(f"  Blueprint cross:  {rh['blueprint_crosswalks']}")

oc = d["observe_context"]
print(f"\nObserve context:")
print(f"  Requests (30d):    {oc['requests_30d']}")
print(f"  Audit events (30d): {oc['audit_events_30d']}")
