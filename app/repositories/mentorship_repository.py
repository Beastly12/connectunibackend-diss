from datetime import datetime, timezone

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.enums.mentorship_request_status import MentorshipRequestStatus
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus
from app.enums.mentorship_session_status import MentorshipSessionStatus
from app.enums.milestone_status import MilestoneStatus
from app.models.mentor_profile import MentorProfile
from app.models.mentorship_milestone import MentorshipMilestone
from app.models.mentorship_preference import MentorshipPreference
from app.models.mentorship_request import MentorshipRequest
from app.models.mentorship_relationship import MentorshipRelationship
from app.models.mentorship_resource import MentorshipResource
from app.models.mentorship_review import MentorshipReview
from app.models.mentorship_session import MentorshipSession
from app.models.professional_profile import ProfessionalProfile
from app.models.user import User


class MentorshipRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # MentorProfile
    # ------------------------------------------------------------------

    async def get_mentor_profile_by_user_id(self, user_id: int) -> MentorProfile | None:
        result = await self.db.execute(
            select(MentorProfile)
            .options(joinedload(MentorProfile.user))
            .where(MentorProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active_mentor_profile_by_user_id(self, user_id: int) -> MentorProfile | None:
        result = await self.db.execute(
            select(MentorProfile)
            .options(joinedload(MentorProfile.user))
            .where(MentorProfile.user_id == user_id, MentorProfile.is_active == True)
        )
        return result.scalar_one_or_none()

    async def create_mentor_profile(self, user_id: int, **data) -> MentorProfile:
        profile = MentorProfile(user_id=user_id, **data)
        self.db.add(profile)
        await self.db.commit()
        return await self.get_mentor_profile_by_user_id(user_id)

    async def update_mentor_profile(self, profile: MentorProfile, data: dict) -> MentorProfile:
        for key, value in data.items():
            setattr(profile, key, value)
        await self.db.commit()
        return await self.get_mentor_profile_by_user_id(profile.user_id)

    async def list_active_mentor_profiles(
        self,
        exclude_user_id: int,
        exclude_mentor_user_ids: set[int],
    ) -> list[MentorProfile]:
        query = (
            select(MentorProfile)
            .options(joinedload(MentorProfile.user))
            .where(
                MentorProfile.is_active == True,
                MentorProfile.user_id != exclude_user_id,
            )
        )
        if exclude_mentor_user_ids:
            query = query.where(MentorProfile.user_id.not_in(exclude_mentor_user_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_active_relationships_for_mentor(self, mentor_user_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(MentorshipRelationship)
            .where(
                MentorshipRelationship.mentor_id == mentor_user_id,
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
            )
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # MentorshipRequest
    # ------------------------------------------------------------------

    async def _load_request(self, request_id: int) -> MentorshipRequest | None:
        result = await self.db.execute(
            select(MentorshipRequest)
            .options(joinedload(MentorshipRequest.mentee), joinedload(MentorshipRequest.mentor))
            .where(MentorshipRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_request_between(
        self, mentee_id: int, mentor_id: int
    ) -> MentorshipRequest | None:
        result = await self.db.execute(
            select(MentorshipRequest).where(
                MentorshipRequest.mentee_id == mentee_id,
                MentorshipRequest.mentor_id == mentor_id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_relationship_between(
        self, mentor_id: int, mentee_id: int
    ) -> MentorshipRelationship | None:
        result = await self.db.execute(
            select(MentorshipRelationship).where(
                MentorshipRelationship.mentor_id == mentor_id,
                MentorshipRelationship.mentee_id == mentee_id,
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def create_request(self, **data) -> MentorshipRequest:
        req = MentorshipRequest(**data)
        self.db.add(req)
        await self.db.commit()
        return await self._load_request(req.id)

    async def update_request_status(
        self, request: MentorshipRequest, new_status: MentorshipRequestStatus
    ) -> MentorshipRequest:
        request.status = new_status
        await self.db.commit()
        return await self._load_request(request.id)

    async def get_incoming_pending_requests(self, mentor_id: int) -> list[MentorshipRequest]:
        result = await self.db.execute(
            select(MentorshipRequest)
            .options(joinedload(MentorshipRequest.mentee), joinedload(MentorshipRequest.mentor))
            .where(
                MentorshipRequest.mentor_id == mentor_id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            )
            .order_by(MentorshipRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_outgoing_requests(self, mentee_id: int) -> list[MentorshipRequest]:
        result = await self.db.execute(
            select(MentorshipRequest)
            .options(joinedload(MentorshipRequest.mentee), joinedload(MentorshipRequest.mentor))
            .where(MentorshipRequest.mentee_id == mentee_id)
            .order_by(MentorshipRequest.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # MentorshipRelationship
    # ------------------------------------------------------------------

    async def _load_relationship(self, relationship_id: int) -> MentorshipRelationship | None:
        result = await self.db.execute(
            select(MentorshipRelationship)
            .options(
                joinedload(MentorshipRelationship.mentor),
                joinedload(MentorshipRelationship.mentee),
            )
            .where(MentorshipRelationship.id == relationship_id)
        )
        return result.scalar_one_or_none()

    async def create_relationship(self, **data) -> MentorshipRelationship:
        rel = MentorshipRelationship(**data)
        self.db.add(rel)
        await self.db.commit()
        return await self._load_relationship(rel.id)

    async def update_relationship(
        self, relationship: MentorshipRelationship, data: dict
    ) -> MentorshipRelationship:
        for key, value in data.items():
            setattr(relationship, key, value)
        await self.db.commit()
        return await self._load_relationship(relationship.id)

    async def get_active_mentees(self, mentor_id: int) -> list[MentorshipRelationship]:
        result = await self.db.execute(
            select(MentorshipRelationship)
            .options(
                joinedload(MentorshipRelationship.mentor),
                joinedload(MentorshipRelationship.mentee),
            )
            .where(
                MentorshipRelationship.mentor_id == mentor_id,
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())

    async def get_active_mentors(self, mentee_id: int) -> list[MentorshipRelationship]:
        result = await self.db.execute(
            select(MentorshipRelationship)
            .options(
                joinedload(MentorshipRelationship.mentor),
                joinedload(MentorshipRelationship.mentee),
            )
            .where(
                MentorshipRelationship.mentee_id == mentee_id,
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())

    async def get_all_relationships_as_mentee(self, mentee_id: int) -> list[MentorshipRelationship]:
        result = await self.db.execute(
            select(MentorshipRelationship)
            .options(
                joinedload(MentorshipRelationship.mentor),
                joinedload(MentorshipRelationship.mentee),
            )
            .where(MentorshipRelationship.mentee_id == mentee_id)
        )
        return list(result.scalars().all())

    async def get_active_mentor_user_ids_for_mentee(self, mentee_id: int) -> set[int]:
        result = await self.db.execute(
            select(MentorshipRelationship.mentor_id).where(
                MentorshipRelationship.mentee_id == mentee_id,
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
            )
        )
        return set(result.scalars().all())

    # ------------------------------------------------------------------
    # MentorshipSession
    # ------------------------------------------------------------------

    async def get_session_by_id(self, session_id: int) -> MentorshipSession | None:
        result = await self.db.execute(
            select(MentorshipSession).where(MentorshipSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def create_session(self, **data) -> MentorshipSession:
        session = MentorshipSession(**data)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def update_session(self, session: MentorshipSession, data: dict) -> MentorshipSession:
        for key, value in data.items():
            setattr(session, key, value)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_sessions_for_relationship(
        self, relationship_id: int
    ) -> list[MentorshipSession]:
        result = await self.db.execute(
            select(MentorshipSession)
            .where(MentorshipSession.relationship_id == relationship_id)
            .order_by(MentorshipSession.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_next_upcoming_session(
        self, relationship_id: int
    ) -> MentorshipSession | None:
        """Return the earliest future UPCOMING session for a relationship."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(MentorshipSession)
            .where(
                MentorshipSession.relationship_id == relationship_id,
                MentorshipSession.status == MentorshipSessionStatus.UPCOMING,
                MentorshipSession.scheduled_at > now,
            )
            .order_by(MentorshipSession.scheduled_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_upcoming_sessions_for_user(
        self, user_id: int, limit: int = 5
    ) -> list[tuple[MentorshipSession, MentorshipRelationship]]:
        """Return upcoming sessions (with relationship) where user is mentor or mentee."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(MentorshipSession, MentorshipRelationship)
            .join(
                MentorshipRelationship,
                MentorshipSession.relationship_id == MentorshipRelationship.id,
            )
            .where(
                MentorshipSession.status == MentorshipSessionStatus.UPCOMING,
                MentorshipSession.scheduled_at > now,
                (
                    (MentorshipRelationship.mentor_id == user_id)
                    | (MentorshipRelationship.mentee_id == user_id)
                ),
            )
            .order_by(MentorshipSession.scheduled_at.asc())
            .limit(limit)
        )
        rows = result.all()

        # Eagerly load mentor/mentee users for each relationship
        pairs: list[tuple[MentorshipSession, MentorshipRelationship]] = []
        for session, rel in rows:
            # Refresh relationship with users loaded
            loaded_rel = await self._load_relationship(rel.id)
            pairs.append((session, loaded_rel))
        return pairs

    # ------------------------------------------------------------------
    # MentorshipResource
    # ------------------------------------------------------------------

    async def _load_resource(self, resource_id: int) -> MentorshipResource | None:
        result = await self.db.execute(
            select(MentorshipResource)
            .options(joinedload(MentorshipResource.shared_by))
            .where(MentorshipResource.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def create_resource(self, **data) -> MentorshipResource:
        resource = MentorshipResource(**data)
        self.db.add(resource)
        await self.db.commit()
        return await self._load_resource(resource.id)

    async def get_resources_for_relationship(
        self, relationship_id: int
    ) -> list[MentorshipResource]:
        result = await self.db.execute(
            select(MentorshipResource)
            .options(joinedload(MentorshipResource.shared_by))
            .where(MentorshipResource.relationship_id == relationship_id)
            .order_by(MentorshipResource.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_resources_shared_by(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(MentorshipResource)
            .where(MentorshipResource.shared_by_id == user_id)
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # MentorshipMilestone  (2.1)
    # ------------------------------------------------------------------

    async def get_milestone_by_id(self, milestone_id: int) -> MentorshipMilestone | None:
        result = await self.db.execute(
            select(MentorshipMilestone).where(MentorshipMilestone.id == milestone_id)
        )
        return result.scalar_one_or_none()

    async def create_milestone(self, **data) -> MentorshipMilestone:
        milestone = MentorshipMilestone(**data)
        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def update_milestone(
        self, milestone: MentorshipMilestone, data: dict
    ) -> MentorshipMilestone:
        for key, value in data.items():
            setattr(milestone, key, value)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def delete_milestone(self, milestone: MentorshipMilestone) -> None:
        await self.db.execute(
            delete(MentorshipMilestone).where(MentorshipMilestone.id == milestone.id)
        )
        await self.db.commit()

    async def get_milestones_for_relationship(
        self, relationship_id: int
    ) -> list[MentorshipMilestone]:
        result = await self.db.execute(
            select(MentorshipMilestone)
            .where(MentorshipMilestone.relationship_id == relationship_id)
            .order_by(MentorshipMilestone.sort_order.asc(), MentorshipMilestone.id.asc())
        )
        return list(result.scalars().all())

    async def get_milestone_counts(
        self, relationship_id: int
    ) -> tuple[int, int, int]:
        """Return (total, completed, in_progress) milestone counts for a relationship."""
        result = await self.db.execute(
            select(MentorshipMilestone.status, func.count())
            .where(MentorshipMilestone.relationship_id == relationship_id)
            .group_by(MentorshipMilestone.status)
        )
        rows = result.all()
        total = sum(count for _, count in rows)
        completed = next((count for status, count in rows if status == MilestoneStatus.COMPLETED), 0)
        in_progress = next((count for status, count in rows if status == MilestoneStatus.IN_PROGRESS), 0)
        return total, completed, in_progress

    async def compute_progress_percentage(self, relationship_id: int) -> int:
        """Calculate (completed / total) * 100, or 0 if no milestones."""
        total, completed, _ = await self.get_milestone_counts(relationship_id)
        if total == 0:
            return 0
        return round((completed / total) * 100)

    # ------------------------------------------------------------------
    # MentorshipReview  (2.2)
    # ------------------------------------------------------------------

    async def _load_review(self, review_id: int) -> MentorshipReview | None:
        result = await self.db.execute(
            select(MentorshipReview)
            .options(
                joinedload(MentorshipReview.reviewer),
                joinedload(MentorshipReview.reviewee),
            )
            .where(MentorshipReview.id == review_id)
        )
        return result.scalar_one_or_none()

    async def get_review_for_relationship(self, relationship_id: int) -> MentorshipReview | None:
        result = await self.db.execute(
            select(MentorshipReview)
            .options(
                joinedload(MentorshipReview.reviewer),
                joinedload(MentorshipReview.reviewee),
            )
            .where(MentorshipReview.relationship_id == relationship_id)
        )
        return result.scalar_one_or_none()

    async def create_review(self, **data) -> MentorshipReview:
        review = MentorshipReview(**data)
        self.db.add(review)
        await self.db.commit()
        return await self._load_review(review.id)

    async def get_reviews_for_mentor(self, mentor_user_id: int) -> list[MentorshipReview]:
        """All reviews where reviewee = mentor_user_id (i.e. mentees reviewed this mentor)."""
        result = await self.db.execute(
            select(MentorshipReview)
            .options(
                joinedload(MentorshipReview.reviewer),
                joinedload(MentorshipReview.reviewee),
            )
            .where(MentorshipReview.reviewee_id == mentor_user_id)
            .order_by(MentorshipReview.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_mentor_rating(self, mentor_user_id: int) -> tuple[float | None, int]:
        """Return (average_rating, total_reviews) for a mentor."""
        result = await self.db.execute(
            select(func.avg(MentorshipReview.rating), func.count())
            .where(MentorshipReview.reviewee_id == mentor_user_id)
        )
        avg, total = result.one()
        return (round(float(avg), 1) if avg is not None else None, total)

    # ------------------------------------------------------------------
    # Stats queries  (2.4)
    # ------------------------------------------------------------------

    async def count_active_mentors_for_mentee(self, mentee_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(MentorshipRelationship)
            .where(
                MentorshipRelationship.mentee_id == mentee_id,
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
            )
        )
        return result.scalar_one()

    async def count_pending_requests_sent(self, mentee_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(MentorshipRequest)
            .where(
                MentorshipRequest.mentee_id == mentee_id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            )
        )
        return result.scalar_one()

    async def count_pending_requests_received(self, mentor_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(MentorshipRequest)
            .where(
                MentorshipRequest.mentor_id == mentor_id,
                MentorshipRequest.status == MentorshipRequestStatus.PENDING,
            )
        )
        return result.scalar_one()

    async def count_active_mentees_for_mentor(self, mentor_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(MentorshipRelationship)
            .where(
                MentorshipRelationship.mentor_id == mentor_id,
                MentorshipRelationship.status == MentorshipRelationshipStatus.ACTIVE,
            )
        )
        return result.scalar_one()

    async def sum_session_minutes_as_mentor(self, mentor_id: int) -> int:
        """Sum session_length_minutes from all completed sessions where user is mentor."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(MentorshipRelationship.session_length_minutes), 0))
            .select_from(MentorshipSession)
            .join(
                MentorshipRelationship,
                MentorshipSession.relationship_id == MentorshipRelationship.id,
            )
            .where(
                MentorshipRelationship.mentor_id == mentor_id,
                MentorshipSession.status == MentorshipSessionStatus.COMPLETED,
            )
        )
        return result.scalar_one()

    async def count_completed_sessions_as_participant(self, user_id: int) -> int:
        """Count completed sessions where user is either mentor or mentee."""
        result = await self.db.execute(
            select(func.count())
            .select_from(MentorshipSession)
            .join(
                MentorshipRelationship,
                MentorshipSession.relationship_id == MentorshipRelationship.id,
            )
            .where(
                MentorshipSession.status == MentorshipSessionStatus.COMPLETED,
                (
                    (MentorshipRelationship.mentor_id == user_id)
                    | (MentorshipRelationship.mentee_id == user_id)
                ),
            )
        )
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Helpers for match %  (2.3)
    # ------------------------------------------------------------------

    async def get_mentorship_preference(self, user_id: int) -> MentorshipPreference | None:
        result = await self.db.execute(
            select(MentorshipPreference).where(MentorshipPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_professional_profile(self, user_id: int) -> ProfessionalProfile | None:
        result = await self.db.execute(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
