from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.mentorship_relationship import MentorshipRelationship
from app.models.message import Message
from app.models.user import User
from app.models.profile import Profile
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus


class DirectMessageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_conversation(
        self, user_a: int, user_b: int
    ) -> tuple[Conversation, bool]:
        """Return (conversation, was_created). Finds or creates a 1-1 conversation."""
        sub_a = (
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.user_id == user_a)
            .scalar_subquery()
        )
        sub_b = (
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.user_id == user_b)
            .scalar_subquery()
        )
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.id.in_(sub_a),
                Conversation.id.in_(sub_b),
            )
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

        conversation = Conversation()
        self.db.add(conversation)
        await self.db.flush()

        self.db.add(ConversationParticipant(conversation_id=conversation.id, user_id=user_a))
        self.db.add(ConversationParticipant(conversation_id=conversation.id, user_id=user_b))
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation, True

    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.participants)
                .joinedload(ConversationParticipant.user)
            )
        )
        return result.scalar_one_or_none()

    async def get_conversations_for_user(
        self, user_id: int
    ) -> list[tuple[Conversation, Message | None, int]]:
        """Return list of (conversation, last_message, unread_count)."""
        conv_ids_q = (
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.user_id == user_id)
        )
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id.in_(conv_ids_q))
            .options(
                selectinload(Conversation.participants)
                .selectinload(ConversationParticipant.user)
                .selectinload(User.profile)
            )
            .order_by(Conversation.created_at.desc())
        )
        conversations = list(result.scalars().all())
        if not conversations:
            return []

        conv_id_list = [c.id for c in conversations]

        # Batch: last message per conversation
        subq = (
            select(
                Message.conversation_id,
                func.max(Message.id).label("max_id"),
            )
            .where(Message.conversation_id.in_(conv_id_list))
            .group_by(Message.conversation_id)
            .subquery()
        )
        last_msg_result = await self.db.execute(
            select(Message).join(subq, Message.id == subq.c.max_id)
        )
        last_msgs: dict[int, Message] = {
            m.conversation_id: m for m in last_msg_result.scalars().all()
        }

        # Batch: unread counts
        unread_result = await self.db.execute(
            select(
                Message.conversation_id,
                func.count().label("cnt"),
            )
            .where(
                Message.conversation_id.in_(conv_id_list),
                Message.sender_id != user_id,
                Message.is_read == False,
            )
            .group_by(Message.conversation_id)
        )
        unread_counts: dict[int, int] = {
            row.conversation_id: row.cnt for row in unread_result
        }

        return [
            (conv, last_msgs.get(conv.id), unread_counts.get(conv.id, 0))
            for conv in conversations
        ]

    async def send_message(
        self, conversation_id: int, sender_id: int, content: str
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(
        self, conversation_id: int, limit: int = 50, offset: int = 0
    ) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_unread(self, conversation_id: int, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.is_read == False,
            )
        )
        return result.scalar_one()

    async def mark_conversation_read(self, conversation_id: int, user_id: int) -> None:
        await self.db.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.is_read == False,
            )
            .values(is_read=True)
        )
        await self.db.commit()

    async def has_active_mentorship(self, user_a: int, user_b: int) -> bool:
        """True if the two users share an active mentorship relationship (either direction)."""
        result = await self.db.execute(
            select(MentorshipRelationship).where(
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
                or_(
                    and_(
                        MentorshipRelationship.mentor_id == user_a,
                        MentorshipRelationship.mentee_id == user_b,
                    ),
                    and_(
                        MentorshipRelationship.mentor_id == user_b,
                        MentorshipRelationship.mentee_id == user_a,
                    ),
                ),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def is_participant(self, conversation_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None
