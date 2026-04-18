from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.mentorship_schema import (
    MentorProfileCreate,
    MentorProfileResponse,
    MentorProfileUpdate,
    MentorRatingResponse,
    MentorshipRelationshipResponse,
    MentorshipRequestCreate,
    MentorshipRequestResponse,
    MentorshipResourceCreate,
    MentorshipResourceResponse,
    MentorshipSessionCreate,
    MentorshipSessionResponse,
    MentorshipSessionUpdate,
    MentorshipStatsResponse,
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    MyMenteeResponse,
    MyMentorResponse,
    ReviewCreate,
    ReviewResponse,
)
from app.services.mentorship_service import MentorshipService

router = APIRouter(prefix="/mentorship", tags=["Mentorship"])


def get_mentorship_service(db: AsyncSession = Depends(get_db)) -> MentorshipService:
    return MentorshipService(db)


# ------------------------------------------------------------------
# Mentor Profile
# ------------------------------------------------------------------

@router.post(
    "/become-mentor",
    response_model=MentorProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a mentor profile for the authenticated user",
)
async def become_mentor(
    body: MentorProfileCreate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Register the authenticated user as a mentor."""
    return await service.become_mentor(user_id=current_user.id, data=body.model_dump())


@router.get(
    "/mentor-profile/me",
    response_model=MentorProfileResponse,
    summary="Get the authenticated user's mentor profile",
)
async def get_my_mentor_profile(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Retrieve the authenticated user's own mentor profile including ratings."""
    return await service.get_my_mentor_profile(current_user.id)


@router.patch(
    "/mentor-profile/me",
    response_model=MentorProfileResponse,
    summary="Update the authenticated user's mentor profile",
)
async def update_my_mentor_profile(
    body: MentorProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Update the authenticated user's mentor profile fields."""
    return await service.update_mentor_profile(
        user_id=current_user.id,
        data=body.model_dump(exclude_unset=True),
    )


@router.delete(
    "/mentor-profile/me",
    response_model=MentorProfileResponse,
    summary="Deactivate the authenticated user's mentor profile (soft delete)",
)
async def deactivate_mentor_profile(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Soft-delete the mentor profile (sets is_active=False)."""
    return await service.deactivate_mentor_profile(current_user.id)


# ------------------------------------------------------------------
# Discovery
# ------------------------------------------------------------------

@router.get(
    "/mentors",
    response_model=list[MentorProfileResponse],
    summary="Browse active mentor profiles with match percentage",
)
async def list_mentors(
    skills: str | None = Query(default=None, description="Comma-separated skills to filter by"),
    goals: str | None = Query(default=None, description="Comma-separated goals to filter by"),
    university: str | None = Query(default=None, description="Filter by university"),
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Browse active mentor profiles, excluding existing mentors and yourself.
    Returns match_percentage for each mentor relative to the authenticated user's preferences.
    """
    return await service.list_mentors(
        current_user=current_user,
        skills=skills,
        goals=goals,
        university=university,
    )


@router.get(
    "/mentors/{user_id}",
    response_model=MentorProfileResponse,
    summary="Get a mentor's public profile by user ID",
)
async def get_mentor_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Retrieve a mentor's public profile including average_rating and total_reviews."""
    return await service.get_mentor_profile_by_user_id(user_id)


# ------------------------------------------------------------------
# Requests
# ------------------------------------------------------------------

@router.post(
    "/requests",
    response_model=MentorshipRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a mentorship request to a mentor (supports optional file attachment)",
)
async def send_mentorship_request(
    mentor_id: Annotated[int, Form()],
    goal: Annotated[str, Form()],
    meeting_frequency: Annotated[str, Form()],
    session_length_minutes: Annotated[int, Form()],
    message: Annotated[str, Form()],
    attachment: Annotated[UploadFile | None, File()] = None,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Send a mentorship request. Accepts multipart/form-data so an optional file
    (JPEG, PNG, or PDF, max 10MB) can be attached alongside the request data.
    Validates: self-request, capacity, duplicate pending request, existing active relationship.
    """
    data = {
        "mentor_id": mentor_id,
        "goal": goal.strip(),
        "meeting_frequency": meeting_frequency.strip(),
        "session_length_minutes": session_length_minutes,
        "message": message.strip(),
    }
    return await service.send_request(
        mentee_id=current_user.id, data=data, attachment=attachment
    )


@router.get(
    "/requests/incoming",
    response_model=list[MentorshipRequestResponse],
    summary="Get pending mentorship requests addressed to the current user as mentor",
)
async def get_incoming_requests(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Mentor sees their pending incoming requests.
    Each request includes match_percentage relative to the mentor's profile and the mentee's preferences.
    """
    return await service.get_incoming_requests(current_user.id)


@router.get(
    "/requests/outgoing",
    response_model=list[MentorshipRequestResponse],
    summary="Get all mentorship requests sent by the current user as mentee",
)
async def get_outgoing_requests(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Mentee sees all their sent requests regardless of status."""
    return await service.get_outgoing_requests(current_user.id)


@router.patch(
    "/requests/{request_id}/accept",
    response_model=MentorshipRequestResponse,
    summary="Accept a pending mentorship request (mentor only)",
)
async def accept_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Accept a pending request. Automatically creates a new active relationship."""
    return await service.accept_request(request_id, current_user.id)


@router.patch(
    "/requests/{request_id}/reject",
    response_model=MentorshipRequestResponse,
    summary="Reject a pending mentorship request (mentor only)",
)
async def reject_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Reject a pending mentorship request and notify the mentee."""
    return await service.reject_request(request_id, current_user.id)


@router.delete(
    "/requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel a pending mentorship request (mentee only)",
)
async def cancel_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Cancel a pending request. Notifies the mentor via in-app notification and email."""
    await service.cancel_request(request_id, current_user.id)


# ------------------------------------------------------------------
# Relationships
# ------------------------------------------------------------------

@router.get(
    "/relationships/my-mentees",
    response_model=list[MentorshipRelationshipResponse],
    summary="List active relationships where the current user is the mentor",
)
async def get_my_mentees(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """List active mentoring relationships including progress_percentage."""
    return await service.get_my_mentees(current_user.id)


@router.get(
    "/relationships/my-mentors",
    response_model=list[MentorshipRelationshipResponse],
    summary="List active relationships where the current user is the mentee",
)
async def get_my_mentors(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """List active mentoring relationships (as mentee) including progress_percentage."""
    return await service.get_my_mentors(current_user.id)


@router.get(
    "/relationships/{relationship_id}",
    response_model=MentorshipRelationshipResponse,
    summary="Get a specific relationship (participants only)",
)
async def get_relationship(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Get relationship details including computed progress_percentage from milestones."""
    return await service.get_relationship(relationship_id, current_user.id)


@router.patch(
    "/relationships/{relationship_id}/end",
    response_model=MentorshipRelationshipResponse,
    summary="End a mentorship relationship (participants only)",
)
async def end_relationship(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """End a relationship. Notifies the other participant via in-app notification and email."""
    return await service.end_relationship(relationship_id, current_user.id)


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

@router.post(
    "/relationships/{relationship_id}/sessions",
    response_model=MentorshipSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a session for a relationship (participants only)",
)
async def create_session(
    relationship_id: int,
    body: MentorshipSessionCreate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Create an upcoming session. Both participants receive a SESSION_REMINDER notification.
    NOTE: In production a background worker (Celery) would send reminder emails 24h before the session.
    """
    return await service.create_session(
        relationship_id=relationship_id,
        current_user_id=current_user.id,
        data=body.model_dump(),
    )


@router.get(
    "/relationships/{relationship_id}/sessions",
    response_model=list[MentorshipSessionResponse],
    summary="List sessions for a relationship ordered by scheduled_at asc (participants only)",
)
async def list_sessions(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """List all sessions for a relationship in chronological order."""
    return await service.list_sessions(relationship_id, current_user.id)


@router.patch(
    "/relationships/{relationship_id}/sessions/{session_id}",
    response_model=MentorshipSessionResponse,
    summary="Update a session (participants only)",
)
async def update_session(
    relationship_id: int,
    session_id: int,
    body: MentorshipSessionUpdate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Update a session. When status is set to 'cancelled', notifies the other participant."""
    return await service.update_session(
        relationship_id=relationship_id,
        session_id=session_id,
        current_user_id=current_user.id,
        data=body.model_dump(exclude_unset=True),
    )


# ------------------------------------------------------------------
# Resources
# ------------------------------------------------------------------

@router.post(
    "/relationships/{relationship_id}/resources",
    response_model=MentorshipResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Share a resource within a relationship (participants only)",
)
async def create_resource(
    relationship_id: int,
    body: MentorshipResourceCreate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Share a resource. Notifies the other participant via in-app notification and email."""
    return await service.create_resource(
        relationship_id=relationship_id,
        current_user_id=current_user.id,
        data=body.model_dump(),
    )


@router.get(
    "/relationships/{relationship_id}/resources",
    response_model=list[MentorshipResourceResponse],
    summary="List resources shared in a relationship ordered by created_at desc (participants only)",
)
async def list_resources(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """List all resources shared within a relationship."""
    return await service.list_resources(relationship_id, current_user.id)


# ------------------------------------------------------------------
# Milestones  (2.1)
# ------------------------------------------------------------------

@router.post(
    "/relationships/{relationship_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a milestone for a relationship (mentor only)",
)
async def create_milestone(
    relationship_id: int,
    body: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Create a milestone in a relationship. Only the mentor can create milestones.
    The relationship must be active.
    """
    return await service.create_milestone(
        relationship_id=relationship_id,
        current_user_id=current_user.id,
        data=body.model_dump(exclude_unset=True),
    )


@router.get(
    "/relationships/{relationship_id}/milestones",
    response_model=list[MilestoneResponse],
    summary="List milestones for a relationship ordered by sort_order (participants only)",
)
async def list_milestones(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """List all milestones for a relationship in sort_order ascending."""
    return await service.get_milestones(relationship_id, current_user.id)


@router.put(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="Update a milestone",
)
async def update_milestone(
    milestone_id: int,
    body: MilestoneUpdate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Update a milestone.
    - Mentor: can update title, description, status, sort_order, target_date.
    - Mentee: can only update status.
    When status changes to 'completed', completed_date is auto-set to today and
    a MILESTONE_COMPLETED notification is sent to the other participant.
    """
    return await service.update_milestone(
        milestone_id=milestone_id,
        current_user_id=current_user.id,
        data=body.model_dump(exclude_unset=True),
    )


@router.delete(
    "/milestones/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a milestone (mentor only)",
)
async def delete_milestone(
    milestone_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Delete a milestone. Only the mentor in the relationship can delete milestones."""
    await service.delete_milestone(milestone_id, current_user.id)


# ------------------------------------------------------------------
# Reviews  (2.2)
# ------------------------------------------------------------------

@router.post(
    "/relationships/{relationship_id}/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Leave a review for the mentor in a relationship (mentee only)",
)
async def create_review(
    relationship_id: int,
    body: ReviewCreate,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Leave a review (rating 1-5) for the mentor. Only the mentee can review.
    One review per relationship — returns 409 if a review already exists.
    """
    return await service.create_review(
        relationship_id=relationship_id,
        reviewer_id=current_user.id,
        data=body.model_dump(),
    )


@router.get(
    "/mentors/{user_id}/reviews",
    response_model=list[ReviewResponse],
    summary="Get all reviews for a specific mentor (public)",
)
async def get_mentor_reviews(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Public endpoint: returns all reviews left for a mentor, including reviewer name."""
    return await service.get_mentor_reviews(user_id)


@router.get(
    "/mentors/{user_id}/rating",
    response_model=MentorRatingResponse,
    summary="Get aggregated rating for a mentor (public)",
)
async def get_mentor_rating(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """Public endpoint: returns average_rating (1 decimal) and total_reviews for a mentor."""
    return await service.get_mentor_rating(user_id)


# ------------------------------------------------------------------
# Stats  (2.4)
# ------------------------------------------------------------------

@router.get(
    "/stats/me",
    response_model=MentorshipStatsResponse,
    summary="Get mentorship stats for the authenticated user (both mentor and mentee views)",
)
async def get_mentorship_stats(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Returns mentoring statistics for the authenticated user from both perspectives:
    - as_mentee: active_mentors, pending_requests_sent, completed_sessions, overall_progress
    - as_mentor: active_mentees, pending_requests_received, total_hours_mentored,
                 resources_shared, total_sessions_completed, average_rating, total_reviews
    """
    return await service.get_mentorship_stats(current_user.id)


@router.get(
    "/my-mentors",
    response_model=list[MyMentorResponse],
    summary="Rich list of the authenticated user's mentors with progress and milestone summaries",
)
async def get_my_mentors_rich(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Returns active mentor relationships with rich details:
    mentor profile (name, role, job title, company, avatar),
    progress percentage, next upcoming session, and milestone summary.
    """
    return await service.get_rich_my_mentors(current_user.id)


@router.get(
    "/my-mentees",
    response_model=list[MyMenteeResponse],
    summary="Rich list of the authenticated user's mentees with progress and milestone summaries",
)
async def get_my_mentees_rich(
    current_user: User = Depends(get_current_user),
    service: MentorshipService = Depends(get_mentorship_service),
):
    """
    Returns active mentee relationships with rich details:
    mentee profile (name, role, avatar),
    progress percentage, next upcoming session, and milestone summary.
    """
    return await service.get_rich_my_mentees(current_user.id)
