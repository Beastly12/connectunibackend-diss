from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.profile import Profile


class ProfileRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int) -> Profile | None:
        result = await self.db.execute(
            select(Profile)
            .options(joinedload(Profile.user))
            .where(Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, **data) -> Profile:
        profile = Profile(user_id=user_id, **data)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete(self, profile: Profile) -> None:
        await self.db.delete(profile)
        await self.db.commit()


    async def update(self, profile: Profile, data: dict) -> Profile:
        # Only set fields that were explicitly provided (partial update)
        for field, value in data.items():
            setattr(profile, field, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile