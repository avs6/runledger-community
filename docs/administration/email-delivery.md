# Email Delivery And Reporting

RunLedger includes platform-admin email controls for:

- SMTP delivery validation
- scheduled analytics report preferences
- report template selection
- test-report delivery
- recent delivery history

This document covers the current product surface and the operator validation path.

## What ships today

The Settings page includes:

- notification preference toggles
- scheduled analytics report cadence
- timezone and recipient controls
- report template selection:
  - `executive`
  - `summary`
  - `detailed`
- `Send Test Email`
- `Send Test Report To Me`
- recent email delivery history

These flows are backed by the email preferences API, email log API, and background report delivery worker.

## Operator prerequisites

Before testing email in a real environment:

1. set `EMAIL_ENABLED=true`
2. configure SMTP credentials
3. set `EMAIL_REPORTS_ENABLED=true` if you want scheduled analytics reports

If SMTP credentials are missing, the dashboard will show that delivery is blocked even when email is enabled.

## Validation flow

Use this order:

1. open `Settings -> Email Delivery`
2. confirm the status banner reflects your current env configuration
3. click `Send Test Email`
4. click `Send Test Report To Me`
5. confirm both entries appear in delivery history
6. save the desired report cadence, recipients, and template

This is enough to validate:

- SMTP connectivity
- background email send path
- analytics report templating
- delivery history recording

## Report templates

RunLedger supports three report templates:

- `executive` for a concise high-level spend snapshot
- `summary` for a balanced operator and finance view
- `detailed` for fuller operational review

Use the template selector in Settings before sending a test report.

## Notes

- Environment-specific SMTP deliverability still needs to be tested by the operator in the target environment.
- The product-side email settings and test flows are considered shipped; remaining work is around local Mailpit support, retry policies, and broader delivery infrastructure hardening.

## Related docs

- [Backup and Restore](../backup-restore.md)
- [Demo runbook](../demo-runbook.md)
