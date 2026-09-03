"""Fetch Build & Improve internal posture."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/build-internal-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Playground sessions 30d: {data['playground_context']['sessions_30d']}")
print(f"  Provider calls 30d: {data['playground_context']['provider_calls_30d']}")
print(f"Prompts: {data['prompts_context']['total_prompts']}")
print(f"Workflows: {data['workflows_context']['definitions']} definitions, {data['workflows_context']['runs_30d']} runs 30d")
print(f"Evaluation: {data['evaluation_context']['datasets']} datasets, {data['evaluation_context']['experiments']} experiments")
print(f"Replay: {data['replay_context']['datasets']} datasets, {data['replay_context']['experiments']} experiments")
print(f"Optimization: {data['optimization_context']['hub_models']} hub models, ${data['optimization_context']['spend_30d']:.2f} spend 30d")
print(f"Scorecards: {data['scorecards_context']['hub_models']} hub models, {data['scorecards_context']['score_events_30d']} score events 30d")
