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
    certificate_received_template,
    verification_status_update_template,
    mentorship_preferences_template,
    mentorship_request_template,
    mentorship_accepted_template,
    mentorship_rejected_template,
    mentee_cancelled_request_template,
    milestone_completed_template,
    session_cancelled_template,
    resource_shared_template,
    relationship_ended_template,
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


def send_certificate_received_email(to_email: str, first_name: str) -> None:
    """Sent when an alumni uploads a graduation certificate for review."""
    send_email(
        to_email=to_email,
        subject="Certificate Received — Under Review | ConnectUni",
        html_content=certificate_received_template(first_name=first_name),
    )


def send_verification_status_update_email(
    to_email: str, first_name: str, new_status: str
) -> None:
    """Sent when an admin updates a user's verification status."""
    subject_map = {
        "verified": "Your Account Has Been Verified ✅ — ConnectUni",
        "pending": "Verification Under Review — ConnectUni",
        "unverified": "Verification Update — ConnectUni",
    }
    subject = subject_map.get(new_status, "Verification Status Update — ConnectUni")
    send_email(
        to_email=to_email,
        subject=subject,
        html_content=verification_status_update_template(
            first_name=first_name, new_status=new_status
        ),
    )


def send_mentorship_preferences_email(
    to_email: str,
    first_name: str,
    is_mentor: bool,
    is_mentee: bool,
    areas: list[str],
    hours_per_week: int,
    preferred_format: str,
) -> None:
    """Sent after a user saves their mentorship preferences."""
    send_email(
        to_email=to_email,
        subject="Your Mentorship Preferences — ConnectUni",
        html_content=mentorship_preferences_template(
            first_name=first_name,
            is_mentor=is_mentor,
            is_mentee=is_mentee,
            areas=areas,
            hours_per_week=hours_per_week,
            preferred_format=preferred_format,
        ),
    )


# ---------------------------------------------------------------------------
# Mentorship action emails  (2.6)
# ---------------------------------------------------------------------------

def send_mentorship_request_email(
    to_email: str, mentor_first_name: str, mentee_name: str
) -> None:
    """Sent to the mentor when a mentee sends them a request."""
    send_email(
        to_email=to_email,
        subject=f"New Mentorship Request from {mentee_name} — ConnectUni",
        html_content=mentorship_request_template(
            mentor_first_name=mentor_first_name,
            mentee_name=mentee_name,
        ),
    )


def send_mentorship_accepted_email(
    to_email: str, mentee_first_name: str, mentor_name: str
) -> None:
    """Sent to the mentee when the mentor accepts their request."""
    send_email(
        to_email=to_email,
        subject=f"{mentor_name} Accepted Your Mentorship Request — ConnectUni",
        html_content=mentorship_accepted_template(
            mentee_first_name=mentee_first_name,
            mentor_name=mentor_name,
        ),
    )


def send_mentorship_rejected_email(
    to_email: str, mentee_first_name: str, mentor_name: str
) -> None:
    """Sent to the mentee when the mentor declines their request."""
    send_email(
        to_email=to_email,
        subject="Mentorship Request Update — ConnectUni",
        html_content=mentorship_rejected_template(
            mentee_first_name=mentee_first_name,
            mentor_name=mentor_name,
        ),
    )


def send_mentee_cancelled_request_email(
    to_email: str, mentor_first_name: str, mentee_name: str
) -> None:
    """Sent to the mentor when the mentee cancels their pending request."""
    send_email(
        to_email=to_email,
        subject=f"{mentee_name} Cancelled Their Request — ConnectUni",
        html_content=mentee_cancelled_request_template(
            mentor_first_name=mentor_first_name,
            mentee_name=mentee_name,
        ),
    )


def send_milestone_completed_email(
    to_email: str,
    recipient_first_name: str,
    actor_name: str,
    milestone_title: str,
) -> None:
    """Sent to the other participant when a milestone is marked as completed."""
    send_email(
        to_email=to_email,
        subject=f"Milestone Completed: {milestone_title} — ConnectUni",
        html_content=milestone_completed_template(
            recipient_first_name=recipient_first_name,
            actor_name=actor_name,
            milestone_title=milestone_title,
        ),
    )


def send_session_cancelled_email(
    to_email: str,
    recipient_first_name: str,
    actor_name: str,
    scheduled_at: datetime,
) -> None:
    """Sent to the other participant when a session is cancelled."""
    formatted = scheduled_at.strftime("%A, %d %B %Y at %H:%M")
    send_email(
        to_email=to_email,
        subject="Session Cancelled — ConnectUni",
        html_content=session_cancelled_template(
            recipient_first_name=recipient_first_name,
            actor_name=actor_name,
            scheduled_at=formatted,
        ),
    )


def send_resource_shared_email(
    to_email: str,
    recipient_first_name: str,
    sharer_name: str,
    resource_title: str,
) -> None:
    """Sent to the other participant when a resource is shared."""
    send_email(
        to_email=to_email,
        subject=f"New Resource Shared by {sharer_name} — ConnectUni",
        html_content=resource_shared_template(
            recipient_first_name=recipient_first_name,
            sharer_name=sharer_name,
            resource_title=resource_title,
        ),
    )


def send_relationship_ended_email(
    to_email: str,
    recipient_first_name: str,
    actor_name: str,
) -> None:
    """Sent to the other participant when a relationship is ended."""
    send_email(
        to_email=to_email,
        subject="Mentorship Relationship Ended — ConnectUni",
        html_content=relationship_ended_template(
            recipient_first_name=recipient_first_name,
            actor_name=actor_name,
        ),
    )