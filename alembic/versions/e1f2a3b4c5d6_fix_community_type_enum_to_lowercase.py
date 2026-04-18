"""fix community_type_enum values to lowercase

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-04-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade():
    # Rename old enum
    op.execute("ALTER TYPE community_type_enum RENAME TO community_type_enum_old")

    # Create new enum with lowercase values
    op.execute("CREATE TYPE community_type_enum AS ENUM ('global', 'university')")

    # Update the column to use the new type, casting via text and lowercasing
    op.execute("""
        ALTER TABLE communities
        ALTER COLUMN type TYPE community_type_enum
        USING lower(type::text)::community_type_enum
    """)

    # Drop the old enum
    op.execute("DROP TYPE community_type_enum_old")


def downgrade():
    op.execute("ALTER TYPE community_type_enum RENAME TO community_type_enum_old")
    op.execute("CREATE TYPE community_type_enum AS ENUM ('GLOBAL', 'UNIVERSITY')")
    op.execute("""
        ALTER TABLE communities
        ALTER COLUMN type TYPE community_type_enum
        USING upper(type::text)::community_type_enum
    """)
    op.execute("DROP TYPE community_type_enum_old")
