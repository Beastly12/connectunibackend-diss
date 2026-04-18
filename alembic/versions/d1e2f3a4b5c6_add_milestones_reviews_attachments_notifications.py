"""add milestones, reviews, request attachment, new notification types

Revision ID: d1e2f3a4b5c6
Revises: a1b2c3d4e5f6
Create Date: 2026-04-15 00:00:00.000000

Changes:
- new enum type: milestone_status_enum (todo, in_progress, completed)
- new table: mentorship_milestones
- new table: mentorship_reviews
- mentorship_requests: add attachment_file_path column
- notification_type_enum: add 6 new values
  (milestone_completed, session_cancelled, session_reminder,
   resource_shared, relationship_ended, mentee_cancelled_request)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. New enum: milestone_status_enum  (idempotent DO block)
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE milestone_status_enum AS ENUM ('todo', 'in_progress', 'completed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ------------------------------------------------------------------
    # 2. New table: mentorship_milestones
    # ------------------------------------------------------------------
    op.create_table(
        "mentorship_milestones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("relationship_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "todo", "in_progress", "completed",
                name="milestone_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="todo",
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["relationship_id"],
            ["mentorship_relationships.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_mentorship_milestones_relationship_id",
        "mentorship_milestones",
        ["relationship_id"],
        unique=False,
        if_not_exists=True,
    )

    # ------------------------------------------------------------------
    # 3. New table: mentorship_reviews
    # ------------------------------------------------------------------
    op.create_table(
        "mentorship_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("relationship_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("reviewee_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["relationship_id"],
            ["mentorship_relationships.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relationship_id", name="uq_mentorship_reviews_relationship_id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_mentorship_reviews_reviewer_id",
        "mentorship_reviews",
        ["reviewer_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_mentorship_reviews_reviewee_id",
        "mentorship_reviews",
        ["reviewee_id"],
        unique=False,
        if_not_exists=True,
    )

    # ------------------------------------------------------------------
    # 4. Add attachment_file_path to mentorship_requests
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE mentorship_requests
            ADD COLUMN IF NOT EXISTS attachment_file_path VARCHAR(500)
    """)

    # ------------------------------------------------------------------
    # 5. Extend notification_type_enum with 6 new values
    #    ALTER TYPE ADD VALUE IF NOT EXISTS requires PostgreSQL 9.6+
    #    and works inside a transaction in PostgreSQL 12+.
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'milestone_completed'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'session_cancelled'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'session_reminder'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'resource_shared'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'relationship_ended'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'mentee_cancelled_request'"
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Reverse in opposite order
    # ------------------------------------------------------------------

    # Note: PostgreSQL does not support removing values from an ENUM type.
    # To fully downgrade the notification enum, the column would need to be
    # rewritten — skipped here for the dissertation scope.

    # Remove attachment column
    op.execute("""
        ALTER TABLE mentorship_requests
            DROP COLUMN IF EXISTS attachment_file_path
    """)

    # Drop review table
    op.drop_index("ix_mentorship_reviews_reviewee_id", table_name="mentorship_reviews")
    op.drop_index("ix_mentorship_reviews_reviewer_id", table_name="mentorship_reviews")
    op.drop_table("mentorship_reviews")

    # Drop milestone table
    op.drop_index(
        "ix_mentorship_milestones_relationship_id",
        table_name="mentorship_milestones",
    )
    op.drop_table("mentorship_milestones")

    # Drop milestone enum
    op.execute("DROP TYPE IF EXISTS milestone_status_enum")