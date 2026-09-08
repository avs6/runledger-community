# Sample evaluators — create these on the **Evaluation** page

An **evaluator** scores runs automatically. Two types:

- **`rule`** — deterministic checks (contains / regex / comparisons). Free, instant.
- **`llm_judge`** — an LLM grades the response against natural-language criteria.

Create them in the GUI (Evaluation → Evaluators → New), paste the config, then run the
evaluator over recent runs (or wire it into an Experiment).

---

## Evaluator 1 — `refund-policy-check` (type: `rule`)

Passes when the answer mentions the correct refund window and doesn't hallucinate a number.

```json
{
  "rules": [
    { "field": "output", "op": "contains", "value": "5 business days", "score_if_pass": 1.0, "score_if_fail": 0.0 },
    { "field": "output", "op": "regex", "value": "(?i)\\b(10|30|60)\\s*days\\b", "score_if_pass": 0.0, "score_if_fail": 1.0 }
  ],
  "aggregation": "avg"
}
```

- Fields you can target: `output`, `input`, `run_id`.
- Ops: `eq, neq, gt, gte, lt, lte, contains, regex`.
- Aggregation: `avg | min | max | first_fail`.

---

## Evaluator 2 — `helpfulness-judge` (type: `llm_judge`)

Uses your **local Ollama** as the judge — no cloud key needed.

```json
{
  "model": "llama3.2",
  "base_url": "http://host.docker.internal:11434/v1",
  "api_key": "ollama",
  "criteria": "Rate from 0 to 1 how helpful, accurate, and concise the agent's answer is for a customer-support context. 1 = fully resolves the question; 0 = unhelpful or wrong.",
  "min_score": 0.0,
  "max_score": 1.0
}
```

> The judge sees `{{input}}` and `{{output}}` of each run. Base URL must be
> `host.docker.internal` (the evaluator runs inside Docker).

---

## How to see them work

1. Generate some traffic into the team's workspace:
   ```bash
   LAB_FEATURE_TAG=support-chat LAB_RUNS=25 python traffic_gen.py
   ```
2. On the Evaluation page, **Run** each evaluator over recent runs.
3. Watch the scores land (Evaluation → Scores), and the **cost-quality** /
   **best-value model** analytics fill in. Re-run after changing a prompt to see
   whether quality moved.
