from pydantic import BaseModel
from datetime import datetime


class ConnectionResponse(BaseModel):
    id: int
    requester_id: int
    requester_name: str | None = None
    receiver_id: int
    receiver_name: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
