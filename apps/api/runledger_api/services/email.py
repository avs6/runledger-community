"""Email service — sends transactional emails via Brevo SMTP."""

from __future__ import annotations

import asyncio
import smtplib
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from runledger_api.core.config import settings

log = structlog.get_logger()


def _send_smtp(to_email: str, subject: str, html: str, text: str) -> None:
    """Synchronous SMTP send — run via asyncio.to_thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"RunLedger <{settings.smtp_from}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.smtp_from, to_email, msg.as_string())


async def send_email(to_email: str, subject: str, html: str, text: str) -> None:
    """Send an email async. Silently logs on failure so signup never breaks."""
    if not settings.smtp_user or not settings.smtp_password:
        log.warning("email_skipped_no_smtp_config", to=to_email, subject=subject)
        return
    try:
        await asyncio.to_thread(_send_smtp, to_email, subject, html, text)
        log.info("email_sent", to=to_email, subject=subject)
    except Exception:
        log.exception("email_send_failed", to=to_email, subject=subject)


async def send_welcome_email(
    to_email: str,
    full_name: str,
    password: str,
    api_key: str,
    verify_url: str,
) -> None:
    name = full_name or to_email
    subject = "Welcome to RunLedger — verify your email"

    text = textwrap.dedent(f"""\
        Hi {name},

        Welcome to RunLedger! Here are your account details:

        Email:    {to_email}
        Password: {password}
        API Key:  {api_key}

        Please verify your email address to activate your account:
        {verify_url}

        This link expires in 24 hours.

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#0f766e,#0891b2);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#99f6e4;">FinOps Control Plane</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Welcome, {name}!</p>
          <p style="margin:0 0 28px;font-size:14px;color:#94a3b8;line-height:1.6;">Your RunLedger account is ready. Here are your credentials — save them somewhere safe.</p>

          <!-- Credentials table -->
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr>
              <td style="padding:14px 20px;border-bottom:1px solid #334155;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Email</p>
                <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;font-family:monospace;">{to_email}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:14px 20px;border-bottom:1px solid #334155;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Password</p>
                <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;font-family:monospace;">{password}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:14px 20px;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">API Key</p>
                <p style="margin:4px 0 0;font-size:13px;color:#2dd4bf;font-family:monospace;word-break:break-all;">{api_key}</p>
              </td>
            </tr>
          </table>

          <!-- Verify button -->
          <p style="margin:0 0 16px;font-size:14px;color:#94a3b8;">Click the button below to verify your email and activate your account:</p>
          <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
            <tr><td style="background:linear-gradient(135deg,#0d9488,#0891b2);border-radius:8px;">
              <a href="{verify_url}" style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:600;color:#fff;text-decoration:none;">Verify Email Address</a>
            </td></tr>
          </table>

          <p style="margin:0;font-size:12px;color:#475569;">This link expires in 24 hours. If you didn't create this account, you can ignore this email.</p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text)


async def send_alert_fired_email(
    to_email: str,
    full_name: str | None,
    rule_name: str,
    metric: str,
    operator: str,
    threshold: str,
    value: str,
    workspace_name: str,
) -> None:
    """Notify a user that an alert rule has fired."""
    name = full_name or to_email
    operator_label = ">" if operator == "gt" else "<"
    subject = f"RunLedger Alert: {rule_name} fired"

    text = textwrap.dedent(f"""\
        Hi {name},

        An alert rule has fired in your workspace "{workspace_name}".

        Rule:      {rule_name}
        Metric:    {metric}
        Value:     {value} {operator_label} {threshold} (threshold)

        Log in to RunLedger to investigate.

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#b45309,#dc2626);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#fde68a;">Alert Fired</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Alert Rule Triggered</p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Rule</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{rule_name}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Metric</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;font-family:monospace;">{metric}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Value vs Threshold</p>
              <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:#f87171;font-family:monospace;">{value} {operator_label} {threshold}</p>
            </td></tr>
          </table>
          <p style="margin:0;font-size:13px;color:#64748b;">Log in to RunLedger to investigate and resolve this alert.</p>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text)


async def send_approval_request_email(
    to_email: str,
    full_name: str | None,
    request_type: str,
    reason: str | None,
    requester: str | None,
    workspace_name: str,
    approval_url: str,
) -> None:
    """Notify an admin that a new approval request needs their attention."""
    name = full_name or to_email
    requester_label = requester or "API key (no user)"
    reason_html = (
        f'<tr><td style="padding:14px 20px;">'
        f'<p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Reason</p>'
        f'<p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{reason}</p>'
        f"</td></tr>"
        if reason
        else ""
    )
    reason_text = f"\nReason:    {reason}" if reason else ""
    subject = f"RunLedger: Approval requested — {request_type}"

    text = textwrap.dedent(f"""\
        Hi {name},

        A new approval request has been submitted in workspace "{workspace_name}".

        Type:      {request_type}
        Requested: {requester_label}{reason_text}

        Review and approve or deny it here:
        {approval_url}

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#0f766e,#0891b2);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#99f6e4;">Approval Required</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">New Approval Request</p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Request Type</p>
              <p style="margin:4px 0 0;font-size:14px;color:#2dd4bf;font-family:monospace;">{request_type}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Requested By</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{requester_label}</p>
            </td></tr>
            {reason_html}
          </table>
          <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
            <tr><td style="background:linear-gradient(135deg,#0d9488,#0891b2);border-radius:8px;">
              <a href="{approval_url}" style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:600;color:#fff;text-decoration:none;">Review Request</a>
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text)


async def send_approval_decision_email(
    to_email: str,
    request_type: str,
    decision: str,
    decision_note: str | None,
    decided_by: str | None,
    workspace_name: str,
) -> None:
    """Notify the requester of an approval decision (approved or denied)."""
    is_approved = decision == "approved"
    status_color = "#4ade80" if is_approved else "#f87171"
    status_label = "Approved" if is_approved else "Denied"
    note_html = (
        f'<tr><td style="padding:14px 20px;">'
        f'<p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Note</p>'
        f'<p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{decision_note}</p>'
        f"</td></tr>"
        if decision_note
        else ""
    )
    note_text = f"\nNote:      {decision_note}" if decision_note else ""
    decider_label = decided_by or "an administrator"
    subject = f"RunLedger: Approval {status_label} — {request_type}"

    text = textwrap.dedent(f"""\
        Your approval request has been {decision}.

        Type:      {request_type}
        Status:    {status_label}
        Decided by: {decider_label}
        Workspace: {workspace_name}{note_text}

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#0f766e,#0891b2);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#99f6e4;">Approval Decision</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Your request has been <span style="color:{status_color};">{status_label}</span></p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:24px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Request Type</p>
              <p style="margin:4px 0 0;font-size:14px;color:#2dd4bf;font-family:monospace;">{request_type}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Decided By</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{decider_label}</p>
            </td></tr>
            {note_html}
          </table>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text)


async def send_reconciliation_email(
    to_email: str,
    full_name: str | None,
    provider: str,
    period: str,
    matched_pct: float,
    unmatched_count: int,
    delta_amount: str,
    workspace_name: str,
) -> None:
    """Notify workspace admins after invoice reconciliation completes."""
    name = full_name or to_email
    matched_color = "#4ade80" if matched_pct >= 90 else "#f59e0b" if matched_pct >= 70 else "#f87171"
    subject = f"RunLedger: Invoice reconciliation complete — {provider}"

    text = textwrap.dedent(f"""\
        Hi {name},

        Invoice reconciliation has completed for workspace "{workspace_name}".

        Provider:  {provider}
        Period:    {period}
        Matched:   {matched_pct:.1f}%
        Unmatched: {unmatched_count} lines
        Delta:     ${delta_amount}

        Log in to RunLedger to review unmatched and disputed lines.

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#0f766e,#0891b2);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#99f6e4;">Reconciliation Complete</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Invoice Reconciliation Summary</p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Provider</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{provider}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Period</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{period}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Match Rate</p>
              <p style="margin:4px 0 0;font-size:20px;font-weight:700;color:{matched_color};">{matched_pct:.1f}%</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Unmatched Lines</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{unmatched_count}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Delta (Invoice − RunLedger)</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;font-family:monospace;">${delta_amount}</p>
            </td></tr>
          </table>
          <p style="margin:0;font-size:13px;color:#64748b;">Log in to RunLedger to review unmatched and disputed lines.</p>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text)


async def send_analytics_report_email(
    to_email: str,
    full_name: str | None,
    period_label: str,
    rows: list[dict[str, object]],
    total_cost: str,
    workspace_name: str,
) -> None:
    """Send a usage analytics report email."""
    name = full_name or to_email
    subject = f"RunLedger: Analytics Report — {period_label}"

    # Build plain-text table
    lines = [f"{'Date':<12} {'Provider':<16} {'Model':<28} {'Cost (USD)':>12} {'Calls':>8}"]
    lines.append("-" * 80)
    for r in rows[:50]:  # cap at 50 rows in email
        lines.append(
            f"{str(r.get('date','')):<12} {str(r.get('provider','')):<16} "
            f"{str(r.get('model','')):<28} {str(r.get('cost_usd','0')):>12} "
            f"{str(r.get('call_count','0')):>8}"
        )
    if len(rows) > 50:
        lines.append(f"  … and {len(rows) - 50} more rows — log in to export all data.")
    table_text = "\n".join(lines)

    text = textwrap.dedent(f"""\
        Hi {name},

        Here is your analytics report for "{workspace_name}" — {period_label}.

        Total spend: ${total_cost}

{table_text}

        — The RunLedger Team
    """)

    # Build HTML rows
    html_rows = ""
    for i, r in enumerate(rows[:50]):
        bg = "#0f172a" if i % 2 == 0 else "#111827"
        html_rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:8px 12px;color:#e2e8f0;font-size:12px;">{r.get("date","")}</td>'
            f'<td style="padding:8px 12px;color:#e2e8f0;font-size:12px;">{r.get("provider","")}</td>'
            f'<td style="padding:8px 12px;color:#94a3b8;font-size:12px;font-family:monospace;">{r.get("model","")}</td>'
            f'<td style="padding:8px 12px;color:#2dd4bf;font-size:12px;text-align:right;">${r.get("cost_usd","0")}</td>'
            f'<td style="padding:8px 12px;color:#e2e8f0;font-size:12px;text-align:right;">{r.get("call_count","0")}</td>'
            f"</tr>"
        )
    truncation_note = (
        f'<tr><td colspan="5" style="padding:10px 12px;color:#64748b;font-size:12px;">'
        f"… and {len(rows) - 50} more rows — log in to export all data.</td></tr>"
        if len(rows) > 50
        else ""
    )

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="620" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#0f766e,#0891b2);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#99f6e4;">Analytics Report</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 4px;font-size:18px;font-weight:600;color:#f1f5f9;">{period_label}</p>
          <p style="margin:0 0 8px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <p style="margin:0 0 24px;font-size:24px;font-weight:700;color:#2dd4bf;">${total_cost} <span style="font-size:14px;color:#64748b;font-weight:400;">total spend</span></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;border:1px solid #334155;overflow:hidden;margin-bottom:24px;">
            <thead>
              <tr style="background:#0f172a;">
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Date</th>
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Provider</th>
                <th style="padding:10px 12px;text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Model</th>
                <th style="padding:10px 12px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Cost</th>
                <th style="padding:10px 12px;text-align:right;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Calls</th>
              </tr>
            </thead>
            <tbody>
              {html_rows}
              {truncation_note}
            </tbody>
          </table>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text)


async def send_verification_email(to_email: str, full_name: str, verify_url: str) -> None:
    """Resend verification email (without password)."""
    name = full_name or to_email
    subject = "Verify your RunLedger email address"

    text = f"Hi {name},\n\nVerify your email: {verify_url}\n\nThis link expires in 24 hours.\n\n— RunLedger"

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#0f766e,#0891b2);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 16px;font-size:18px;font-weight:600;color:#f1f5f9;">Verify your email, {name}</p>
          <table cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr><td style="background:linear-gradient(135deg,#0d9488,#0891b2);border-radius:8px;">
              <a href="{verify_url}" style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:600;color:#fff;text-decoration:none;">Verify Email Address</a>
            </td></tr>
          </table>
          <p style="margin:0;font-size:12px;color:#475569;">Link expires in 24 hours.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text)
