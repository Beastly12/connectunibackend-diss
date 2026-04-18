from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.banned_word_repository import BannedWordRepository


class BannedWordService:

    def __init__(self, db: AsyncSession):
        self.repo = BannedWordRepository(db)

    async def check(self, text: str) -> str | None:
        """Returns the first banned word found in text, or None if clean."""
        words = await self.repo.get_all()
        text_lower = text.lower()
        for word in words:
            if word in text_lower:
                return word
        return None

    async def is_clean(self, text: str) -> bool:
        return await self.check(text) is None

    async def add_word(self, word: str) -> None:
        try:
            await self.repo.add(word)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{word.lower().strip()}' is already in the banned words list.",
            )

    async def remove_word(self, word: str) -> bool:
        removed = await self.repo.remove(word)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"'{word.lower().strip()}' is not in the banned words list.",
            )
        return removed

    async def list_words(self) -> list[str]:
        return await self.repo.get_all()
