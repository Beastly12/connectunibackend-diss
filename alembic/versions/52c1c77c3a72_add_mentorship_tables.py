"""add mentorship tables

Revision ID: 52c1c77c3a72
Revises: b7e3f9a2c1d4
Create Date: 2026-03-31 00:00:00.000000

New tables:
- mentor_profiles
- mentorship_requests
- mentorship_relationships
- mentorship_sessions
- mentorship_resources

New enum types:
- mentorship_request_status_enum
- mentorship_relationship_status_enum
- mentorship_session_status_enum
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "52c1c77c3a72"
down_revision = "b7e3f9a2c1d4"
branch_labels = None
depends_on = None

# References to existing enum types — create_type=False means Alembic will
# never attempt a CREATE TYPE; we handle that explicitly via op.execute below.
req_status = postgresql.ENUM(
    "pending", "accepted", "rejected", "cancelled",
    name="mentorship_request_status_enum",
    create_type=False,
)
rel_status = postgresql.ENUM(
    "active", "paused", "ended",
    name="mentorship_relationship_status_enum",
    create_type=False,
)
ses_status = postgresql.ENUM(
    "upcoming", "completed", "cancelled",
    name="mentorship_session_status_enum",
    create_type=False,
)


def upgrade() -> None:
    # Create enum types with IF NOT EXISTS semantics via a DO block so the
    # migration is idempotent even if a previous attempt partially succeeded.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mentorship_request_status_enum
                AS ENUM ('pending', 'accepted', 'rejected', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mentorship_relationship_status_enum
                AS ENUM ('active', 'paused', 'ended');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mentorship_session_status_enum
                AS ENUM ('upcoming', 'completed', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # --- mentor_profiles ---
    op.create_table(
        "mentor_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column(
            "expertise_areas",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "mentorship_goals",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("availability_slots", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("max_mentees", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_mentor_profiles_user_id", "mentor_profiles", ["user_id"])

    # --- mentorship_requests ---
    op.create_table(
        "mentorship_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mentee_id", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=False),
        sa.Column("goal", sa.String(length=500), nullable=False),
        sa.Column("meeting_frequency", sa.String(length=100), nullable=False),
        sa.Column("session_length_minutes", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", req_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["mentee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mentorship_requests_mentee_id", "mentorship_requests", ["mentee_id"])
    op.create_index("ix_mentorship_requests_mentor_id", "mentorship_requests", ["mentor_id"])

    # --- mentorship_relationships ---
    op.create_table(
        "mentorship_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=False),
        sa.Column("mentee_id", sa.Integer(), nullable=False),
        sa.Column("goal", sa.String(length=500), nullable=False),
        sa.Column("meeting_frequency", sa.String(length=100), nullable=False),
        sa.Column("session_length_minutes", sa.Integer(), nullable=False),
        sa.Column("status", rel_status, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["mentor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mentorship_relationships_mentor_id", "mentorship_relationships", ["mentor_id"]
    )
    op.create_index(
        "ix_mentorship_relationships_mentee_id", "mentorship_relationships", ["mentee_id"]
    )

    # --- mentorship_sessions ---
    op.create_table(
        "mentorship_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("relationship_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", ses_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["relationship_id"], ["mentorship_relationships.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mentorship_sessions_relationship_id", "mentorship_sessions", ["relationship_id"]
    )

    # --- mentorship_resources ---
    op.create_table(
        "mentorship_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("relationship_id", sa.Integer(), nullable=False),
        sa.Column("shared_by_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["relationship_id"], ["mentorship_relationships.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["shared_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mentorship_resources_relationship_id", "mentorship_resources", ["relationship_id"]
    )
    op.create_index(
        "ix_mentorship_resources_shared_by_id", "mentorship_resources", ["shared_by_id"]
    )


def downgrade() -> None:
    op.drop_table("mentorship_resources")
    op.drop_table("mentorship_sessions")
    op.drop_table("mentorship_relationships")
    op.drop_table("mentorship_requests")
    op.drop_table("mentor_profiles")

    op.execute("DROP TYPE IF EXISTS mentorship_session_status_enum")
    op.execute("DROP TYPE IF EXISTS mentorship_relationship_status_enum")
    op.execute("DROP TYPE IF EXISTS mentorship_request_status_enum")
