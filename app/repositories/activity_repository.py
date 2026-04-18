from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.activity import Activity
from app.enums.activity_type import ActivityType


class ActivityRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        user_id: int,
        activity_type: ActivityType,
        reference_id: int | None = None,
        description: str | None = None,
    ) -> Activity:
        activity = Activity(
            user_id=user_id,
            activity_type=activity_type,
            reference_id=reference_id,
            description=description,
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def get_recent(self, user_id: int, limit: int = 20) -> list[Activity]:
        result = await self.db.execute(
            select(Activity)
            .where(Activity.user_id == user_id)
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_by_type(
        self,
        user_id: int,
        activity_type: ActivityType,
        limit: int = 20,
    ) -> list[Activity]:
        result = await self.db.execute(
            select(Activity)
            .where(
                Activity.user_id == user_id,
                Activity.activity_type == activity_type,
            )
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()