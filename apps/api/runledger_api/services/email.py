"""Email service — sends transactional emails via Brevo SMTP."""

from __future__ import annotations

import asyncio
import smtplib
import textwrap
import uuid
from typing import TYPE_CHECKING

import structlog

from runledger_api.core.config import settings

if TYPE_CHECKING:
    pass

log = structlog.get_logger()


def get_unsubscribe_url(base_url: str, token: str) -> str:
    """Build an unsubscribe URL from base URL and user token."""
    return f"{base_url}/unsubscribe?token={token}"


def _send_smtp(to_email: str, subject: str, html: str, text: str) -> None:
    """Synchronous SMTP send — run via asyncio.to_thread."""
    msg = __import__("email.mime.multipart", fromlist=["MIMEMultipart"]).MIMEMultipart(
        "alternative"
    )
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

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


async def _log_email(
    workspace_id: uuid.UUID | None,
    to_email: str,
    subject: str,
    event_type: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Write email delivery record to email_log table."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from runledger_api.core.config import settings as _settings
    from runledger_api.models.email_prefs import EmailLog

    try:
        engine = create_async_engine(_settings.database_url, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            db.add(
                EmailLog(
                    workspace_id=workspace_id,
                    to_email=to_email,
                    subject=subject,
                    event_type=event_type,
                    status=status,
                    error_message=error_message,
                )
            )
            await db.commit()
        await engine.dispose()
    except Exception:
        pass  # logging failure must never break email sending


async def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    *,
    workspace_id: uuid.UUID | None = None,
    event_type: str = "generic",
    background: bool = True,
) -> None:
    """Send an email async. Silently logs on failure so signup never breaks."""
    if not settings.email_enabled:
        log.info("email_skipped_disabled", to=to_email, subject=subject)
        return
    if not settings.smtp_user or not settings.smtp_password:
        log.warning("email_skipped_no_smtp_config", to=to_email, subject=subject)
        return
    exc_str: str | None = None
    try:
        await asyncio.to_thread(_send_smtp, to_email, subject, html, text)
        log.info("email_sent", to=to_email, subject=subject)
        _status = "sent"
    except Exception as exc:
        log.exception("email_send_failed", to=to_email, subject=subject)
        exc_str = str(exc)
        _status = "failed"

    log_coro = _log_email(workspace_id, to_email, subject, event_type, _status, exc_str)
    if background:
        try:
            asyncio.get_running_loop()
            asyncio.create_task(log_coro)
        except RuntimeError:
            await log_coro
    else:
        await log_coro


async def send_welcome_email(
    to_email: str,
    full_name: str,
    password: str,
    api_key: str,
    verify_url: str,
) -> None:
    name = full_name or to_email
    reset_url = f"{settings.app_base_url}/reset-password?token={verify_url.split('token=')[-1]}" if "token=" in verify_url else verify_url
    subject = "Welcome to RunLedger — verify your email"

    text = textwrap.dedent(f"""\
        Hi {name},

        Welcome to RunLedger! Your account has been created.

        Email: {to_email}

        Please verify your email and set your password:
        {reset_url}

        Your API key is available in the dashboard after login.

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
          <p style="margin:0 0 28px;font-size:14px;color:#94a3b8;line-height:1.6;">Your RunLedger account is ready. Verify your email and set your password to get started.</p>

          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr>
              <td style="padding:14px 20px;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Email</p>
                <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;font-family:monospace;">{to_email}</p>
              </td>
            </tr>
          </table>

          <!-- Verify + set password button -->
          <p style="margin:0 0 16px;font-size:14px;color:#94a3b8;">Click below to verify your email and set your password:</p>
          <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
            <tr><td style="background:linear-gradient(135deg,#0d9488,#0891b2);border-radius:8px;">
              <a href="{reset_url}" style="display:inline-block;padding:14px 32px;font-size:14px;font-weight:600;color:#fff;text-decoration:none;">Verify &amp; Set Password</a>
            </td></tr>
          </table>

          <p style="margin:0 0 12px;font-size:13px;color:#94a3b8;">Your API key will be available in the dashboard under <strong style="color:#e2e8f0;">Settings &gt; API Keys</strong> after you log in.</p>
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

    await send_email(to_email, subject, html, text, event_type="welcome")


async def send_alert_fired_email(
    to_email: str,
    full_name: str | None,
    rule_name: str,
    metric: str,
    operator: str,
    threshold: str,
    value: str,
    workspace_name: str,
    unsubscribe_url: str = "",
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

    unsub_html = (
        f'<p style="margin:8px 0 0;font-size:11px;color:#475569;">'
        f'<a href="{unsubscribe_url}" style="color:#475569;">Unsubscribe</a></p>'
        if unsubscribe_url
        else ""
    )

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
          {unsub_html}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text, event_type="alert_fired")


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

    await send_email(to_email, subject, html, text, event_type="approval_request")


async def send_approval_decision_email(
    to_email: str,
    request_type: str,
    decision: str,
    decision_note: str | None,
    decided_by: str | None,
    workspace_name: str,
    *,
    template: str = "detailed",
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

    await send_email(to_email, subject, html, text, event_type="approval_decision")


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
    matched_color = (
        "#4ade80" if matched_pct >= 90 else "#f59e0b" if matched_pct >= 70 else "#f87171"
    )
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

    await send_email(to_email, subject, html, text, event_type="reconciliation")


async def send_analytics_report_email(
    to_email: str,
    full_name: str | None,
    period_label: str,
    rows: list[dict[str, object]],
    total_cost: str,
    workspace_name: str,
    *,
    template: str = "detailed",
) -> None:
    """Send a usage analytics report email."""
    name = full_name or to_email
    subject = f"RunLedger: Analytics Report — {period_label}"

    template = template if template in {"executive", "summary", "detailed"} else "detailed"
    row_limit = 10 if template == "executive" else 25 if template == "summary" else 50
    intro_line = {
        "executive": "A concise spend snapshot for fast review.",
        "summary": "A balanced usage summary for operators and finance.",
        "detailed": "A detailed usage breakdown for operations review.",
    }[template]

    # Build plain-text table
    lines = [f"{'Date':<12} {'Provider':<16} {'Model':<28} {'Cost (USD)':>12} {'Calls':>8}"]
    lines.append("-" * 80)
    for r in rows[:row_limit]:
        lines.append(
            f"{str(r.get('date', '')):<12} {str(r.get('provider', '')):<16} "
            f"{str(r.get('model', '')):<28} {str(r.get('cost_usd', '0')):>12} "
            f"{str(r.get('call_count', '0')):>8}"
        )
    if len(rows) > row_limit:
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
    for i, r in enumerate(rows[:row_limit]):
        bg = "#0f172a" if i % 2 == 0 else "#111827"
        html_rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:8px 12px;color:#e2e8f0;font-size:12px;">{r.get("date", "")}</td>'
            f'<td style="padding:8px 12px;color:#e2e8f0;font-size:12px;">{r.get("provider", "")}</td>'
            f'<td style="padding:8px 12px;color:#94a3b8;font-size:12px;font-family:monospace;">{r.get("model", "")}</td>'
            f'<td style="padding:8px 12px;color:#2dd4bf;font-size:12px;text-align:right;">${r.get("cost_usd", "0")}</td>'
            f'<td style="padding:8px 12px;color:#e2e8f0;font-size:12px;text-align:right;">{r.get("call_count", "0")}</td>'
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

    await send_email(to_email, subject, html, text, event_type="analytics_report")


async def send_budget_breach_email(
    to_email: str,
    full_name: str | None,
    scope_type: str,
    scope_id: str | None,
    period_type: str,
    limit_usd: str,
    spent_usd: str,
    action: str,
    workspace_name: str,
    unsubscribe_url: str = "",
) -> None:
    """Notify workspace admins of a budget breach or runaway protection event."""
    name = full_name or to_email
    subject = f"RunLedger Budget Alert: {scope_type} — action: {action}"

    scope_label = f"{scope_type}" + (f" ({scope_id})" if scope_id else "")

    unsub_html = (
        f'<p style="margin:8px 0 0;font-size:11px;color:#475569;">'
        f'<a href="{unsubscribe_url}" style="color:#475569;">Unsubscribe</a></p>'
        if unsubscribe_url
        else ""
    )

    text = textwrap.dedent(f"""\
        Hi {name},

        A budget alert has fired in workspace "{workspace_name}".

        Scope:     {scope_label}
        Period:    {period_type}
        Limit:     ${limit_usd}
        Spent:     ${spent_usd}
        Action:    {action}

        Log in to RunLedger to review.

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#b45309,#ea580c);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#fed7aa;">Budget Alert</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Budget Limit Exceeded</p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Scope</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{scope_label}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Period</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{period_type}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Spent / Limit</p>
              <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:#f87171;font-family:monospace;">${spent_usd} / ${limit_usd}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Action Taken</p>
              <p style="margin:4px 0 0;font-size:14px;color:#fbbf24;font-family:monospace;">{action}</p>
            </td></tr>
          </table>
          <p style="margin:0;font-size:13px;color:#64748b;">Log in to RunLedger to review and adjust your budget settings.</p>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
          {unsub_html}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text, event_type="budget_breach")


async def send_billing_period_closed_email(
    to_email: str,
    full_name: str | None,
    period_start: str,
    period_end: str,
    total_cost_usd: str,
    snapshot_hash: str,
    workspace_name: str,
    unsubscribe_url: str = "",
) -> None:
    """Notify workspace admins when a billing period is closed and signed."""
    name = full_name or to_email
    subject = f"RunLedger: Billing Period Closed — {period_start} to {period_end}"

    unsub_html = (
        f'<p style="margin:8px 0 0;font-size:11px;color:#475569;">'
        f'<a href="{unsubscribe_url}" style="color:#475569;">Unsubscribe</a></p>'
        if unsubscribe_url
        else ""
    )

    text = textwrap.dedent(f"""\
        Hi {name},

        A billing period has been closed and signed in workspace "{workspace_name}".

        Period:     {period_start} to {period_end}
        Total Cost: ${total_cost_usd}
        HMAC Hash:  {snapshot_hash}

        The signed snapshot is tamper-evident and available for audit export.

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#065f46,#0891b2);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#6ee7b7;">Billing Period Closed</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Billing Period Signed &amp; Closed</p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Period</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{period_start} → {period_end}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Total Cost</p>
              <p style="margin:4px 0 0;font-size:20px;font-weight:700;color:#4ade80;">${total_cost_usd}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">HMAC Signature (first 16 chars)</p>
              <p style="margin:4px 0 0;font-size:12px;color:#2dd4bf;font-family:monospace;">{snapshot_hash}</p>
            </td></tr>
          </table>
          <p style="margin:0;font-size:13px;color:#64748b;">The signed snapshot is tamper-evident. Export it from the Billing section for audit purposes.</p>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
          {unsub_html}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text, event_type="billing_closed")


async def send_dispute_flagged_email(
    to_email: str,
    full_name: str | None,
    provider: str,
    line_date: str,
    dispute_note: str | None,
    workspace_name: str,
    unsubscribe_url: str = "",
) -> None:
    """Notify workspace admins when an invoice line is marked disputed."""
    name = full_name or to_email
    subject = f"RunLedger: Invoice Line Disputed — {provider}"

    note_html = (
        f'<tr><td style="padding:14px 20px;">'
        f'<p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Dispute Note</p>'
        f'<p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{dispute_note}</p>'
        f"</td></tr>"
        if dispute_note
        else ""
    )
    note_text = f"\nNote:      {dispute_note}" if dispute_note else ""

    unsub_html = (
        f'<p style="margin:8px 0 0;font-size:11px;color:#475569;">'
        f'<a href="{unsubscribe_url}" style="color:#475569;">Unsubscribe</a></p>'
        if unsubscribe_url
        else ""
    )

    text = textwrap.dedent(f"""\
        Hi {name},

        An invoice line has been marked as disputed in workspace "{workspace_name}".

        Provider:  {provider}
        Date:      {line_date}{note_text}

        Log in to RunLedger to review the invoice and export the dispute package.

        — The RunLedger Team
    """)

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;">
        <tr><td style="background:linear-gradient(135deg,#78350f,#b45309);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#fde68a;">Invoice Line Disputed</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Invoice Line Flagged as Disputed</p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Provider</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{provider}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Line Date</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;">{line_date}</p>
            </td></tr>
            {note_html}
          </table>
          <p style="margin:0;font-size:13px;color:#64748b;">Log in to RunLedger to review the invoice and export the dispute package for finance.</p>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
          {unsub_html}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text, event_type="dispute_flagged")


async def send_score_regression_email(
    to_email: str,
    full_name: str | None,
    metric_name: str,
    current_avg: float,
    prior_avg: float,
    change_pct: float,
    workspace_name: str,
    unsubscribe_url: str = "",
) -> None:
    """Notify workspace admins when a score metric regresses significantly."""
    name = full_name or to_email
    subject = f"RunLedger: Score Regression Detected — {metric_name}"

    unsub_html = (
        f'<p style="margin:8px 0 0;font-size:11px;color:#475569;">'
        f'<a href="{unsubscribe_url}" style="color:#475569;">Unsubscribe</a></p>'
        if unsubscribe_url
        else ""
    )

    text = textwrap.dedent(f"""\
        Hi {name},

        A score regression has been detected in workspace "{workspace_name}".

        Metric:      {metric_name}
        Current Avg: {current_avg:.4f}
        Prior Avg:   {prior_avg:.4f}
        Change:      -{change_pct:.1f}%

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
        <tr><td style="background:linear-gradient(135deg,#92400e,#b45309);padding:32px 40px;">
          <p style="margin:0;font-size:22px;font-weight:700;color:#fff;">RunLedger</p>
          <p style="margin:4px 0 0;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:#fde68a;">Score Regression Detected</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:18px;font-weight:600;color:#f1f5f9;">Score Metric Regression</p>
          <p style="margin:0 0 24px;font-size:14px;color:#94a3b8;">Workspace: <strong style="color:#e2e8f0;">{workspace_name}</strong></p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;border:1px solid #334155;margin-bottom:28px;">
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Metric</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;font-family:monospace;">{metric_name}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Current Avg</p>
              <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:#f87171;font-family:monospace;">{current_avg:.4f}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;border-bottom:1px solid #334155;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Prior 7-day Avg</p>
              <p style="margin:4px 0 0;font-size:14px;color:#e2e8f0;font-family:monospace;">{prior_avg:.4f}</p>
            </td></tr>
            <tr><td style="padding:14px 20px;">
              <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Change</p>
              <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:#f87171;font-family:monospace;">-{change_pct:.1f}%</p>
            </td></tr>
          </table>
          <p style="margin:0;font-size:13px;color:#64748b;">Log in to RunLedger to investigate this score regression.</p>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
          <p style="margin:0;font-size:12px;color:#475569;">RunLedger · Billing-grade observability for AI agents</p>
          {unsub_html}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    await send_email(to_email, subject, html, text, event_type="score_regression")


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

    await send_email(to_email, subject, html, text, event_type="verification")
