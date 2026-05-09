"""add connections, community_posts, jobs, conversations, messages tables

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-05-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # connections
    # ------------------------------------------------------------------
    op.execute(
        "CREATE TYPE connection_status_enum AS ENUM "
        "('pending', 'accepted', 'blocked', 'declined')"
    )
    op.create_table(
        "connections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("requester_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("receiver_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("status",
                  sa.Enum("pending", "accepted", "blocked", "declined",
                          name="connection_status_enum", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("requester_id", "receiver_id", name="uq_connection"),
    )

    # ------------------------------------------------------------------
    # community_posts
    # ------------------------------------------------------------------
    op.create_table(
        "community_posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("community_id", sa.Integer,
                  sa.ForeignKey("communities.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("author_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("image_url", sa.String(500)),
        sa.Column("image_public_id", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    # post_likes
    op.create_table(
        "post_likes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer,
                  sa.ForeignKey("community_posts.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.UniqueConstraint("post_id", "user_id", name="uq_post_like"),
    )

    # post_comments
    op.create_table(
        "post_comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer,
                  sa.ForeignKey("community_posts.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("author_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    # ------------------------------------------------------------------
    # jobs
    # ------------------------------------------------------------------
    op.execute(
        "CREATE TYPE job_application_status_enum AS ENUM "
        "('pending', 'reviewed', 'accepted', 'rejected')"
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("posted_by", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("description", sa.Text),
        sa.Column("requirements", sa.Text),
        sa.Column("job_type", sa.String(100)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "job_applications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer,
                  sa.ForeignKey("jobs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("applicant_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("cover_letter", sa.Text),
        sa.Column("resume_url", sa.String(500)),
        sa.Column("status",
                  sa.Enum("pending", "reviewed", "accepted", "rejected",
                          name="job_application_status_enum", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("applied_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", "applicant_id", name="uq_job_application"),
    )

    # ------------------------------------------------------------------
    # conversations / messages
    # ------------------------------------------------------------------
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.Integer,
                  sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("user_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("joined_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("conversation_id", "user_id",
                            name="uq_conversation_participant"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.Integer,
                  sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("sender_id", sa.Integer,
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("content", sa.Text),
        sa.Column("image_url", sa.String(500)),
        sa.Column("image_public_id", sa.String(500)),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )


def downgrade():
    op.drop_table("messages")
    op.drop_table("conversation_participants")
    op.drop_table("conversations")
    op.drop_table("job_applications")
    op.drop_table("jobs")
    op.execute("DROP TYPE job_application_status_enum")
    op.drop_table("post_comments")
    op.drop_table("post_likes")
    op.drop_table("community_posts")
    op.drop_table("connections")
    op.execute("DROP TYPE connection_status_enum")
