from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.banned_word import BannedWord


class BannedWordRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[str]:
        result = await self.db.execute(select(BannedWord.word))
        return result.scalars().all()

    async def add(self, word: str) -> BannedWord:
        banned = BannedWord(word=word.lower().strip())
        self.db.add(banned)
        await self.db.commit()
        await self.db.refresh(banned)
        return banned

    async def remove(self, word: str) -> bool:
        result = await self.db.execute(
            delete(BannedWord).where(BannedWord.word == word.lower().strip())
        )
        await self.db.commit()
        return result.rowcount > 0
