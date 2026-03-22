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
