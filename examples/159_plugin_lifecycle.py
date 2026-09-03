"""Plugin lifecycle: create, list, get detail, update, view executions, and deactivate."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

r = httpx.post(
    f"{BASE}/plugins",
    headers=HEADERS,
    json={
        "name": "example-webhook-relay",
        "description": "Forwards events to an external webhook",
        "plugin_type": "webhook",
        "hooks": ["on_run_complete", "on_alert_fired"],
        "config": {"url": "https://example.com/hook", "secret": "demo"},
    },
)
r.raise_for_status()
plugin = r.json()
pid = plugin["id"]
print(f"Created plugin: {pid} ({plugin['name']})")

r = httpx.get(f"{BASE}/plugins", headers=HEADERS)
r.raise_for_status()
plugins = r.json()
print(f"Total plugins: {plugins['total']}")

r = httpx.get(f"{BASE}/plugins/{pid}", headers=HEADERS)
r.raise_for_status()
detail = r.json()
print(f"Plugin type: {detail['plugin_type']}, active: {detail['is_active']}")

r = httpx.put(
    f"{BASE}/plugins/{pid}",
    headers=HEADERS,
    json={"description": "Updated description", "priority": 10},
)
r.raise_for_status()
print(f"Updated plugin priority to {r.json()['priority']}")

r = httpx.get(f"{BASE}/plugins/{pid}/executions", headers=HEADERS)
r.raise_for_status()
execs = r.json()
print(f"Execution log entries: {execs['total']}")

r = httpx.delete(f"{BASE}/plugins/{pid}", headers=HEADERS)
r.raise_for_status()
print(f"Deactivated plugin: {r.json()['is_active']}")
