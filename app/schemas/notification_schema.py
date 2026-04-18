from pydantic import BaseModel
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    type: str
    sender_id: int | None
    sender_name: str | None
    sender_avatar: str | None
    reference_id: int | None
    body: str
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    unread_count: int
