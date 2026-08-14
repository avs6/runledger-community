# Part 13 - Billing And Reconciliation

This lab exercises the Bundle B billing workflow end to end from the operator
point of view.

## Goal

Validate that Billing now works as a real operations surface rather than a
simple list/export page.

You will:

1. create a billing period
2. inspect the Billing page summary
3. open the period detail page
4. add and edit adjustments
5. review reconciliation and breakdown
6. export signed evidence
7. review shared-cost policy management

## Prerequisites

- RunLedger stack is up
- an org, workspace, and API key already exist
- you have an org admin or workspace admin session

## Steps

### 1. Open Billing

Navigate to `/billing`.

Verify:

- the page shows `Billing Periods`, `Summary`, and `Shared Costs`
- summary cards show recent cost, total calls, and billable share

### 2. Create a period

Use `New period`.

Create a period for the current month.

Verify:

- the new row appears in the period list
- the row shows status `open`
- the detail link opens `/billing/{period_id}`

### 3. Inspect period detail

Open the new period.

Verify:

- the detail page shows tabs for `Summary`, `Reconciliation`, `Breakdown`,
  `Adjustments`, and `Exports`
- the summary tab shows gross cost, net cost, status, and cross-feature links

### 4. Add adjustments

Open the `Adjustments` tab.

Create:

- a `credit`
- a `surcharge`

Verify:

- both rows appear in the table
- totals update for credits, surcharges, and net adjustment
- edit works for at least one row
- delete works for at least one row

### 5. Review reconciliation and breakdown

Open the `Reconciliation` tab.

Verify:

- provider-calls sum and usage-daily sum render
- issues and warnings render even if empty

Open the `Breakdown` tab.

Verify:

- application group rows render
- user rows expand and collapse
- adjustments included in net cost are visible below the table

### 6. Export finance evidence

Open the `Exports` tab.

Run:

- `Export CSV`
- `Export signed JSON`

Verify:

- both downloads succeed
- signed JSON contains rows and a signature

### 7. Review shared-cost policies

Return to `/billing?tab=shared-costs`.

Verify:

- create policy works
- edit policy works
- preview allocation works
- delete policy works

## Optional API checks

You can also verify directly with curl:

```bash
curl -s "$RUNLEDGER_BASE_URL/billing/periods/$PERIOD_ID/reconciliation" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq

curl -s "$RUNLEDGER_BASE_URL/billing/periods/$PERIOD_ID/adjustments" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq

curl -s "$RUNLEDGER_BASE_URL/billing/shared-cost-policies" \
  -H "Authorization: Bearer $RUNLEDGER_API_KEY" | jq
```

## Expected Outcome

Billing should now feel like a true accounting-operations surface:

- periods are manageable
- reconciliation is visible
- adjustments are operator-usable
- shared-cost policy management exists in the product
- exports provide finance-ready evidence
