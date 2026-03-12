"""
Email tasks for ConnectUni.
Each function handles one specific email type.
These are called from routers or services after the relevant action completes.
"""
import logging
from datetime import datetime

from app.core.config import settings
from app.services.email_service import send_email
from app.services.email_templates import (
    welcome_template,
    verification_template,
    password_reset_template,
    rsvp_confirmation_template,
)

logger = logging.getLogger(__name__)


def send_welcome_email(to_email: str, first_name: str) -> None:
    """
    Sent immediately after a user registers.
    Informs them their account was created and that verification is required.
    """
    send_email(
        to_email=to_email,
        subject="Welcome to ConnectUni",
        html_content=welcome_template(first_name=first_name),
    )


def send_verification_email(to_email: str, first_name: str, verification_token: str) -> None:
    """
    Sent after registration with a unique token.
    The token is stored on the User model and validated at GET /auth/verify-email.
    Link expires in 24 hours — enforced by the verify endpoint checking created_at.
    """
    verification_url = f"{settings.APP_URL}/auth/verify-email?token={verification_token}"

    send_email(
        to_email=to_email,
        subject="Verify Your Email Address — ConnectUni",
        html_content=verification_template(
            first_name=first_name,
            verification_url=verification_url,
        ),
    )


def send_password_reset_email(to_email: str, first_name: str, reset_token: str) -> None:
    """
    Sent when a user requests a password reset.
    The token is stored hashed on the User model and expires in 30 minutes.
    Link points to your frontend reset page, which then calls POST /auth/reset-password.
    """
    reset_url = f"{settings.APP_URL}/auth/reset-password?token={reset_token}"

    send_email(
        to_email=to_email,
        subject="Reset Your Password — ConnectUni",
        html_content=password_reset_template(
            first_name=first_name,
            reset_url=reset_url,
        ),
    )


def send_rsvp_confirmation_email(
    to_email: str,
    first_name: str,
    event_title: str,
    event_date: datetime,
    event_location: str | None,
) -> None:
    """
    Sent after a user successfully RSVPs to an event.
    Called from EventService.rsvp() after the registration is saved.
    """
    formatted_date = event_date.strftime("%A, %d %B %Y at %H:%M")

    send_email(
        to_email=to_email,
        subject=f"RSVP Confirmed: {event_title} — ConnectUni",
        html_content=rsvp_confirmation_template(
            first_name=first_name,
            event_title=event_title,
            event_date=formatted_date,
            event_location=event_location,
        ),
    )