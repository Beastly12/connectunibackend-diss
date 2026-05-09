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
    # This data migration must be applied manually via a fresh DB connection
    # because asyncpg caches enum type info per-connection and cannot see
    # enum values added by ALTER TYPE ADD VALUE in the same connection.
    # Run once on the server:
    #   docker compose run --rm api python3 -c "
    #     import asyncio, asyncpg, os
    #     async def main():
    #         url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    #         conn = await asyncpg.connect(url)
    #         pairs = [('MESSAGE','message'),('MENTORSHIP_REQUEST','mentorship_request'),
    #                  ('MENTORSHIP_ACCEPTED','mentorship_accepted'),('MENTORSHIP_REJECTED','mentorship_rejected'),
    #                  ('CONNECTION_REQUEST','connection_request'),('CONNECTION_ACCEPTED','connection_accepted'),
    #                  ('EVENT_REMINDER','event_reminder'),('POST_LIKE','post_like'),
    #                  ('POST_COMMENT','post_comment'),('JOB_APPLICATION','job_application')]
    #         for old, new in pairs:
    #             await conn.execute(f\"UPDATE notifications SET type = '{new}' WHERE type = '{old}'\")
    #         await conn.close()
    #     asyncio.run(main())
    #   "
    # Then: docker compose run --rm api alembic stamp d3e4f5a6b7c8
    pass


def downgrade():
    pass
