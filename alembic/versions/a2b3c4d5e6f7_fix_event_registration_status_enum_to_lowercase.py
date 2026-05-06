"""fix event_registration_status_enum values to lowercase

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-05-06 15:30:00.000000
"""
from alembic import op

revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE event_registration_status_enum RENAME TO event_registration_status_enum_old")

    op.execute(
        "CREATE TYPE event_registration_status_enum AS ENUM ('registered', 'attended', 'cancelled')"
    )

    op.execute("""
        ALTER TABLE event_registrations
        ALTER COLUMN status TYPE event_registration_status_enum
        USING lower(status::text)::event_registration_status_enum
    """)

    op.execute("DROP TYPE event_registration_status_enum_old")


def downgrade():
    op.execute("ALTER TYPE event_registration_status_enum RENAME TO event_registration_status_enum_old")

    op.execute(
        "CREATE TYPE event_registration_status_enum AS ENUM ('REGISTERED', 'ATTENDED', 'CANCELLED')"
    )

    op.execute("""
        ALTER TABLE event_registrations
        ALTER COLUMN status TYPE event_registration_status_enum
        USING upper(status::text)::event_registration_status_enum
    """)

    op.execute("DROP TYPE event_registration_status_enum_old")
