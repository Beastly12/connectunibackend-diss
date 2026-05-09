from pydantic import BaseModel
from datetime import datetime


class StartConversationRequest(BaseModel):
    other_user_id: int


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int | None
    content: str | None
    image_url: str | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    other_user_id: int
    other_user_name: str
    other_user_avatar: str | None
    last_message: str | None
    last_message_at: datetime | None
    unread_count: int
    created_at: datetime
