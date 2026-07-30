# Devin Configuration Notes

Devin integration should usually be a wrapper rather than inline model routing.

## Recommended Flow

- A local or hosted wrapper receives the task request.
- The wrapper checks RunLedger budget and policy.
- The wrapper starts a RunLedger run.
- The wrapper creates a Devin session.
- The wrapper records Devin session ID, repo, branch, and task metadata.
- On completion, the wrapper records outcome and imported/estimated usage.

## Generate Repo Instructions

```bash
python skills/shared/scripts/install_agent_instructions.py --client devin --repo /path/to/repo
```

## Validate RunLedger

```bash
python skills/shared/scripts/runledger_smoke.py --client devin --task "devin setup smoke"
```
