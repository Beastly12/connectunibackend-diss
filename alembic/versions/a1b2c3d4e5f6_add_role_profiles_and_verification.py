"""add role profiles and verification status

Revision ID: a1b2c3d4e5f6
Revises: 52c1c77c3a72
Create Date: 2026-04-08 00:00:00.000000

Changes:
- users: add verification_status column (new verification_status_enum type)
- new enum type: preferred_format_enum
- new tables: student_profiles, alumni_profiles, professional_profiles,
              mentorship_preferences
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '52c1c77c3a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. New enum: verification_status_enum  (idempotent DO block)
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE verification_status_enum
                AS ENUM ('verified', 'pending', 'unverified', 'self_declared');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ------------------------------------------------------------------
    # 2. Add verification_status to users  (IF NOT EXISTS — idempotent)
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS verification_status
                verification_status_enum NOT NULL DEFAULT 'unverified'
    """)

    # ------------------------------------------------------------------
    # 3. New enum: preferred_format_enum  (idempotent DO block)
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE preferred_format_enum
                AS ENUM ('chat', 'video', 'in_person');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ------------------------------------------------------------------
    # 4. student_profiles
    # ------------------------------------------------------------------
    op.create_table(
        'student_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('university_name', sa.String(length=255), nullable=False),
        sa.Column('course_title', sa.String(length=255), nullable=False),
        sa.Column('year_of_study', sa.Integer(), nullable=False),
        sa.Column('expected_graduation', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        if_not_exists=True,
    )
    op.create_index('ix_student_profiles_user_id', 'student_profiles',
                    ['user_id'], unique=False,
                    if_not_exists=True)

    # ------------------------------------------------------------------
    # 5. alumni_profiles
    # ------------------------------------------------------------------
    op.create_table(
        'alumni_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('university_name', sa.String(length=255), nullable=False),
        sa.Column('course_completed', sa.String(length=255), nullable=False),
        sa.Column('graduation_year', sa.Integer(), nullable=False),
        sa.Column('certificate_url', sa.String(length=1000), nullable=True),
        sa.Column('certificate_public_id', sa.String(length=500), nullable=True),
        sa.Column('certificate_uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        if_not_exists=True,
    )
    op.create_index('ix_alumni_profiles_user_id', 'alumni_profiles',
                    ['user_id'], unique=False,
                    if_not_exists=True)

    # ------------------------------------------------------------------
    # 6. professional_profiles
    # ------------------------------------------------------------------
    op.create_table(
        'professional_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('industry_sector', sa.String(length=255), nullable=False),
        sa.Column('years_of_experience', sa.Integer(), nullable=False),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        if_not_exists=True,
    )
    op.create_index('ix_professional_profiles_user_id', 'professional_profiles',
                    ['user_id'], unique=False,
                    if_not_exists=True)

    # ------------------------------------------------------------------
    # 7. mentorship_preferences
    #    Use PgEnum(..., create_type=False) — type already created above.
    # ------------------------------------------------------------------
    op.create_table(
        'mentorship_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_mentor', sa.Boolean(), nullable=False,
                  server_default='false'),
        sa.Column('is_mentee', sa.Boolean(), nullable=False,
                  server_default='false'),
        sa.Column('areas_of_interest', sa.JSON(), nullable=False,
                  server_default='[]'),
        sa.Column('availability_hours_per_week', sa.Integer(), nullable=False),
        sa.Column(
            'preferred_format',
            # create_type=False: enum type was already created above
            PgEnum('chat', 'video', 'in_person',
                   name='preferred_format_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        if_not_exists=True,
    )
    op.create_index('ix_mentorship_preferences_user_id', 'mentorship_preferences',
                    ['user_id'], unique=False,
                    if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_mentorship_preferences_user_id',
                  table_name='mentorship_preferences')
    op.drop_table('mentorship_preferences')

    op.drop_index('ix_professional_profiles_user_id',
                  table_name='professional_profiles')
    op.drop_table('professional_profiles')

    op.drop_index('ix_alumni_profiles_user_id', table_name='alumni_profiles')
    op.drop_table('alumni_profiles')

    op.drop_index('ix_student_profiles_user_id', table_name='student_profiles')
    op.drop_table('student_profiles')

    op.execute("DROP TYPE IF EXISTS preferred_format_enum")

    op.drop_column('users', 'verification_status')

    op.execute("DROP TYPE IF EXISTS verification_status_enum")
