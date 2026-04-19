from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.services.profile_service import ProfileService
from app.services.role_profile_service import RoleProfileService
from app.schemas.profile_dto import (
    ProfileUpdateDto,
    ProfileResponse,
    ProfileCompletionResponse,
)
from app.schemas.role_profile_schema import FullProfileResponse

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(db)


def get_role_profile_service(db: AsyncSession = Depends(get_db)) -> RoleProfileService:
    return RoleProfileService(db)


# /me/completion must be declared before /{user_id} to avoid route shadowing
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


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete the authenticated user's profile",
)
async def delete_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    await service.delete_profile(user_id=current_user.id)


@router.get(
    "/{user_id}",
    response_model=FullProfileResponse,
    summary="Get any user's full profile by their ID (public)",
)
async def get_profile(
    user_id: int,
    service: RoleProfileService = Depends(get_role_profile_service),
):
    return await service.get_full_profile_by_user_id(user_id)
