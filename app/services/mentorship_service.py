from datetime import datetime, date, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.mentorship_request_status import MentorshipRequestStatus
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus
from app.enums.mentorship_session_status import MentorshipSessionStatus
from app.enums.milestone_status import MilestoneStatus
from app.enums.notification_type import NotificationType
from app.models.mentor_profile import MentorProfile
from app.models.mentorship_milestone import MentorshipMilestone
from app.models.mentorship_preference import MentorshipPreference
from app.models.mentorship_request import MentorshipRequest
from app.models.mentorship_relationship import MentorshipRelationship
from app.models.mentorship_review import MentorshipReview
from app.models.mentorship_session import MentorshipSession
from app.models.mentorship_resource import MentorshipResource
from app.models.user import User
from app.repositories.mentorship_repository import MentorshipRepository
from app.schemas.mentorship_schema import (
    DashboardStatsResponse,
    MenteeSummaryInRelationship,
    MentorshipStatsResponse,
    MentorStatsResponse,
    MenteeStatsResponse,
    MentorSummaryInRelationship,
    MilestoneSummary,
    MyMenteeResponse,
    MyMentorResponse,
    MentorProfileResponse,
    MentorRatingResponse,
    MentorshipRelationshipResponse,
    MentorshipRequestResponse,
    MentorshipSessionResponse,
    ReviewResponse,
    UpcomingSessionSummary,
)
from app.services.notification_service import NotificationService
from app.services.image_service import ImageService
from app.tasks.email_tasks import (
    send_mentorship_request_email,
    send_mentorship_accepted_email,
    send_mentorship_rejected_email,
    send_mentee_cancelled_request_email,
    send_milestone_completed_email,
    send_session_cancelled_email,
    send_resource_shared_email,
    send_relationship_ended_email,
)


class MentorshipService:

    def __init__(self, db: AsyncSession):
        self.repo = MentorshipRepository(db)
        self.notification_service = NotificationService(db)
        self.image_service = ImageService()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _assert_participant(
        self, relationship_id: int, user_id: int
    ) -> MentorshipRelationship:
        rel = await self.repo._load_relationship(relationship_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        if rel.mentor_id != user_id and rel.mentee_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        return rel

    async def _build_relationship_response(
        self, rel: MentorshipRelationship
    ) -> MentorshipRelationshipResponse:
        """Build a relationship response with computed progress_percentage."""
        progress = await self.repo.compute_progress_percentage(rel.id)
        resp = MentorshipRelationshipResponse.model_validate(rel)
        resp.progress_percentage = progress
        return resp

    async def _build_mentor_profile_response(
        self,
        profile: MentorProfile,
        match_percentage: int | None = None,
    ) -> MentorProfileResponse:
        """Build a mentor profile response with rating stats and optional match %."""
        avg_rating, total_reviews = await self.repo.get_mentor_rating(profile.user_id)
        resp = MentorProfileResponse.model_validate(profile)
        resp.average_rating = avg_rating
        resp.total_reviews = total_reviews
        resp.match_percentage = match_percentage
        return resp

    # ------------------------------------------------------------------
    # Match percentage algorithm  (2.3)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_match_percentage(
        mentee_user: User,
        mentee_prefs: MentorshipPreference | None,
        mentor_profile: MentorProfile,
        mentor_prefs: MentorshipPreference | None,
    ) -> int:
        """
        Algorithm:
        - 70 pts: proportional overlap of mentee areas_of_interest vs mentor expertise_areas
        - 15 pts: same university bonus
        - 15 pts: preferred_format match
        Capped at 100.
        """
        score = 0.0

        if mentee_prefs and mentee_prefs.areas_of_interest:
            mentee_areas = {str(a).strip().lower() for a in mentee_prefs.areas_of_interest if a}
            mentor_areas = {str(e).strip().lower() for e in (mentor_profile.expertise_areas or [])}
            if mentee_areas:
                matching = mentee_areas & mentor_areas
                score += (len(matching) / len(mentee_areas)) * 70

        # Same university bonus
        mentor_university = (
            mentor_profile.user.university.strip().lower()
            if mentor_profile.user and mentor_profile.user.university
            else ""
        )
        mentee_university = mentee_user.university.strip().lower() if mentee_user.university else ""
        if mentor_university and mentee_university and mentor_university == mentee_university:
            score += 15

        # Format compatibility
        if mentee_prefs and mentor_prefs:
            if mentee_prefs.preferred_format == mentor_prefs.preferred_format:
                score += 15

        return min(100, round(score))

    # ------------------------------------------------------------------
    # Mentor Profile
    # ------------------------------------------------------------------

    async def become_mentor(self, user_id: int, data: dict) -> MentorProfileResponse:
        """Create a mentor profile for the authenticated user."""
        existing = await self.repo.get_mentor_profile_by_user_id(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a mentor profile.",
            )
        profile = await self.repo.create_mentor_profile(user_id=user_id, **data)
        return await self._build_mentor_profile_response(profile)

    async def get_my_mentor_profile(self, user_id: int) -> MentorProfileResponse:
        """Get the authenticated user's own mentor profile."""
        profile = await self.repo.get_mentor_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mentor profile not found.",
            )
        return await self._build_mentor_profile_response(profile)

    async def update_mentor_profile(self, user_id: int, data: dict) -> MentorProfileResponse:
        """Update the authenticated user's mentor profile."""
        profile = await self.repo.get_mentor_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mentor profile not found.",
            )
        updates = {k: v for k, v in data.items() if v is not None}
        profile = await self.repo.update_mentor_profile(profile, updates)
        return await self._build_mentor_profile_response(profile)

    async def deactivate_mentor_profile(self, user_id: int) -> MentorProfileResponse:
        """Soft-delete the authenticated user's mentor profile."""
        profile = await self.repo.get_mentor_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mentor profile not found.",
            )
        profile = await self.repo.update_mentor_profile(profile, {"is_active": False})
        return await self._build_mentor_profile_response(profile)

    async def list_mentors(
        self,
        current_user: User,
        skills: str | None,
        goals: str | None,
        university: str | None,
    ) -> list[MentorProfileResponse]:
        """Browse active mentor profiles with optional filters and match % calculation."""
        active_mentor_ids = await self.repo.get_active_mentor_user_ids_for_mentee(current_user.id)
        profiles = await self.repo.list_active_mentor_profiles(
            exclude_user_id=current_user.id,
            exclude_mentor_user_ids=active_mentor_ids,
        )

        if skills:
            skill_set = {s.strip().lower() for s in skills.split(",") if s.strip()}
            profiles = [
                p for p in profiles
                if skill_set & {e.lower() for e in (p.expertise_areas or [])}
            ]

        if goals:
            goals_set = {g.strip().lower() for g in goals.split(",") if g.strip()}
            profiles = [
                p for p in profiles
                if goals_set & {g.lower() for g in (p.mentorship_goals or [])}
            ]

        if university:
            uni_lower = university.strip().lower()
            profiles = [
                p for p in profiles
                if p.user and p.user.university.lower() == uni_lower
            ]

        # Load mentee's own preferences once for match % calculation
        mentee_prefs = await self.repo.get_mentorship_preference(current_user.id)

        result = []
        for profile in profiles:
            mentor_prefs = await self.repo.get_mentorship_preference(profile.user_id)
            match_pct = self._compute_match_percentage(
                current_user, mentee_prefs, profile, mentor_prefs
            )
            result.append(await self._build_mentor_profile_response(profile, match_pct))

        return result

    async def get_mentor_profile_by_user_id(self, user_id: int) -> MentorProfileResponse:
        """Get a public mentor profile by user ID."""
        profile = await self.repo.get_active_mentor_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mentor profile not found.",
            )
        return await self._build_mentor_profile_response(profile)

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    async def send_request(
        self,
        mentee_id: int,
        data: dict,
        attachment: UploadFile | None = None,
    ) -> MentorshipRequestResponse:
        """Send a mentorship request, with optional file attachment."""
        mentor_id = data["mentor_id"]

        if mentor_id == mentee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot send a mentorship request to yourself.",
            )

        mentor_profile = await self.repo.get_active_mentor_profile_by_user_id(mentor_id)
        if not mentor_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mentor not found.",
            )

        active_count = await self.repo.count_active_relationships_for_mentor(mentor_id)
        if active_count >= mentor_profile.max_mentees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This mentor is currently at full capacity",
            )

        existing_pending = await self.repo.get_pending_request_between(mentee_id, mentor_id)
        if existing_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending request to this mentor already exists.",
            )

        existing_relationship = await self.repo.get_active_relationship_between(mentor_id, mentee_id)
        if existing_relationship:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active mentorship with this mentor.",
            )

        # Handle optional file attachment
        attachment_file_path: str | None = None
        if attachment:
            uploaded = await self.image_service.upload(
                file=attachment, image_type="request_attachment"
            )
            attachment_file_path = uploaded["url"]

        request = await self.repo.create_request(
            mentee_id=mentee_id,
            mentor_id=mentor_id,
            goal=data["goal"],
            meeting_frequency=data["meeting_frequency"],
            session_length_minutes=data["session_length_minutes"],
            message=data["message"],
            attachment_file_path=attachment_file_path,
        )

        try:
            await self.notification_service.send(
                recipient_id=mentor_id,
                notification_type=NotificationType.MENTORSHIP_REQUEST,
                sender_id=mentee_id,
                reference_id=request.id,
            )
        except Exception:
            pass

        # Email notification to mentor
        try:
            mentor_user = await self.repo.get_user_by_id(mentor_id)
            mentee_user = await self.repo.get_user_by_id(mentee_id)
            if mentor_user and mentee_user:
                send_mentorship_request_email(
                    to_email=mentor_user.email,
                    mentor_first_name=mentor_user.full_name.split()[0],
                    mentee_name=mentee_user.full_name,
                )
        except Exception:
            pass

        resp = MentorshipRequestResponse.model_validate(request)
        return resp

    async def get_incoming_requests(self, mentor_id: int) -> list[MentorshipRequestResponse]:
        """Mentor sees pending requests with match percentage for each mentee."""
        requests = await self.repo.get_incoming_pending_requests(mentor_id)
        mentor_profile = await self.repo.get_mentor_profile_by_user_id(mentor_id)
        mentor_prefs = await self.repo.get_mentorship_preference(mentor_id)

        result = []
        for req in requests:
            mentee_prefs = await self.repo.get_mentorship_preference(req.mentee_id)
            mentee_user = req.mentee  # already loaded via joinedload

            match_pct: int | None = None
            if mentor_profile:
                match_pct = self._compute_match_percentage(
                    mentee_user, mentee_prefs, mentor_profile, mentor_prefs
                )

            resp = MentorshipRequestResponse.model_validate(req)
            resp.match_percentage = match_pct
            result.append(resp)

        return result

    async def get_outgoing_requests(self, mentee_id: int) -> list[MentorshipRequestResponse]:
        """Mentee sees all their sent requests."""
        requests = await self.repo.get_outgoing_requests(mentee_id)
        return [MentorshipRequestResponse.model_validate(r) for r in requests]

    async def accept_request(
        self, request_id: int, current_user_id: int
    ) -> MentorshipRequestResponse:
        """Accept a pending mentorship request (mentor only). Auto-creates relationship."""
        request = await self.repo._load_request(request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

        if request.mentor_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

        if request.status != MentorshipRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending requests can be accepted.",
            )

        await self.repo.create_relationship(
            mentor_id=request.mentor_id,
            mentee_id=request.mentee_id,
            goal=request.goal,
            meeting_frequency=request.meeting_frequency,
            session_length_minutes=request.session_length_minutes,
        )

        updated = await self.repo.update_request_status(request, MentorshipRequestStatus.ACCEPTED)

        try:
            await self.notification_service.send(
                recipient_id=request.mentee_id,
                notification_type=NotificationType.MENTORSHIP_ACCEPTED,
                sender_id=current_user_id,
                reference_id=request_id,
            )
        except Exception:
            pass

        try:
            mentee_user = await self.repo.get_user_by_id(request.mentee_id)
            mentor_user = await self.repo.get_user_by_id(current_user_id)
            if mentee_user and mentor_user:
                send_mentorship_accepted_email(
                    to_email=mentee_user.email,
                    mentee_first_name=mentee_user.full_name.split()[0],
                    mentor_name=mentor_user.full_name,
                )
        except Exception:
            pass

        return MentorshipRequestResponse.model_validate(updated)

    async def reject_request(
        self, request_id: int, current_user_id: int
    ) -> MentorshipRequestResponse:
        """Reject a pending mentorship request (mentor only)."""
        request = await self.repo._load_request(request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

        if request.mentor_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

        if request.status != MentorshipRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending requests can be rejected.",
            )

        updated = await self.repo.update_request_status(request, MentorshipRequestStatus.REJECTED)

        try:
            await self.notification_service.send(
                recipient_id=request.mentee_id,
                notification_type=NotificationType.MENTORSHIP_REJECTED,
                sender_id=current_user_id,
                reference_id=request_id,
            )
        except Exception:
            pass

        try:
            mentee_user = await self.repo.get_user_by_id(request.mentee_id)
            mentor_user = await self.repo.get_user_by_id(current_user_id)
            if mentee_user and mentor_user:
                send_mentorship_rejected_email(
                    to_email=mentee_user.email,
                    mentee_first_name=mentee_user.full_name.split()[0],
                    mentor_name=mentor_user.full_name,
                )
        except Exception:
            pass

        return MentorshipRequestResponse.model_validate(updated)

    async def cancel_request(self, request_id: int, current_user_id: int) -> None:
        """Cancel a pending mentorship request (mentee only)."""
        request = await self.repo._load_request(request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

        if request.mentee_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

        if request.status != MentorshipRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending requests can be cancelled.",
            )

        await self.repo.update_request_status(request, MentorshipRequestStatus.CANCELLED)

        # Notify mentor that the mentee cancelled  (2.6)
        try:
            await self.notification_service.send(
                recipient_id=request.mentor_id,
                notification_type=NotificationType.MENTEE_CANCELLED_REQUEST,
                sender_id=current_user_id,
                reference_id=request_id,
            )
        except Exception:
            pass

        try:
            mentor_user = await self.repo.get_user_by_id(request.mentor_id)
            mentee_user = await self.repo.get_user_by_id(current_user_id)
            if mentor_user and mentee_user:
                send_mentee_cancelled_request_email(
                    to_email=mentor_user.email,
                    mentor_first_name=mentor_user.full_name.split()[0],
                    mentee_name=mentee_user.full_name,
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    async def get_my_mentees(self, mentor_id: int) -> list[MentorshipRelationshipResponse]:
        """List active relationships where the current user is the mentor."""
        rels = await self.repo.get_active_mentees(mentor_id)
        return [await self._build_relationship_response(r) for r in rels]

    async def get_my_mentors(self, mentee_id: int) -> list[MentorshipRelationshipResponse]:
        """List active relationships where the current user is the mentee."""
        rels = await self.repo.get_active_mentors(mentee_id)
        return [await self._build_relationship_response(r) for r in rels]

    async def get_relationship(
        self, relationship_id: int, current_user_id: int
    ) -> MentorshipRelationshipResponse:
        """Get a specific relationship (participants only)."""
        rel = await self.repo._load_relationship(relationship_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        if rel.mentor_id != current_user_id and rel.mentee_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        return await self._build_relationship_response(rel)

    async def end_relationship(
        self, relationship_id: int, current_user_id: int
    ) -> MentorshipRelationshipResponse:
        """End a mentorship relationship (participants only)."""
        rel = await self.repo._load_relationship(relationship_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        if rel.mentor_id != current_user_id and rel.mentee_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        if rel.status == MentorshipRelationshipStatus.ENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This relationship has already ended.",
            )

        other_id = rel.mentee_id if current_user_id == rel.mentor_id else rel.mentor_id

        updated_rel = await self.repo.update_relationship(rel, {
            "status": MentorshipRelationshipStatus.ENDED,
            "ended_at": datetime.now(timezone.utc),
        })

        # Notify the other participant  (2.6)
        try:
            await self.notification_service.send(
                recipient_id=other_id,
                notification_type=NotificationType.RELATIONSHIP_ENDED,
                sender_id=current_user_id,
                reference_id=relationship_id,
            )
        except Exception:
            pass

        try:
            other_user = await self.repo.get_user_by_id(other_id)
            actor_user = await self.repo.get_user_by_id(current_user_id)
            if other_user and actor_user:
                send_relationship_ended_email(
                    to_email=other_user.email,
                    recipient_first_name=other_user.full_name.split()[0],
                    actor_name=actor_user.full_name,
                )
        except Exception:
            pass

        return await self._build_relationship_response(updated_rel)

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def create_session(
        self, relationship_id: int, current_user_id: int, data: dict
    ) -> MentorshipSession:
        """Create a session for an active relationship (participants only)."""
        rel = await self._assert_participant(relationship_id, current_user_id)
        if rel.status != MentorshipRelationshipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sessions can only be added to active relationships.",
            )
        session = await self.repo.create_session(relationship_id=relationship_id, **data)

        # Session reminder notification: created at session creation time.
        # TODO: In production, a background worker (e.g. Celery beat) would check
        # for sessions with scheduled_at ~24h in the future and send the reminder
        # at the right time. For the dissertation, we create the in-app notification
        # immediately so the intent is captured.
        other_id = rel.mentee_id if current_user_id == rel.mentor_id else rel.mentor_id
        try:
            for recipient in [current_user_id, other_id]:
                await self.notification_service.send(
                    recipient_id=recipient,
                    notification_type=NotificationType.SESSION_REMINDER,
                    sender_id=None,
                    reference_id=session.id,
                )
        except Exception:
            pass

        return session

    async def list_sessions(
        self, relationship_id: int, current_user_id: int
    ) -> list[MentorshipSession]:
        """List sessions for a relationship (participants only)."""
        await self._assert_participant(relationship_id, current_user_id)
        return await self.repo.get_sessions_for_relationship(relationship_id)

    async def update_session(
        self,
        relationship_id: int,
        session_id: int,
        current_user_id: int,
        data: dict,
    ) -> MentorshipSession:
        """Update a session (participants only). Triggers SESSION_CANCELLED notification."""
        rel = await self._assert_participant(relationship_id, current_user_id)
        session = await self.repo.get_session_by_id(session_id)
        if not session or session.relationship_id != relationship_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        updates = {k: v for k, v in data.items() if v is not None}
        was_cancelled = updates.get("status") == MentorshipSessionStatus.CANCELLED

        updated = await self.repo.update_session(session, updates)

        # Notify other participant when session is cancelled  (2.6)
        if was_cancelled:
            other_id = rel.mentee_id if current_user_id == rel.mentor_id else rel.mentor_id
            try:
                await self.notification_service.send(
                    recipient_id=other_id,
                    notification_type=NotificationType.SESSION_CANCELLED,
                    sender_id=current_user_id,
                    reference_id=session_id,
                )
            except Exception:
                pass

            try:
                other_user = await self.repo.get_user_by_id(other_id)
                actor_user = await self.repo.get_user_by_id(current_user_id)
                if other_user and actor_user:
                    send_session_cancelled_email(
                        to_email=other_user.email,
                        recipient_first_name=other_user.full_name.split()[0],
                        actor_name=actor_user.full_name,
                        scheduled_at=session.scheduled_at,
                    )
            except Exception:
                pass

        return updated

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    async def create_resource(
        self, relationship_id: int, current_user_id: int, data: dict
    ) -> MentorshipResource:
        """Share a resource within a relationship. Notifies the other participant."""
        rel = await self._assert_participant(relationship_id, current_user_id)
        resource = await self.repo.create_resource(
            relationship_id=relationship_id,
            shared_by_id=current_user_id,
            **data,
        )

        # Notify the other participant  (2.6)
        other_id = rel.mentee_id if current_user_id == rel.mentor_id else rel.mentor_id
        try:
            await self.notification_service.send(
                recipient_id=other_id,
                notification_type=NotificationType.RESOURCE_SHARED,
                sender_id=current_user_id,
                reference_id=resource.id,
            )
        except Exception:
            pass

        try:
            other_user = await self.repo.get_user_by_id(other_id)
            actor_user = await self.repo.get_user_by_id(current_user_id)
            if other_user and actor_user:
                send_resource_shared_email(
                    to_email=other_user.email,
                    recipient_first_name=other_user.full_name.split()[0],
                    sharer_name=actor_user.full_name,
                    resource_title=data.get("title", "a resource"),
                )
        except Exception:
            pass

        return resource

    async def list_resources(
        self, relationship_id: int, current_user_id: int
    ) -> list[MentorshipResource]:
        """List resources for a relationship (participants only)."""
        await self._assert_participant(relationship_id, current_user_id)
        return await self.repo.get_resources_for_relationship(relationship_id)

    # ------------------------------------------------------------------
    # Milestones  (2.1)
    # ------------------------------------------------------------------

    async def create_milestone(
        self, relationship_id: int, current_user_id: int, data: dict
    ) -> MentorshipMilestone:
        """Create a milestone for a relationship. Only the mentor can create milestones."""
        rel = await self.repo._load_relationship(relationship_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found.")

        if rel.mentor_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the mentor can create milestones.",
            )

        if rel.status != MentorshipRelationshipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Milestones can only be added to active relationships.",
            )

        return await self.repo.create_milestone(relationship_id=relationship_id, **data)

    async def get_milestones(
        self, relationship_id: int, current_user_id: int
    ) -> list[MentorshipMilestone]:
        """List milestones for a relationship (participants only)."""
        await self._assert_participant(relationship_id, current_user_id)
        return await self.repo.get_milestones_for_relationship(relationship_id)

    async def update_milestone(
        self, milestone_id: int, current_user_id: int, data: dict
    ) -> MentorshipMilestone:
        """
        Update a milestone.
        - Mentor can update everything.
        - Mentee can only update status.
        - When status → completed, auto-set completed_date.
        - Triggers MILESTONE_COMPLETED notification to the other participant.
        """
        milestone = await self.repo.get_milestone_by_id(milestone_id)
        if not milestone:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")

        rel = await self.repo._load_relationship(milestone.relationship_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

        is_mentor = rel.mentor_id == current_user_id
        is_mentee = rel.mentee_id == current_user_id

        if not is_mentor and not is_mentee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

        # Mentees can only update status
        if is_mentee and not is_mentor:
            allowed_keys = {"status"}
            disallowed = set(data.keys()) - allowed_keys
            if disallowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mentees can only update the milestone status.",
                )

        updates = {k: v for k, v in data.items() if v is not None}

        # Auto-set completed_date when status becomes completed
        new_status = updates.get("status")
        if new_status == MilestoneStatus.COMPLETED and milestone.status != MilestoneStatus.COMPLETED:
            updates["completed_date"] = date.today()

            # Notify the other participant  (milestone completed — 2.1 / 2.6)
            other_id = rel.mentee_id if is_mentor else rel.mentor_id
            try:
                await self.notification_service.send(
                    recipient_id=other_id,
                    notification_type=NotificationType.MILESTONE_COMPLETED,
                    sender_id=current_user_id,
                    reference_id=milestone_id,
                )
            except Exception:
                pass

            try:
                other_user = await self.repo.get_user_by_id(other_id)
                actor_user = await self.repo.get_user_by_id(current_user_id)
                if other_user and actor_user:
                    send_milestone_completed_email(
                        to_email=other_user.email,
                        recipient_first_name=other_user.full_name.split()[0],
                        actor_name=actor_user.full_name,
                        milestone_title=milestone.title,
                    )
            except Exception:
                pass

        return await self.repo.update_milestone(milestone, updates)

    async def delete_milestone(self, milestone_id: int, current_user_id: int) -> None:
        """Delete a milestone. Only the mentor can delete."""
        milestone = await self.repo.get_milestone_by_id(milestone_id)
        if not milestone:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")

        rel = await self.repo._load_relationship(milestone.relationship_id)
        if not rel or rel.mentor_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the mentor can delete milestones.",
            )

        await self.repo.delete_milestone(milestone)

    # ------------------------------------------------------------------
    # Reviews  (2.2)
    # ------------------------------------------------------------------

    async def create_review(
        self, relationship_id: int, reviewer_id: int, data: dict
    ) -> ReviewResponse:
        """
        Create a review. Only the mentee can review the mentor.
        One review per relationship (unique constraint enforced at DB level).
        """
        rel = await self.repo._load_relationship(relationship_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found.")

        # Reviewer must be the mentee
        if rel.mentee_id != reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the mentee in this relationship can leave a review.",
            )

        # Check for duplicate review
        existing = await self.repo.get_review_for_relationship(relationship_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A review for this relationship already exists.",
            )

        review = await self.repo.create_review(
            relationship_id=relationship_id,
            reviewer_id=reviewer_id,
            reviewee_id=rel.mentor_id,
            rating=data["rating"],
            review_text=data.get("review_text"),
        )

        return ReviewResponse(
            id=review.id,
            relationship_id=review.relationship_id,
            reviewer_id=review.reviewer_id,
            reviewee_id=review.reviewee_id,
            reviewer_name=review.reviewer.full_name,
            rating=review.rating,
            review_text=review.review_text,
            created_at=review.created_at,
        )

    async def get_mentor_reviews(self, mentor_user_id: int) -> list[ReviewResponse]:
        """Get all reviews for a specific mentor (public endpoint)."""
        reviews = await self.repo.get_reviews_for_mentor(mentor_user_id)
        return [
            ReviewResponse(
                id=r.id,
                relationship_id=r.relationship_id,
                reviewer_id=r.reviewer_id,
                reviewee_id=r.reviewee_id,
                reviewer_name=r.reviewer.full_name,
                rating=r.rating,
                review_text=r.review_text,
                created_at=r.created_at,
            )
            for r in reviews
        ]

    async def get_mentor_rating(self, mentor_user_id: int) -> MentorRatingResponse:
        """Get aggregated rating for a mentor (public endpoint)."""
        avg, total = await self.repo.get_mentor_rating(mentor_user_id)
        return MentorRatingResponse(
            user_id=mentor_user_id,
            average_rating=avg,
            total_reviews=total,
        )

    # ------------------------------------------------------------------
    # Dashboard stats  (2.4)
    # ------------------------------------------------------------------

    async def get_dashboard_stats(self, user_id: int) -> DashboardStatsResponse:
        """Combined dashboard stats for the authenticated user."""
        # TODO: messages_unread — integrate with the direct messaging / community message system
        messages_unread = 0

        # TODO: upcoming_events — integrate with the events system (EventRegistration table)
        upcoming_events = 0

        sessions_with_rels = await self.repo.get_upcoming_sessions_for_user(user_id, limit=5)

        upcoming_sessions = []
        for session, rel in sessions_with_rels:
            other_id = rel.mentee_id if rel.mentor_id == user_id else rel.mentor_id
            other_name = (
                rel.mentee.full_name if rel.mentor_id == user_id else rel.mentor.full_name
            )
            upcoming_sessions.append(
                UpcomingSessionSummary(
                    session_id=session.id,
                    mentor_or_mentee_name=other_name,
                    title=session.notes,
                    scheduled_at=session.scheduled_at,
                    relationship_id=rel.id,
                )
            )

        return DashboardStatsResponse(
            messages_unread=messages_unread,
            upcoming_events=upcoming_events,
            upcoming_sessions=upcoming_sessions,
        )

    async def get_mentorship_stats(self, user_id: int) -> MentorshipStatsResponse:
        """Mentoring-specific stats for the authenticated user (both mentor and mentee views)."""
        # As mentee
        active_mentors = await self.repo.count_active_mentors_for_mentee(user_id)
        pending_sent = await self.repo.count_pending_requests_sent(user_id)
        completed_sessions = await self.repo.count_completed_sessions_as_participant(user_id)

        # Calculate overall_progress: average milestone progress across active mentee relationships
        active_mentee_rels = await self.repo.get_active_mentors(user_id)
        overall_progress = 0
        if active_mentee_rels:
            progress_values = [
                await self.repo.compute_progress_percentage(r.id)
                for r in active_mentee_rels
            ]
            overall_progress = round(sum(progress_values) / len(progress_values))

        # As mentor
        active_mentees = await self.repo.count_active_mentees_for_mentor(user_id)
        pending_received = await self.repo.count_pending_requests_received(user_id)
        total_minutes = await self.repo.sum_session_minutes_as_mentor(user_id)
        total_hours = round(total_minutes / 60, 1)
        resources_shared = await self.repo.count_resources_shared_by(user_id)
        total_sessions_completed = await self.repo.count_completed_sessions_as_participant(user_id)
        avg_rating, total_reviews = await self.repo.get_mentor_rating(user_id)

        return MentorshipStatsResponse(
            as_mentee=MenteeStatsResponse(
                active_mentors=active_mentors,
                pending_requests_sent=pending_sent,
                completed_sessions=completed_sessions,
                overall_progress=overall_progress,
            ),
            as_mentor=MentorStatsResponse(
                active_mentees=active_mentees,
                pending_requests_received=pending_received,
                total_hours_mentored=total_hours,
                resources_shared=resources_shared,
                total_sessions_completed=total_sessions_completed,
                average_rating=avg_rating,
                total_reviews=total_reviews,
            ),
        )

    # ------------------------------------------------------------------
    # Rich my-mentors / my-mentees  (2.4)
    # ------------------------------------------------------------------

    async def get_rich_my_mentors(self, mentee_id: int) -> list[MyMentorResponse]:
        """Rich list of the user's mentors with progress and milestone summaries."""
        rels = await self.repo.get_active_mentors(mentee_id)
        result = []

        for rel in rels:
            total, completed, in_progress = await self.repo.get_milestone_counts(rel.id)
            progress = round((completed / total) * 100) if total > 0 else 0
            next_session = await self.repo.get_next_upcoming_session(rel.id)
            professional_profile = await self.repo.get_professional_profile(rel.mentor_id)

            mentor_data = MentorSummaryInRelationship(
                user_id=rel.mentor.id,
                name=rel.mentor.full_name,
                role=rel.mentor.user_role,
                job_title=professional_profile.job_title if professional_profile else None,
                company=professional_profile.company if professional_profile else None,
                avatar_url=rel.mentor.profile.avatar_url if rel.mentor.profile else None,
                verification_status=rel.mentor.verification_status,
            )

            result.append(
                MyMentorResponse(
                    relationship_id=rel.id,
                    mentor=mentor_data,
                    status=rel.status,
                    started_at=rel.started_at,
                    progress_percentage=progress,
                    next_session=MentorshipSessionResponse.model_validate(next_session) if next_session else None,
                    milestone_summary=MilestoneSummary(
                        total=total,
                        completed=completed,
                        in_progress=in_progress,
                    ),
                )
            )

        return result

    async def get_rich_my_mentees(self, mentor_id: int) -> list[MyMenteeResponse]:
        """Rich list of the user's mentees with progress and milestone summaries."""
        rels = await self.repo.get_active_mentees(mentor_id)
        result = []

        for rel in rels:
            total, completed, in_progress = await self.repo.get_milestone_counts(rel.id)
            progress = round((completed / total) * 100) if total > 0 else 0
            next_session = await self.repo.get_next_upcoming_session(rel.id)

            mentee_data = MenteeSummaryInRelationship(
                user_id=rel.mentee.id,
                name=rel.mentee.full_name,
                role=rel.mentee.user_role,
                avatar_url=rel.mentee.profile.avatar_url if rel.mentee.profile else None,
                verification_status=rel.mentee.verification_status,
            )

            result.append(
                MyMenteeResponse(
                    relationship_id=rel.id,
                    mentee=mentee_data,
                    status=rel.status,
                    started_at=rel.started_at,
                    progress_percentage=progress,
                    next_session=MentorshipSessionResponse.model_validate(next_session) if next_session else None,
                    milestone_summary=MilestoneSummary(
                        total=total,
                        completed=completed,
                        in_progress=in_progress,
                    ),
                )
            )

        return result
