from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Any


class SenderSummary(BaseModel):
    id: int
    full_name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_avatar(cls, data: Any) -> Any:
        if not isinstance(data, dict) and hasattr(data, "profile") and data.profile is not None:
            data.avatar_url = data.profile.avatar_url
        return data


class AttachmentResponse(BaseModel):
    id: int
    file_url: str
    file_name: str | None
    file_type: str | None

    model_config = {"from_attributes": True}


class ReactionSummary(BaseModel):
    emoji: str
    count: int
    reacted_by_me: bool


class MessageReplyResponse(BaseModel):
    id: int
    sender_id: int | None
    sender: SenderSummary | None = None
    content: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommunityMessageResponse(BaseModel):
    id: int
    community_id: int
    sender_id: int | None
    sender: SenderSummary | None
    content: str | None
    reply_to_id: int | None
    reply_to: MessageReplyResponse | None
    attachments: list[AttachmentResponse]
    reactions: list[ReactionSummary]
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str | None = None
    reply_to_id: int | None = None


class ToggleReactionRequest(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=10)
