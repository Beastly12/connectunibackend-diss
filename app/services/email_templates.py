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