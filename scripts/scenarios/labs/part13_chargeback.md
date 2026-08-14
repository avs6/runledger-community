# Part 13 - Chargeback

This lab exercises the Bundle C chargeback workflow end to end from the operator
point of view.

## Goal

Validate that Chargeback now works as a real allocation surface rather than a
placeholder report.

You will:

1. create and edit chargeback rules
2. review the summary posture for a month
3. inspect allocation rows by workflow tag and workspace
4. export finance-ready evidence

## Prerequisites

- RunLedger stack is up
- an org, workspace, and API key already exist
- you have an org admin or workspace admin session
- the workspace has some recent runs/provider calls

## Steps

### 1. Open Chargeback

Navigate to `/chargeback`.

Verify:

- the page shows `Overview`, `Rules`, `Allocations`, and `Exports`
- period and dimension selectors are visible

### 2. Create a rule

Open the `Rules` tab and create a rule:

- allocation type: `Direct allocation`
- dimension: `Workflow tag`
- weight: `1.0`

Verify:

- the rule appears in the table
- status shows `active` or `pending_approval`

### 3. Edit and delete lifecycle

Edit the rule and change:

- allocation type to `Showback only` or `Shared weight`
- dimension to `Workspace` or `Application`

Verify:

- the row updates in place
- delete also works for the same rule lifecycle

### 4. Review overview posture

Open the `Overview` tab.

Verify:

- total cost renders
- budget-covered cost renders
- unallocated cost renders
- top allocation rows render for the selected dimension

### 5. Inspect allocation rows

Open the `Allocations` tab.

Check at least two dimensions:

- `Workflow tag`
- `Workspace`

Verify:

- rows show cost, percent of total, runs, and calls
- allocation status shows `allocated` or `unallocated`
- coverage status reflects whether a matching budget exists

### 6. Export finance evidence

Open the `Exports` tab.

Run:

- `Export CSV`
- `Export JSON`

Verify:

- both downloads succeed
- CSV contains dimension rows
- JSON contains `period`, `dimension`, and `breakdown`

## Optional API checks

```bash
curl -s "$RUNLEDGER_BASE_URL/billing/chargeback-rules" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq

curl -s "$RUNLEDGER_BASE_URL/billing/chargeback-report?period=2026-08&dimension=feature_tag" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq

curl -s "$RUNLEDGER_BASE_URL/billing/chargeback-report/export?period=2026-08&dimension=workspace&format=json" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq
```

## Expected outcome

Chargeback should now feel like a real workspace FinOps surface:

- rules are manageable
- allocations are visible by modern ownership dimensions
- unallocated spend is explicit
- finance exports are available without leaving the product
