from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from app.models.notification import Notification
from app.models.community import Community
from app.models.community_message import CommunityMessage
from app.models.user import User


class NotificationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_for_user(self, user_id: int, limit: int = 50) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .options(
                selectinload(Notification.sender).selectinload(User.profile),
            )
            .where(Notification.recipient_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_community_names_by_message_ids(
        self, message_ids: set[int]
    ) -> dict[int, str]:
        """Returns {message_id: community_name} for all given message IDs."""
        result = await self.db.execute(
            select(CommunityMessage.id, Community.name)
            .join(Community, Community.id == CommunityMessage.community_id)
            .where(CommunityMessage.id.in_(message_ids))
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_community_names_by_ids(
        self, community_ids: set[int]
    ) -> dict[int, str]:
        """Returns {community_id: community_name} for all given community IDs."""
        result = await self.db.execute(
            select(Community.id, Community.name)
            .where(Community.id.in_(community_ids))
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_by_id(self, notification_id: int, user_id: int) -> Notification | None:
        result = await self.db.execute(
            select(Notification)
            .options(selectinload(Notification.sender).selectinload(User.profile))
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_unread_count(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                Notification.recipient_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar_one()

    async def mark_one_read(self, notification_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.recipient_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: int) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.recipient_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await self.db.commit()

    async def delete_all(self, user_id: int) -> None:
        await self.db.execute(
            delete(Notification).where(Notification.recipient_id == user_id)
        )
        await self.db.commit()

    async def create(
        self,
        recipient_id: int,
        notification_type: str,
        sender_id: int | None = None,
        reference_id: int | None = None,
    ) -> Notification:
        notification = Notification(
            recipient_id=recipient_id,
            sender_id=sender_id,
            type=notification_type,
            reference_id=reference_id,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification
