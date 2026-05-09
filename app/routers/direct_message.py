from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.direct_message_schema import (
    StartConversationRequest,
    MessageCreate,
    MessageResponse,
    ConversationResponse,
)
from app.services.direct_message_service import DirectMessageService

router = APIRouter(prefix="/conversations", tags=["Direct Messages"])


def get_service(db: AsyncSession = Depends(get_db)) -> DirectMessageService:
    return DirectMessageService(db)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    body: StartConversationRequest,
    current_user: User = Depends(get_current_user),
    service: DirectMessageService = Depends(get_service),
):
    conversation = await service.get_or_create_conversation(
        user_id=current_user.id,
        other_user_id=body.other_user_id,
    )
    # Return minimal response — conversations list gives full detail
    return ConversationResponse(
        id=conversation.id,
        other_user_id=body.other_user_id,
        other_user_name="",
        other_user_avatar=None,
        last_message=None,
        last_message_at=None,
        unread_count=0,
        created_at=conversation.created_at,
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    service: DirectMessageService = Depends(get_service),
):
    conversations = await service.get_conversations(user_id=current_user.id)
    return [ConversationResponse(**c) for c in conversations]


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: DirectMessageService = Depends(get_service),
):
    return await service.get_messages(
        conversation_id=conversation_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    service: DirectMessageService = Depends(get_service),
):
    return await service.send_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=body.content,
    )
