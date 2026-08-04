# Part 3 · Quality & Experiments

*Prerequisite: Part 1 done. Some runs from Part 2 help but aren't required.*

This part is about **quality**: managing prompts, scoring runs, and choosing models with
evidence. First, the distinction that trips everyone up.

## Evaluation vs Experiments vs Replay

| | **Evaluation** | **Experiments** | **Replay** |
|---|---|---|---|
| Answers | "How good is my **live** agent?" | "Which model/prompt should I **ship**?" | "What would a change have **cost**?" |
| Works on | your recorded production **runs** | a fixed **dataset** × a **prompt version** × several **models** | a saved set of past **run IDs** + a **config delta** |
| Calls models? | No — scores existing runs | **Yes** — runs the dataset across models | No — projects cost over history |
| Output | quality scores on real traffic | avg score & cost per model → a winner | projected cost delta |
| GUI page | **Evaluation** | **Experiments** | **Replay** |

Rule of thumb: **Evaluation grades reality, Experiments test hypotheses before shipping,
Replay estimates the cost of a what-if.**

---

## 3.1 · Prompts

**Goal:** version your prompts and promote them like code.

1. Open **Prompts**. Create the two prompts from [`samples/prompts.md`](./samples/prompts.md)
   (`support-agent` with two staging versions, `ticket-summarizer`).
2. **Promote** a `support-agent` version from `staging` → `production`.
3. Generate traffic so runs link to the production prompt:
   ```bash
   LAB_FEATURE_TAG=support-chat LAB_RUNS=30 python traffic_gen.py
   ```
4. On the prompt's detail page, watch **per-version metrics** fill in (run count, avg cost,
   avg score).

🔎 Prompts become measurable artifacts — you can see if v2 actually beat v1 in production.

---

## 3.2 · Evaluation (grade live runs)

**Goal:** attach quality scores to real traffic automatically.

1. Open **Evaluation → Evaluators**. Create the two from
   [`samples/evaluators.md`](./samples/evaluators.md): `refund-policy-check` (rule) and
   `helpfulness-judge` (llm_judge on local Ollama).
2. **Run** each evaluator over recent runs.
3. See scores under **Evaluation → Scores**, and the **cost-quality** / **best-value model**
   charts populate.

🔎 This scores what already happened. It doesn't call new models — it judges your runs.

---

## 3.3 · Datasets

**Goal:** build a fixed test set with known-good answers.

Open **Datasets → Import** and load [`samples/dataset_support_faq.json`](./samples/dataset_support_faq.json)
(10 support questions with reference answers). This is the *controlled* input an Experiment
will run against — unlike Evaluation, it's not your live traffic.

🔎 A dataset = inputs + `expected_output`. It's your regression suite for agents.

---

## 3.4 · Experiments (choose a model before shipping)

**Goal:** run one prompt over the dataset across several models and compare.

1. Open **Experiments → New**. Configure:
   - **Dataset:** `Support FAQ v1`
   - **Prompt:** `support-agent`, version = your production version
   - **Evaluators:** `helpfulness-judge` (and `refund-policy-check`)
   - **Models:** add two to compare, e.g.
     `llama3.2` (ollama) labelled *cheap*, and `qwen2.5-coder:14b` (ollama) labelled *bigger*
2. **Run** the experiment. It executes the prompt over all 10 items for each model and scores
   the outputs. Re-run it a few times if you want to see variance between runs.
3. Open **results**: `avg_score` and cost **per model**. The cheaper model that still clears
   your quality bar is the one to ship.

🔎 This is the only one of the three that actually **calls the models** — it's an offline
bake-off. No production traffic is touched.

---

## 3.5 · Replay (cost of a what-if)

**Goal:** estimate what a config change would have cost on real past traffic.

1. Open **Replay**. Create a **dataset of run IDs** — a saved slice of past runs (e.g. your
   last support-chat runs).
2. Create a **Replay experiment** with a **config delta** — e.g. "what if these had run on
   `llama3.2` instead of the current model?"
3. **Run** it → RunLedger projects the cost. No models are called; it's arithmetic over the
   recorded token counts and the pricing catalog.

4. On the results table, click **Recommend Route** on a config row to create a route
   recommendation. This feeds back into the Gateway routing decisions.

🔎 Replay answers cost questions retrospectively. Pair it with Experiments (which proves the
cheaper model is *good enough*) to justify a switch: *"good enough" (Experiment) **and**
"X% cheaper across last month's traffic" (Replay).* The **Recommend Route** button closes the
loop — evidence-based model switching from replay to production.

---

✅ **End of Part 3.** You can version prompts, auto-grade live runs, bake off models on a
dataset, project the cost of a change, and recommend routes from evidence. Next:
**[Part 4 · Optimization layer](./part4_optimization.md)**.
