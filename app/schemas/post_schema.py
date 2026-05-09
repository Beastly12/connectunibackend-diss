from pydantic import BaseModel
from datetime import datetime


class PostCreate(BaseModel):
    title: str
    content: str
    category: str | None = None


class PostCommentCreate(BaseModel):
    content: str


class PostResponse(BaseModel):
    id: int
    community_id: int
    author_id: int
    author_name: str
    title: str
    content: str
    category: str | None
    image_url: str | None
    like_count: int
    comment_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PostCommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LikeToggleResponse(BaseModel):
    liked: bool
    like_count: int
