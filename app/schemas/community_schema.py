from pydantic import BaseModel, Field
from datetime import datetime

from app.enums.community_type import CommunityType
from app.enums.community_role import CommunityRole


class CommunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    type: CommunityType
    university: str | None = None
    is_private: bool = False


class CommunityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_private: bool | None = None


class CommunityResponse(BaseModel):
    id: int
    name: str
    description: str | None
    type: str
    university: str | None
    is_private: bool
    is_active: bool
    cover_image_url: str | None
    creator_id: int | None
    member_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    user_id: int
    full_name: str
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class RoleUpdateRequest(BaseModel):
    role: CommunityRole


class InviteResponse(BaseModel):
    id: int
    token: str
    community_id: int
    created_by: int
    use_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
