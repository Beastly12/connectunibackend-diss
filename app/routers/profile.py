from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.services.profile_service import ProfileService
from app.schemas.profile_dto import (
    ProfileCreateDto,
    ProfileUpdateDto,
    ProfileResponse,
    ProfileCompletionResponse,
)

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(db)


@router.post(
    "/",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a profile for the authenticated user",
)
async def create_profile(
    body: ProfileCreateDto,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.create_profile(user_id=current_user.id, data=body.model_dump())


@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Get the authenticated user's own profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_profile(user_id=current_user.id)


@router.get(
    "/{user_id}",
    response_model=ProfileResponse,
    summary="Get any user's profile by their ID",
)
async def get_profile(
    user_id: int,
    service: ProfileService = Depends(get_profile_service),
):
    # Public endpoint — no auth required to view other profiles
    return await service.get_profile(user_id=user_id)


@router.patch(
    "/me",
    response_model=ProfileResponse,
    summary="Update the authenticated user's profile",
)
async def update_profile(
    body: ProfileUpdateDto,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.update_profile(user_id=current_user.id, data=body.model_dump())


@router.put(
    "/me/avatar",
    response_model=ProfileResponse,
    summary="Upload or replace the authenticated user's avatar",
)
async def update_avatar(
    file: UploadFile = File(..., description="Image file — JPEG, PNG, WebP or GIF, max 5MB"),
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.update_avatar(user_id=current_user.id, file=file)


@router.get(
    "/me/completion",
    response_model=ProfileCompletionResponse,
    summary="Get profile completion percentage and missing fields",
)
async def get_completion(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_completion(user_id=current_user.id)

@router.delete(
    "/me/completion",
    response_model=ProfileCompletionResponse, summary="Delete profile completion percentage and missing fields", )
async def delete_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.delete_profile(user_id=current_user.id)