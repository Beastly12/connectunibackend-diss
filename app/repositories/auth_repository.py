from datetime import datetime
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.refresh_token import RefreshToken


class AuthRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def save_refresh_token(
            self, user_id: int, token_hash: str, expires_at: datetime
    ) -> None:
        self.db.add(RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        ))
        await self.db.commit()
