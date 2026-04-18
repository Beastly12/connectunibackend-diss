from pydantic import BaseModel
from datetime import datetime


class ActivityResponse(BaseModel):
    id: int
    activity_type: str
    reference_id: int | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}