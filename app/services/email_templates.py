"""
HTML email templates for ConnectUni.
All templates use .format() with named placeholders.
"""


def welcome_template(first_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #007bff; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Welcome to ConnectUni 👋</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>Thanks for joining ConnectUni — the platform connecting students and alumni.</p>
      <p>Your account has been created. Please verify your email address to get started.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def verification_template(first_name: str, verification_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #007bff; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Verify Your Email</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>Please verify your email address by clicking the button below:</p>
      <div style="margin: 30px 0; text-align: center;">
        <a href="{verification_url}"
           style="background-color: #007bff; color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-size: 16px; display: inline-block;">
          Verify Email Address
        </a>
      </div>
      <p>Or copy and paste this link into your browser:</p>
      <p style="color: #007bff; word-break: break-all; font-size: 14px;">{verification_url}</p>
      <p style="color: #999; font-size: 13px;">This link expires in 24 hours. If you didn't create a ConnectUni account, you can safely ignore this email.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def password_reset_template(first_name: str, reset_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #dc3545; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Password Reset Request</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>We received a request to reset your ConnectUni password. Click the button below to set a new one:</p>
      <div style="margin: 30px 0; text-align: center;">
        <a href="{reset_url}"
           style="background-color: #dc3545; color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-size: 16px; display: inline-block;">
          Reset My Password
        </a>
      </div>
      <p>Or copy and paste this link into your browser:</p>
      <p style="color: #dc3545; word-break: break-all; font-size: 14px;">{reset_url}</p>
      <p style="color: #999; font-size: 13px;">This link expires in 30 minutes. If you didn't request a password reset, you can safely ignore this email — your password will not change.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def certificate_received_template(first_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #6f42c1; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Certificate Received</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>We've received your graduation certificate and it's now <strong>under review</strong> by our team.</p>
      <p>We'll notify you once the review is complete — this usually takes 1–3 business days.</p>
      <p>Thank you for helping us keep ConnectUni a trusted community.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def verification_status_update_template(first_name: str, new_status: str) -> str:
    if new_status == "verified":
        colour = "#28a745"
        heading = "Account Verified ✅"
        body = "Great news — your account has been <strong>verified</strong>. You now have full access to all ConnectUni features."
    elif new_status == "pending":
        colour = "#ffc107"
        heading = "Verification Under Review"
        body = "Your verification request is currently <strong>under review</strong>. We'll be in touch shortly."
    else:
        colour = "#dc3545"
        heading = "Verification Unsuccessful"
        body = "Unfortunately we could not verify your account at this time. Please re-upload your certificate or contact support for assistance."

    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: {colour}; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">{heading}</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>{body}</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def mentorship_preferences_template(
    first_name: str,
    is_mentor: bool,
    is_mentee: bool,
    areas: list[str],
    hours_per_week: int,
    preferred_format: str,
) -> str:
    role_parts = []
    if is_mentor:
        role_parts.append("mentor")
    if is_mentee:
        role_parts.append("mentee")
    role_str = " and ".join(role_parts).capitalize()
    areas_str = ", ".join(areas) if areas else "Not specified"
    format_display = preferred_format.replace("_", " ").title()

    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #007bff; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Mentorship Preferences Set 🎓</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>You've successfully set your mentorship preferences on ConnectUni. Here's a summary:</p>
      <div style="background-color: white; border-left: 4px solid #007bff; padding: 16px; margin: 20px 0; border-radius: 4px;">
        <p style="margin: 0 0 8px 0;"><strong>Role:</strong> {role_str}</p>
        <p style="margin: 0 0 8px 0;"><strong>Areas of interest:</strong> {areas_str}</p>
        <p style="margin: 0 0 8px 0;"><strong>Availability:</strong> {hours_per_week} hour(s) per week</p>
        <p style="margin: 0;"><strong>Preferred format:</strong> {format_display}</p>
      </div>
      <p>We'll use this to help match you with the right people. You can update your preferences at any time.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def mentorship_request_template(mentor_first_name: str, mentee_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #007bff; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">New Mentorship Request</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{mentor_first_name}</strong>,</p>
      <p><strong>{mentee_name}</strong> has sent you a mentorship request on ConnectUni.</p>
      <p>Log in to review their request and decide whether to accept or decline.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def mentorship_accepted_template(mentee_first_name: str, mentor_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #28a745; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Mentorship Request Accepted! 🎉</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{mentee_first_name}</strong>,</p>
      <p>Great news — <strong>{mentor_name}</strong> has accepted your mentorship request.</p>
      <p>Log in to ConnectUni to schedule your first session and get started!</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def mentorship_rejected_template(mentee_first_name: str, mentor_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #6c757d; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Mentorship Request Update</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{mentee_first_name}</strong>,</p>
      <p>Unfortunately, <strong>{mentor_name}</strong> is unable to take on new mentees at this time.</p>
      <p>Don't be discouraged — browse other mentors on ConnectUni who may be a great fit for you.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def mentee_cancelled_request_template(mentor_first_name: str, mentee_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #ffc107; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: #333; margin: 0;">Mentorship Request Cancelled</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{mentor_first_name}</strong>,</p>
      <p><strong>{mentee_name}</strong> has cancelled their mentorship request to you.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def milestone_completed_template(recipient_first_name: str, actor_name: str, milestone_title: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #28a745; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Milestone Completed ✅</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{recipient_first_name}</strong>,</p>
      <p><strong>{actor_name}</strong> has marked the following milestone as completed:</p>
      <div style="background-color: white; border-left: 4px solid #28a745; padding: 16px; margin: 20px 0; border-radius: 4px;">
        <p style="margin: 0; font-weight: bold;">{milestone_title}</p>
      </div>
      <p>Great progress on your learning journey!</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def session_cancelled_template(recipient_first_name: str, actor_name: str, scheduled_at: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #dc3545; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Session Cancelled</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{recipient_first_name}</strong>,</p>
      <p><strong>{actor_name}</strong> has cancelled your scheduled session on <strong>{scheduled_at}</strong>.</p>
      <p>Please log in to ConnectUni to reschedule at a time that works for both of you.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def resource_shared_template(recipient_first_name: str, sharer_name: str, resource_title: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #007bff; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">New Resource Shared 📚</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{recipient_first_name}</strong>,</p>
      <p><strong>{sharer_name}</strong> has shared a resource with you:</p>
      <div style="background-color: white; border-left: 4px solid #007bff; padding: 16px; margin: 20px 0; border-radius: 4px;">
        <p style="margin: 0; font-weight: bold;">{resource_title}</p>
      </div>
      <p>Log in to ConnectUni to view it.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def relationship_ended_template(recipient_first_name: str, actor_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #6c757d; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">Mentorship Relationship Ended</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{recipient_first_name}</strong>,</p>
      <p><strong>{actor_name}</strong> has ended your mentorship relationship on ConnectUni.</p>
      <p>Thank you for being part of the ConnectUni community. You can browse new mentors or mentees at any time.</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""


def rsvp_confirmation_template(first_name: str, event_title: str, event_date: str, event_location: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #28a745; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="color: white; margin: 0;">You're going! 🎉</h1>
    </div>
    <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>Your RSVP has been confirmed for the following event:</p>
      <div style="background-color: white; border-left: 4px solid #28a745; padding: 16px; margin: 20px 0; border-radius: 4px;">
        <p style="margin: 0 0 8px 0;"><strong>📅 {event_title}</strong></p>
        <p style="margin: 0 0 4px 0; color: #555;">Date: {event_date}</p>
        <p style="margin: 0; color: #555;">Location: {event_location or 'To be announced'}</p>
      </div>
      <p>We look forward to seeing you there!</p>
      <p style="color: #666; font-size: 14px;">— The ConnectUni Team</p>
    </div>
  </body>
</html>
"""