from __future__ import annotations

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email_notification(rca_output: str) -> None:
    """Send RCA result via email."""
    smtp_server = os.getenv("SMTP_SERVER", "").strip()
    smtp_port_str = os.getenv("SMTP_PORT", "587").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    email_from = os.getenv("EMAIL_FROM", smtp_user or "rca-bot@example.com").strip()
    email_to = os.getenv("EMAIL_TO", "").strip()

    if not email_to:
        raise ValueError("Set EMAIL_TO to enable email notifications")
    if not smtp_server:
        raise ValueError("Set SMTP_SERVER to enable email notifications")

    try:
        smtp_port = int(smtp_port_str) if smtp_port_str else 587
    except ValueError:
        raise ValueError(f"SMTP_PORT must be a valid integer, got: {smtp_port_str}")

    # Parse RCA output for subject and body
    try:
        finding = json.loads(rca_output)
        subject = f"RCA Alert: {finding.get('probable_root_cause', 'Unknown')}"
        body = format_email_body(finding)
    except json.JSONDecodeError:
        subject = "RCA Update"
        body = f"<pre>{rca_output.strip()}</pre>"

    msg = MIMEMultipart("alternative")
    msg["From"] = email_from
    msg["To"] = email_to
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            if smtp_user and smtp_password:
                server.starttls()
                server.login(smtp_user, smtp_password)
            server.sendmail(email_from, [email_to], msg.as_string())
    except Exception as error:
        raise RuntimeError(f"Failed to send email: {error}") from error


def format_email_body(finding: dict) -> str:
    """Format RCA finding as HTML email body."""
    evidence = "<br>".join(f"• {item}" for item in finding.get("evidence", [])) or "No evidence captured"
    remediation = "<br>".join(
        f"• {item}" for item in finding.get("remediation_steps", [])
    ) or "No remediation steps available"

    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2 style="color: #d32f2f;">Splunk RCA Alert</h2>
        
        <p><strong>Service:</strong> {finding.get('affected_service', 'unknown')}</p>
        <p><strong>Probable Cause:</strong> {finding.get('probable_root_cause', 'unknown')}</p>
        <p><strong>Confidence:</strong> {finding.get('confidence', 'unknown')}</p>
        
        <h3>Explanation</h3>
        <p>{finding.get('explanation', 'No explanation available')}</p>
        
        <h3>Evidence</h3>
        <p>{evidence}</p>
        
        <h3>Suggested Actions</h3>
        <p>{remediation}</p>
        
        <hr>
        <p style="color: #666; font-size: 0.9em;">
          This is an automated RCA alert. Please validate before taking action.
        </p>
      </body>
    </html>
    """
