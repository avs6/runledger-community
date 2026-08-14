# Part 13 - Ledger Closure

This lab exercises the Bundle D compliance-close workflow from the operator
point of view.

## Goal

Validate that compliance closure now lives under Platform Settings and links
Billing, Chargeback, Ledger verification, backup evidence, and audit activity
into one workflow.

## Prerequisites

- RunLedger stack is up
- a platform-admin session exists
- at least one workspace has recent traffic

## Steps

### 1. Open Platform Settings

Navigate to `/settings?tab=compliance`.

Verify:

- the page shows readiness cards
- evidence chain tiles are visible
- ledger snapshots are listed below the summary

### 2. Review closure readiness

Verify:

- `Closure readiness` renders
- `Latest closed period` renders when a billing period has been closed
- `Ledger verification` shows current snapshot posture
- `Chargeback evidence` shows allocation posture or clearly reports it as missing
- `Audit activity` shows recent event count

### 3. Generate and verify a snapshot

Use `Generate Snapshot`.

Then use `Verify` on the newest snapshot.

Verify:

- snapshot row appears or refreshes
- verification returns `ok` or clearly surfaces a non-`ok` state

### 4. Follow the evidence chain

Use the links to:

- `/billing`
- `/chargeback`
- `/audit`

Verify:

- Billing can be used to inspect upstream period-close evidence
- Chargeback can be used to inspect ownership allocation
- Audit Log can be used to inspect downstream mutation evidence

### 5. Review backup evidence

Open `/settings?tab=backup`.

Verify:

- backup status and snapshot inventory exist
- backup evidence is visible as part of the broader closure story

## Optional API checks

```bash
curl -s "$RUNLEDGER_BASE_URL/ledger/closure-summary" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq

curl -s -X POST "$RUNLEDGER_BASE_URL/ledger/snapshots/generate" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq

curl -s "$RUNLEDGER_BASE_URL/ledger/snapshots" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq
```

## Expected outcome

Compliance closure should now feel cohesive:

- `/ledger` is not competing with Platform Settings
- the close workflow is visible in one place
- ledger verification is linked to billing, chargeback, backup, and audit evidence
