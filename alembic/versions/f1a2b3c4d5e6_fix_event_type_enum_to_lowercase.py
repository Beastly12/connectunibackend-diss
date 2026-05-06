"""fix event_type_enum values to lowercase

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE event_type_enum RENAME TO event_type_enum_old")

    op.execute(
        "CREATE TYPE event_type_enum AS ENUM ('academic', 'social', 'career', 'networking')"
    )

    op.execute("""
        ALTER TABLE events
        ALTER COLUMN event_type TYPE event_type_enum
        USING lower(event_type::text)::event_type_enum
    """)

    op.execute("DROP TYPE event_type_enum_old")


def downgrade():
    op.execute("ALTER TYPE event_type_enum RENAME TO event_type_enum_old")
    op.execute(
        "CREATE TYPE event_type_enum AS ENUM ('ACADEMIC', 'SOCIAL', 'CAREER', 'NETWORKING')"
    )
    op.execute("""
        ALTER TABLE events
        ALTER COLUMN event_type TYPE event_type_enum
        USING upper(event_type::text)::event_type_enum
    """)
    op.execute("DROP TYPE event_type_enum_old")
