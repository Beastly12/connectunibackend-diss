from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.post_schema import (
    PostCreate,
    PostCommentCreate,
    PostResponse,
    PostCommentResponse,
    LikeToggleResponse,
)
from app.services.post_service import PostService

router = APIRouter(
    prefix="/communities/{community_id}/posts",
    tags=["Community Posts"],
)


def get_service(db: AsyncSession = Depends(get_db)) -> PostService:
    return PostService(db)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    community_id: int,
    body: PostCreate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_service),
):
    data = await service.create_post(
        community_id=community_id,
        author_id=current_user.id,
        title=body.title,
        content=body.content,
        category=body.category,
    )
    return PostResponse(**data)


@router.get("", response_model=list[PostResponse])
async def get_posts(
    community_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_service),
):
    posts = await service.get_posts(
        community_id=community_id,
        requesting_user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return [PostResponse(**p) for p in posts]


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    community_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_service),
):
    await service.delete_post(
        community_id=community_id,
        post_id=post_id,
        user_id=current_user.id,
    )


@router.post("/{post_id}/like", response_model=LikeToggleResponse)
async def toggle_like(
    community_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_service),
):
    result = await service.toggle_like(
        community_id=community_id,
        post_id=post_id,
        user_id=current_user.id,
    )
    return LikeToggleResponse(**result)


@router.post(
    "/{post_id}/comments",
    response_model=PostCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    community_id: int,
    post_id: int,
    body: PostCommentCreate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_service),
):
    data = await service.add_comment(
        community_id=community_id,
        post_id=post_id,
        author_id=current_user.id,
        content=body.content,
    )
    return PostCommentResponse(**data)


@router.get("/{post_id}/comments", response_model=list[PostCommentResponse])
async def get_comments(
    community_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_service),
):
    comments = await service.get_comments(
        community_id=community_id,
        post_id=post_id,
        requesting_user_id=current_user.id,
    )
    return [PostCommentResponse(**c) for c in comments]
