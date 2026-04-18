from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.notification_type import NotificationType
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification_schema import NotificationResponse
from app.services.websocket_manager import ws_manager

_MESSAGE_TYPES = {
    NotificationType.COMMUNITY_MESSAGE,
    NotificationType.MESSAGE_REPLY,
    NotificationType.MESSAGE_REACTION,
}


def _build_body(
    notification_type: str,
    sender_name: str | None,
    community_name: str | None,
) -> str:
    name = sender_name or "Someone"
    community = f" in {community_name}" if community_name else ""
    bodies = {
        NotificationType.COMMUNITY_MESSAGE: f"{name} sent a message{community}",
        NotificationType.MESSAGE_REPLY:      f"{name} replied to your message{community}",
        NotificationType.MESSAGE_REACTION:   f"{name} reacted to your message{community}",
        NotificationType.COMMUNITY_ADDED:    f"{name} added you to {community_name or 'a community'}",
        NotificationType.MENTORSHIP_REQUEST: f"{name} sent you a mentorship request",
        NotificationType.MENTORSHIP_ACCEPTED:f"{name} accepted your mentorship request",
        NotificationType.MENTORSHIP_REJECTED:f"{name} declined your mentorship request",
        NotificationType.CONNECTION_REQUEST: f"{name} sent you a connection request",
        NotificationType.CONNECTION_ACCEPTED:f"{name} accepted your connection request",
        NotificationType.POST_LIKE:          f"{name} liked your post",
        NotificationType.POST_COMMENT:       f"{name} commented on your post",
        NotificationType.EVENT_REMINDER:     "You have an upcoming event",
        NotificationType.JOB_APPLICATION:    f"{name} applied to your job posting",
        NotificationType.MESSAGE:            f"{name} sent you a message",
        NotificationType.MESSAGE_REACTION:   f"{name} reacted to your message{community}",
        NotificationType.MILESTONE_COMPLETED:    f"{name} completed a milestone",
        NotificationType.SESSION_CANCELLED:      f"{name} cancelled a scheduled session",
        NotificationType.SESSION_REMINDER:       "You have an upcoming mentorship session",
        NotificationType.RESOURCE_SHARED:        f"{name} shared a resource with you",
        NotificationType.RELATIONSHIP_ENDED:     f"{name} ended your mentorship relationship",
        NotificationType.MENTEE_CANCELLED_REQUEST: f"{name} cancelled their mentorship request",
    }
    return bodies.get(notification_type, "You have a new notification")


class NotificationService:

    def __init__(self, db: AsyncSession):
        self.repo = NotificationRepository(db)

    async def get_notifications(self, user_id: int, limit: int = 50) -> list[NotificationResponse]:
        notifications = await self.repo.get_for_user(user_id=user_id, limit=limit)

        # Batch-load community names — two sources depending on type
        message_ids = {
            n.reference_id for n in notifications
            if n.type in _MESSAGE_TYPES and n.reference_id
        }
        direct_community_ids = {
            n.reference_id for n in notifications
            if n.type == NotificationType.COMMUNITY_ADDED and n.reference_id
        }

        msg_to_community: dict[int, str] = {}
        if message_ids:
            msg_to_community = await self.repo.get_community_names_by_message_ids(message_ids)

        community_names: dict[int, str] = {}
        if direct_community_ids:
            community_names = await self.repo.get_community_names_by_ids(direct_community_ids)

        result = []
        for n in notifications:
            sender_name = n.sender.full_name if n.sender else None
            sender_avatar = (
                n.sender.profile.avatar_url
                if n.sender and n.sender.profile
                else None
            )

            if n.type in _MESSAGE_TYPES and n.reference_id:
                community_name = msg_to_community.get(n.reference_id)
            elif n.type == NotificationType.COMMUNITY_ADDED and n.reference_id:
                community_name = community_names.get(n.reference_id)
            else:
                community_name = None

            result.append(NotificationResponse(
                id=n.id,
                type=n.type,
                sender_id=n.sender_id,
                sender_name=sender_name,
                sender_avatar=sender_avatar,
                reference_id=n.reference_id,
                body=_build_body(n.type, sender_name, community_name),
                is_read=n.is_read,
                created_at=n.created_at,
            ))

        return result

    async def get_notification(self, notification_id: int, user_id: int) -> NotificationResponse | None:
        n = await self.repo.get_by_id(notification_id=notification_id, user_id=user_id)
        if not n:
            return None

        sender_name = n.sender.full_name if n.sender else None
        sender_avatar = n.sender.profile.avatar_url if n.sender and n.sender.profile else None

        community_name = None
        if n.type in _MESSAGE_TYPES and n.reference_id:
            names = await self.repo.get_community_names_by_message_ids({n.reference_id})
            community_name = names.get(n.reference_id)
        elif n.type == NotificationType.COMMUNITY_ADDED and n.reference_id:
            names = await self.repo.get_community_names_by_ids({n.reference_id})
            community_name = names.get(n.reference_id)

        return NotificationResponse(
            id=n.id,
            type=n.type,
            sender_id=n.sender_id,
            sender_name=sender_name,
            sender_avatar=sender_avatar,
            reference_id=n.reference_id,
            body=_build_body(n.type, sender_name, community_name),
            is_read=n.is_read,
            created_at=n.created_at,
        )

    async def get_unread_count(self, user_id: int) -> int:
        return await self.repo.get_unread_count(user_id=user_id)

    async def mark_one_as_read(self, notification_id: int, user_id: int) -> bool:
        return await self.repo.mark_one_read(notification_id=notification_id, user_id=user_id)

    async def mark_all_as_read(self, user_id: int) -> None:
        await self.repo.mark_all_read(user_id=user_id)

    async def delete_all(self, user_id: int) -> None:
        await self.repo.delete_all(user_id=user_id)

    async def send(
        self,
        recipient_id: int,
        notification_type: NotificationType,
        sender_id: int | None = None,
        reference_id: int | None = None,
    ) -> Notification:
        notification = await self.repo.create(
            recipient_id=recipient_id,
            notification_type=notification_type,
            sender_id=sender_id,
            reference_id=reference_id,
        )
        await ws_manager.send_to_user(
            recipient_id,
            {
                "event": "notification",
                "data": {
                    "id": notification.id,
                    "type": notification.type,
                    "sender_id": notification.sender_id,
                    "reference_id": notification.reference_id,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )
        return notification
