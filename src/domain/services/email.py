"""Email service for sending transactional emails."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email settings from environment
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@auditeng.local")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send password reset email with reset link.

    Returns True if email sent successfully, False otherwise.
    In development (no SMTP configured), logs the reset link instead.
    """
    reset_link = f"{APP_URL}/reset-password?token={reset_token}"

    # If SMTP not configured, just log (for development)
    if not SMTP_USER:
        print(f"[DEV] Password reset link for {to_email}: {reset_link}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "AuditEng - Password Reset Request"
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email

        text_body = f"""
You requested a password reset for your AuditEng account.

Click the link below to reset your password (valid for 15 minutes):
{reset_link}

If you did not request this reset, please ignore this email.

- AuditEng Team
"""

        html_body = f"""
<html>
<body>
<h2>Password Reset Request</h2>
<p>You requested a password reset for your AuditEng account.</p>
<p><a href="{reset_link}">Click here to reset your password</a></p>
<p><small>This link is valid for 15 minutes.</small></p>
<p>If you did not request this reset, please ignore this email.</p>
<p>- AuditEng Team</p>
</body>
</html>
"""

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Failed to send reset email to {to_email}: {e}")
        return False


async def send_temp_password_email(to_email: str, temp_password: str) -> bool:
    """Send temporary password to newly created user.

    Returns True if email sent successfully, False otherwise.
    In development (no SMTP configured), logs the password instead.
    """
    # If SMTP not configured, just log (for development)
    if not SMTP_USER:
        print(f"[DEV] Temp password for {to_email}: {temp_password}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "AuditEng - Your Account Has Been Created"
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email

        text_body = f"""
Your AuditEng account has been created.

Your temporary password is: {temp_password}

Please log in at {APP_URL} and change your password immediately.

- AuditEng Team
"""

        html_body = f"""
<html>
<body>
<h2>Welcome to AuditEng</h2>
<p>Your account has been created.</p>
<p><strong>Temporary Password:</strong> <code>{temp_password}</code></p>
<p>Please <a href="{APP_URL}">log in</a> and change your password immediately.</p>
<p>- AuditEng Team</p>
</body>
</html>
"""

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Failed to send temp password email to {to_email}: {e}")
        return False
