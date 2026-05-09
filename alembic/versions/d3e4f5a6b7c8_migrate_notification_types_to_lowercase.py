"""migrate existing notification rows from uppercase to lowercase type values

Must run AFTER c2d3e4f5a6b7 which adds the lowercase enum values.
ALTER TYPE ADD VALUE must be committed before the new values can be used
in DML, so this data migration is a separate transaction.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-09 00:02:00.000000
"""
from alembic import op

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None

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


def upgrade():
    for uc, lc in _RENAMES:
        op.execute(
            f"UPDATE notifications SET type = '{lc}' WHERE type = '{uc}'"
        )


def downgrade():
    for uc, lc in _RENAMES:
        op.execute(
            f"UPDATE notifications SET type = '{uc}' WHERE type = '{lc}'"
        )
