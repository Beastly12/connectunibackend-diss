from fastapi import APIRouter, Depends, Form, Query, UploadFile, File, status
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.community_message_schema import (
    CommunityMessageResponse,
    ReactionSummary,
    ToggleReactionRequest,
)
from app.services.community_message_service import CommunityMessageService

router = APIRouter(
    prefix="/communities/{community_id}/messages",
    tags=["Community Messages"],
)


def get_message_service(db: AsyncSession = Depends(get_db)) -> CommunityMessageService:
    return CommunityMessageService(db)


@router.get("", response_model=list[CommunityMessageResponse])
async def get_messages(
    community_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: CommunityMessageService = Depends(get_message_service),
):
    return await service.get_messages(
        community_id=community_id,
        requesting_user_id=current_user.id,
        page=page,
        limit=limit,
    )


@router.post("", response_model=CommunityMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    community_id: int,
    content: Annotated[str | None, Form()] = None,
    reply_to_id: Annotated[int | None, Form()] = None,
    files: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    service: CommunityMessageService = Depends(get_message_service),
):
    return await service.send_message(
        community_id=community_id,
        sender_id=current_user.id,
        content=content,
        reply_to_id=reply_to_id,
        files=files,
    )


@router.post(
    "/{message_id}/reactions",
    response_model=list[ReactionSummary],
)
async def toggle_reaction(
    community_id: int,
    message_id: int,
    body: ToggleReactionRequest,
    current_user: User = Depends(get_current_user),
    service: CommunityMessageService = Depends(get_message_service),
):
    return await service.toggle_reaction(
        community_id=community_id,
        message_id=message_id,
        emoji=body.emoji,
        user_id=current_user.id,
    )
