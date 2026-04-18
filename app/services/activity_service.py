from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.activity_type import ActivityType
from app.models.activity import Activity
from app.repositories.activity_repository import ActivityRepository


class ActivityService:

    def __init__(self, db: AsyncSession):
        self.repo = ActivityRepository(db)

    # ------------------------------------------------------------------
    # Logging helpers — one method per action type
    # ------------------------------------------------------------------

    async def log_joined_community(self, user_id: int, community_id: int, community_name: str) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.JOINED_COMMUNITY,
            reference_id=community_id,
            description=f"Joined community: {community_name}",
        )

    async def log_left_community(self, user_id: int, community_id: int, community_name: str) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.LEFT_COMMUNITY,
            reference_id=community_id,
            description=f"Left community: {community_name}",
        )

    async def log_created_post(self, user_id: int, post_id: int, post_title: str) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.CREATED_POST,
            reference_id=post_id,
            description=f"Posted: {post_title}",
        )

    async def log_rsvp(self, user_id: int, event_id: int, event_title: str) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.RSVP_EVENT,
            reference_id=event_id,
            description=f"RSVPd to: {event_title}",
        )

    async def log_cancelled_rsvp(self, user_id: int, event_id: int, event_title: str) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.CANCELLED_RSVP,
            reference_id=event_id,
            description=f"Cancelled RSVP: {event_title}",
        )

    async def log_connected(self, user_id: int, connected_user_id: int, connected_user_name: str) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.CONNECTED_WITH_USER,
            reference_id=connected_user_id,
            description=f"Connected with: {connected_user_name}",
        )

    async def log_mentorship(self, user_id: int, mentorship_id: int, other_user_name: str) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.STARTED_MENTORSHIP,
            reference_id=mentorship_id,
            description=f"Started mentorship with: {other_user_name}",
        )

    async def log_message(self, user_id: int, conversation_id: int) -> None:
        await self._log(
            user_id=user_id,
            activity_type=ActivityType.SENT_MESSAGE,
            reference_id=conversation_id,
            description="Sent a message",
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_recent_activity(self, user_id: int, limit: int = 20) -> list[Activity]:
        return await self.repo.get_recent(user_id=user_id, limit=limit)

    async def get_activity_by_type(
        self,
        user_id: int,
        activity_type: ActivityType,
        limit: int = 20,
    ) -> list[Activity]:
        return await self.repo.get_recent_by_type(
            user_id=user_id,
            activity_type=activity_type,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _log(
        self,
        user_id: int,
        activity_type: ActivityType,
        reference_id: int | None,
        description: str | None,
    ) -> None:
        try:
            await self.repo.log(
                user_id=user_id,
                activity_type=activity_type,
                reference_id=reference_id,
                description=description,
            )
        except Exception:
            pass