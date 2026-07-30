# RunLedger Connect Devin

Use this skill when a user wants Devin sessions to be tracked by RunLedger.

## What This Skill Does

- Adds `RUNLEDGER_AGENT.md` to the target repo.
- Defines the Devin bridge pattern: create RunLedger run, start Devin session, poll/webhook completion, record outcome.
- Validates RunLedger ingest with the shared smoke test.

## Steps

```bash
python skills/shared/scripts/install_agent_instructions.py --client devin --repo .
python skills/shared/scripts/runledger_smoke.py --client devin --task "devin connector validation"
```

## Bridge Pattern

1. Check RunLedger budget before creating a Devin session.
2. Create a RunLedger run with repo, branch, task, and requester metadata.
3. Create the Devin session.
4. Store Devin session ID in RunLedger run metadata.
5. Poll or receive webhook completion.
6. Record final outcome, PR URL, branch, elapsed time, and estimated/imported model usage.

## Success Criteria

- `RUNLEDGER_AGENT.md` exists.
- A wrapper can create a RunLedger run before a Devin session.
- Completion updates the RunLedger outcome.
