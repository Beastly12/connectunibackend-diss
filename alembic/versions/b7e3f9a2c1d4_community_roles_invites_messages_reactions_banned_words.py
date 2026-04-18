"""community roles, invites, messages, reactions, banned words

Revision ID: b7e3f9a2c1d4
Revises: 36223ec74ca3
Create Date: 2026-03-26 00:00:00.000000

Changes:
- communities: add is_private, creator_id
- community_members: add role column (new community_role_enum type)
- new tables: community_invites, community_messages,
              community_message_attachments, community_message_reactions,
              banned_words
- notification_type_enum: add community_added, community_message,
                          message_reply, message_reaction values
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7e3f9a2c1d4'
down_revision: Union[str, None] = '36223ec74ca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. New enum type: community_role_enum
    # ------------------------------------------------------------------
    community_role_enum = sa.Enum(
        'admin', 'moderator', 'member',
        name='community_role_enum',
    )
    community_role_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # 2. Alter existing tables
    # ------------------------------------------------------------------

    # communities — add is_private and creator_id
    op.add_column(
        'communities',
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'communities',
        sa.Column('creator_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_communities_creator_id',
        'communities', 'users',
        ['creator_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_communities_creator_id', 'communities', ['creator_id'])

    # community_members — add role (default to 'member')
    op.add_column(
        'community_members',
        sa.Column(
            'role',
            sa.Enum('admin', 'moderator', 'member', name='community_role_enum'),
            nullable=False,
            server_default='member',
        ),
    )

    # ------------------------------------------------------------------
    # 3. New tables
    # ------------------------------------------------------------------

    op.create_table(
        'community_invites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('community_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('token', name='uq_community_invite_token'),
    )
    op.create_index('ix_community_invites_community_id', 'community_invites', ['community_id'])
    op.create_index('ix_community_invites_token', 'community_invites', ['token'])

    op.create_table(
        'community_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('community_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('reply_to_id', sa.Integer(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reply_to_id'], ['community_messages.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_community_messages_community_id', 'community_messages', ['community_id'])
    op.create_index('ix_community_messages_sender_id', 'community_messages', ['sender_id'])

    op.create_table(
        'community_message_attachments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=False),
        sa.Column('file_public_id', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_type', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ['message_id'], ['community_messages.id'], ondelete='CASCADE'
        ),
    )
    op.create_index(
        'ix_community_message_attachments_message_id',
        'community_message_attachments',
        ['message_id'],
    )

    op.create_table(
        'community_message_reactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('emoji', sa.String(length=10), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['message_id'], ['community_messages.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'message_id', 'user_id', 'emoji', name='uq_community_msg_reaction'
        ),
    )
    op.create_index(
        'ix_community_message_reactions_message_id',
        'community_message_reactions',
        ['message_id'],
    )
    op.create_index(
        'ix_community_message_reactions_user_id',
        'community_message_reactions',
        ['user_id'],
    )

    op.create_table(
        'banned_words',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.UniqueConstraint('word', name='uq_banned_word'),
    )
    op.create_index('ix_banned_words_word', 'banned_words', ['word'])

    # ------------------------------------------------------------------
    # 4. Extend notification_type_enum with new values
    #    (PostgreSQL: ADD VALUE cannot run inside a transaction,
    #     Alembic handles this via execution_options)
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'community_added'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'community_message'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'message_reply'"
    )
    op.execute(
        "ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'message_reaction'"
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Drop new tables (reverse order of creation)
    # ------------------------------------------------------------------
    op.drop_index('ix_banned_words_word', table_name='banned_words')
    op.drop_table('banned_words')

    op.drop_index(
        'ix_community_message_reactions_user_id',
        table_name='community_message_reactions',
    )
    op.drop_index(
        'ix_community_message_reactions_message_id',
        table_name='community_message_reactions',
    )
    op.drop_table('community_message_reactions')

    op.drop_index(
        'ix_community_message_attachments_message_id',
        table_name='community_message_attachments',
    )
    op.drop_table('community_message_attachments')

    op.drop_index('ix_community_messages_sender_id', table_name='community_messages')
    op.drop_index('ix_community_messages_community_id', table_name='community_messages')
    op.drop_table('community_messages')

    op.drop_index('ix_community_invites_token', table_name='community_invites')
    op.drop_index('ix_community_invites_community_id', table_name='community_invites')
    op.drop_table('community_invites')

    # ------------------------------------------------------------------
    # Revert community_members and communities changes
    # ------------------------------------------------------------------
    op.drop_column('community_members', 'role')

    op.drop_index('ix_communities_creator_id', table_name='communities')
    op.drop_constraint('fk_communities_creator_id', 'communities', type_='foreignkey')
    op.drop_column('communities', 'creator_id')
    op.drop_column('communities', 'is_private')

    # Drop the community_role_enum type
    sa.Enum(name='community_role_enum').drop(op.get_bind(), checkfirst=True)

    # NOTE: PostgreSQL does not support removing values from an enum type.
    # The notification_type_enum additions (community_added, community_message,
    # message_reply, message_reaction) cannot be automatically rolled back.
    # To fully revert, recreate the enum without these values manually.
