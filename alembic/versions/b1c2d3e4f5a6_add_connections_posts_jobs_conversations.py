"""add connections, community_posts, jobs, conversations, messages tables

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-05-09 00:00:00.000000
"""
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    # Use raw SQL throughout so every statement is idempotent.

    # ------------------------------------------------------------------
    # connections
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE connection_status_enum AS ENUM
                ('pending', 'accepted', 'blocked', 'declined');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id          SERIAL PRIMARY KEY,
            requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            receiver_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status       connection_status_enum NOT NULL DEFAULT 'pending',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_connection UNIQUE (requester_id, receiver_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_connections_requester_id ON connections(requester_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_connections_receiver_id  ON connections(receiver_id)")

    # ------------------------------------------------------------------
    # community_posts
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS community_posts (
            id           SERIAL PRIMARY KEY,
            community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
            author_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title        VARCHAR(255) NOT NULL,
            content      TEXT NOT NULL,
            category     VARCHAR(100),
            image_url    VARCHAR(500),
            image_public_id VARCHAR(500),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_community_posts_community_id ON community_posts(community_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_community_posts_author_id    ON community_posts(author_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS post_likes (
            id      SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT uq_post_like UNIQUE (post_id, user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_post_likes_post_id ON post_likes(post_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_post_likes_user_id ON post_likes(user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS post_comments (
            id         SERIAL PRIMARY KEY,
            post_id    INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
            author_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content    TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_post_comments_post_id    ON post_comments(post_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_post_comments_author_id  ON post_comments(author_id)")

    # ------------------------------------------------------------------
    # jobs
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE job_application_status_enum AS ENUM
                ('pending', 'reviewed', 'accepted', 'rejected');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id           SERIAL PRIMARY KEY,
            posted_by    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title        VARCHAR(255) NOT NULL,
            company      VARCHAR(255) NOT NULL,
            location     VARCHAR(255),
            description  TEXT,
            requirements TEXT,
            job_type     VARCHAR(100),
            is_active    BOOLEAN NOT NULL DEFAULT true,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_posted_by ON jobs(posted_by)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS job_applications (
            id           SERIAL PRIMARY KEY,
            job_id       INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            applicant_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            cover_letter TEXT,
            resume_url   VARCHAR(500),
            status       job_application_status_enum NOT NULL DEFAULT 'pending',
            applied_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_job_application UNIQUE (job_id, applicant_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_job_applications_job_id       ON job_applications(job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_job_applications_applicant_id ON job_applications(applicant_id)")

    # ------------------------------------------------------------------
    # conversations / messages
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         SERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS conversation_participants (
            id              SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_conversation_participant UNIQUE (conversation_id, user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversation_participants_conversation_id ON conversation_participants(conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversation_participants_user_id         ON conversation_participants(user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id              SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            sender_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            content         TEXT,
            image_url       VARCHAR(500),
            image_public_id VARCHAR(500),
            is_read         BOOLEAN NOT NULL DEFAULT false,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages(conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_sender_id       ON messages(sender_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversation_participants")
    op.execute("DROP TABLE IF EXISTS conversations")
    op.execute("DROP TABLE IF EXISTS job_applications")
    op.execute("DROP TABLE IF EXISTS jobs")
    op.execute("DROP TYPE IF EXISTS job_application_status_enum")
    op.execute("DROP TABLE IF EXISTS post_comments")
    op.execute("DROP TABLE IF EXISTS post_likes")
    op.execute("DROP TABLE IF EXISTS community_posts")
    op.execute("DROP TABLE IF EXISTS connections")
    op.execute("DROP TYPE IF EXISTS connection_status_enum")
