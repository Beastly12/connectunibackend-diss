"""fix notification_type_enum: add lowercase values and migrate existing data

The original migration created the enum with UPPERCASE values (MESSAGE,
MENTORSHIP_REQUEST, etc.). The code now uses lowercase values. This migration:
1. Adds all missing lowercase enum values (IF NOT EXISTS)
2. Updates existing notification rows to use lowercase values
3. Also adds new values that did not exist at all (event_rsvp)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-05-09 00:01:00.000000
"""
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None

# Pairs of (old_uppercase_value, new_lowercase_value)
_RENAMES = [
    ("MESSAGE", "message"),
    ("MENTORSHIP_REQUEST", "mentorship_request"),
    ("MENTORSHIP_ACCEPTED", "mentorship_accepted"),
    ("MENTORSHIP_REJECTED", "mentorship_rejected"),
    ("CONNECTION_REQUEST", "connection_request"),
    ("CONNECTION_ACCEPTED", "connection_accepted"),
    ("EVENT_REMINDER", "event_reminder"),
    ("POST_LIKE", "post_like"),
    ("POST_COMMENT", "post_comment"),
    ("JOB_APPLICATION", "job_application"),
]

# Brand-new values that have never existed in the enum
_NEW_VALUES = ["event_rsvp"]


def upgrade():
    # Only ADD VALUE here. PostgreSQL requires ADD VALUE to be committed
    # before the new values can be used in DML — they cannot coexist in
    # the same transaction. The data UPDATE is in the next migration.
    for _, lc in _RENAMES:
        op.execute(
            f"ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS '{lc}'"
        )
    for val in _NEW_VALUES:
        op.execute(
            f"ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS '{val}'"
        )


def downgrade():
    pass  # PostgreSQL does not support removing enum values
