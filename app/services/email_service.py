import smtplib
import logging
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_content: str) -> None:
    """
    Core email sender. Uses SMTP_SSL on port 465.
    All other email functions in email_tasks.py call this.
    Raises on failure so the caller can decide how to handle it.
    """
    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("This email requires an HTML-capable email client.")
    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email sent to {to_email} — subject: '{subject}'")

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        raise

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending to {to_email}: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        raise