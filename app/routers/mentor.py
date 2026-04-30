from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.mentorship_schema import (
    MentorProfileResponse,
    MentorshipRequestResponse,
)
from app.services.mentorship_service import MentorshipService

router = APIRouter(prefix="/mentors", tags=["Mentors"])


class LegacyMentorshipRequestCreate(BaseModel):
    goal: str = Field(default="Career guidance", min_length=1, max_length=500)
    meeting_frequency: str = Field(default="Monthly", min_length=1, max_length=100)
    session_length_minutes: int = Field(default=60, ge=15)
    message: str = Field(default="I would like to request mentorship.", min_length=1)


def get_mentorship_service(db: AsyncSession = Depends(get_db)) -> MentorshipService:
    return MentorshipService(db)


@router.get("", response_model=list[MentorProfileResponse])
async def list_mentors(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Backward-compatible alias for GET /mentorship/mentors."""
    return await service.list_mentors(current_user=current_user)


@router.get("/{user_id}", response_model=MentorProfileResponse)
async def get_mentor(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Backward-compatible alias for GET /mentorship/mentors/{user_id}."""
    return await service.get_mentor_profile_by_user_id(user_id)


@router.post(
    "/{mentor_id}/request",
    response_model=MentorshipRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_mentorship_request(
    mentor_id: int,
    body: LegacyMentorshipRequestCreate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Backward-compatible JSON alias for POST /mentorship/requests."""
    data = body.model_dump()
    data["mentor_id"] = mentor_id
    return await service.send_request(
        mentee_id=current_user.id,
        data=data,
        attachment=None,
    )
