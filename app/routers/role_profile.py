from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.enums.verification_status import VerificationStatus
from app.models.user import User
from app.schemas.role_profile_schema import (
    AlumniProfileResponse,
    FullProfileResponse,
    MentorshipPreferenceCreate,
    MentorshipPreferenceResponse,
    ProfessionalProfileCreate,
    ProfessionalProfileResponse,
    StudentProfileCreate,
    StudentProfileResponse,
    VerificationUpdateRequest,
)
from app.services.role_profile_service import RoleProfileService

router = APIRouter(prefix="/profile", tags=["Role Profiles"])


def get_service(db: AsyncSession = Depends(get_db)) -> RoleProfileService:
    return RoleProfileService(db)


# ---------------------------------------------------------------------------
# Student profile
# ---------------------------------------------------------------------------

@router.post(
    "/student",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update the authenticated user's student profile",
)
async def save_student_profile(
    body: StudentProfileCreate,
    current_user: User = Depends(get_current_user),
    service: RoleProfileService = Depends(get_service),
):
    return await service.save_student_profile(user=current_user, data=body.model_dump())


# ---------------------------------------------------------------------------
# Alumni profile
# ---------------------------------------------------------------------------

@router.post(
    "/alumni",
    response_model=AlumniProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update the authenticated user's alumni profile",
)
async def save_alumni_profile(
    university_name: Annotated[str, Form()],
    course_completed: Annotated[str, Form()],
    graduation_year: Annotated[int, Form()],
    certificate: Annotated[UploadFile | None, File()] = None,
    current_user: User = Depends(get_current_user),
    service: RoleProfileService = Depends(get_service),
):
    data = {
        "university_name": university_name,
        "course_completed": course_completed,
        "graduation_year": graduation_year,
    }
    return await service.save_alumni_profile(
        user=current_user, data=data, certificate=certificate
    )


# ---------------------------------------------------------------------------
# Professional profile
# ---------------------------------------------------------------------------

@router.post(
    "/professional",
    response_model=ProfessionalProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update the authenticated user's professional profile",
)
async def save_professional_profile(
    body: ProfessionalProfileCreate,
    current_user: User = Depends(get_current_user),
    service: RoleProfileService = Depends(get_service),
):
    return await service.save_professional_profile(
        user=current_user, data=body.model_dump()
    )


# ---------------------------------------------------------------------------
# Mentorship preferences
# ---------------------------------------------------------------------------

@router.post(
    "/mentorship/preferences",
    response_model=MentorshipPreferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or update mentorship preferences for the authenticated user",
)
async def set_mentorship_preferences(
    body: MentorshipPreferenceCreate,
    current_user: User = Depends(get_current_user),
    service: RoleProfileService = Depends(get_service),
):
    return await service.set_mentorship_preferences(
        user=current_user, data=body.model_dump()
    )


# ---------------------------------------------------------------------------
# Full profile
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=FullProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the full profile of the authenticated user",
)
async def get_full_profile(
    current_user: User = Depends(get_current_user),
    service: RoleProfileService = Depends(get_service),
):
    return await service.get_full_profile(user=current_user)


# ---------------------------------------------------------------------------
# Admin: update verification status
# ---------------------------------------------------------------------------

@router.put(
    "/{user_id}/verification",
    status_code=status.HTTP_200_OK,
    summary="Admin: update a user's verification status",
)
async def update_verification_status(
    user_id: int,
    body: VerificationUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: RoleProfileService = Depends(get_service),
):
    user = await service.update_verification_status(
        target_user_id=user_id,
        new_status=body.verification_status,
        admin=current_user,
    )
    return {
        "id": user.id,
        "email": user.email,
        "verification_status": user.verification_status,
    }
