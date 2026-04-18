from pydantic import BaseModel

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.services.banned_word_service import BannedWordService

router = APIRouter(prefix="/admin/banned-words", tags=["Moderation"])


class WordRequest(BaseModel):
    word: str


def get_banned_word_service(db: AsyncSession = Depends(get_db)) -> BannedWordService:
    return BannedWordService(db)


@router.get("", response_model=list[str])
async def list_banned_words(
    current_user: User = Depends(get_current_user),
    service: BannedWordService = Depends(get_banned_word_service),
):
    return await service.list_words()


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_banned_word(
    body: WordRequest,
    current_user: User = Depends(get_current_user),
    service: BannedWordService = Depends(get_banned_word_service),
):
    await service.add_word(body.word)
    return {"word": body.word.lower().strip()}


@router.delete("/{word}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_banned_word(
    word: str,
    current_user: User = Depends(get_current_user),
    service: BannedWordService = Depends(get_banned_word_service),
):
    await service.remove_word(word)
