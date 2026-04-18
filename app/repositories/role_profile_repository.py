from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_profile import StudentProfile
from app.models.alumni_profile import AlumniProfile
from app.models.professional_profile import ProfessionalProfile
from app.models.mentorship_preference import MentorshipPreference
from app.models.user import User
from app.enums.verification_status import VerificationStatus


class RoleProfileRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Student profile
    # ------------------------------------------------------------------

    async def get_student_profile(self, user_id: int) -> StudentProfile | None:
        result = await self.db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_student_profile(self, user_id: int, **data) -> StudentProfile:
        profile = await self.get_student_profile(user_id)
        if profile:
            for key, value in data.items():
                setattr(profile, key, value)
        else:
            profile = StudentProfile(user_id=user_id, **data)
            self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    # ------------------------------------------------------------------
    # Alumni profile
    # ------------------------------------------------------------------

    async def get_alumni_profile(self, user_id: int) -> AlumniProfile | None:
        result = await self.db.execute(
            select(AlumniProfile).where(AlumniProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_alumni_profile(self, user_id: int, **data) -> AlumniProfile:
        profile = await self.get_alumni_profile(user_id)
        if profile:
            for key, value in data.items():
                setattr(profile, key, value)
        else:
            profile = AlumniProfile(user_id=user_id, **data)
            self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    # ------------------------------------------------------------------
    # Professional profile
    # ------------------------------------------------------------------

    async def get_professional_profile(self, user_id: int) -> ProfessionalProfile | None:
        result = await self.db.execute(
            select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_professional_profile(self, user_id: int, **data) -> ProfessionalProfile:
        profile = await self.get_professional_profile(user_id)
        if profile:
            for key, value in data.items():
                setattr(profile, key, value)
        else:
            profile = ProfessionalProfile(user_id=user_id, **data)
            self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    # ------------------------------------------------------------------
    # Mentorship preferences
    # ------------------------------------------------------------------

    async def get_mentorship_preference(self, user_id: int) -> MentorshipPreference | None:
        result = await self.db.execute(
            select(MentorshipPreference).where(MentorshipPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_mentorship_preference(self, user_id: int, **data) -> MentorshipPreference:
        pref = await self.get_mentorship_preference(user_id)
        if pref:
            for key, value in data.items():
                setattr(pref, key, value)
        else:
            pref = MentorshipPreference(user_id=user_id, **data)
            self.db.add(pref)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    # ------------------------------------------------------------------
    # User verification status
    # ------------------------------------------------------------------

    async def set_verification_status(
        self, user_id: int, status: VerificationStatus
    ) -> User | None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(verification_status=status)
        )
        await self.db.commit()
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
