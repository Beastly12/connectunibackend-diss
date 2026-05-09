from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.enums.notification_type import NotificationType
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.direct_message_repository import DirectMessageRepository
from app.services.activity_service import ActivityService
from app.services.notification_service import NotificationService


class DirectMessageService:

    def __init__(self, db: AsyncSession):
        self.repo = DirectMessageRepository(db)
        self.activity = ActivityService(db)
        self.notifications = NotificationService(db)

    async def get_or_create_conversation(
        self, user_id: int, other_user_id: int
    ) -> Conversation:
        if user_id == other_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start a conversation with yourself.",
            )
        if not await self.repo.has_active_mentorship(user_id, other_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private messaging is only available between users with an active mentorship relationship.",
            )
        conversation, _ = await self.repo.get_or_create_conversation(user_id, other_user_id)
        return conversation

    async def get_conversations(self, user_id: int) -> list[dict]:
        rows = await self.repo.get_conversations_for_user(user_id)
        result = []
        for conversation, last_msg, unread_count in rows:
            other = next(
                (p for p in conversation.participants if p.user_id != user_id), None
            )
            if not other or not other.user:
                continue
            other_user = other.user
            avatar = (
                other_user.profile.avatar_url
                if other_user.profile
                else None
            )
            result.append({
                "id": conversation.id,
                "other_user_id": other_user.id,
                "other_user_name": other_user.full_name,
                "other_user_avatar": avatar,
                "last_message": last_msg.content if last_msg else None,
                "last_message_at": last_msg.created_at if last_msg else None,
                "unread_count": unread_count,
                "created_at": conversation.created_at,
            })
        return result

    async def get_messages(
        self, conversation_id: int, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Message]:
        if not await self.repo.is_participant(conversation_id, user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        messages = await self.repo.get_messages(conversation_id, limit=limit, offset=offset)
        await self.repo.mark_conversation_read(conversation_id, user_id)
        # Return in chronological order
        return list(reversed(messages))

    async def send_message(
        self, conversation_id: int, sender_id: int, content: str
    ) -> Message:
        if not await self.repo.is_participant(conversation_id, sender_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        message = await self.repo.send_message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
        )
        # Notify the other participant(s)
        conv = await self.repo.get_conversation(conversation_id)
        if conv:
            for p in conv.participants:
                if p.user_id != sender_id:
                    try:
                        await self.notifications.send(
                            recipient_id=p.user_id,
                            notification_type=NotificationType.MESSAGE,
                            sender_id=sender_id,
                            reference_id=conversation_id,
                        )
                    except Exception:
                        pass
        try:
            await self.activity.log_message(
                user_id=sender_id,
                conversation_id=conversation_id,
            )
        except Exception:
            pass
        return message
