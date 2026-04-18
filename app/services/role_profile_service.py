from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.verification_status import VerificationStatus
from app.models.alumni_profile import AlumniProfile
from app.models.mentorship_preference import MentorshipPreference
from app.models.professional_profile import ProfessionalProfile
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.repositories.role_profile_repository import RoleProfileRepository
from app.schemas.role_profile_schema import (
    AlumniProfileResponse,
    FullProfileResponse,
    MentorshipPreferenceResponse,
    ProfessionalProfileResponse,
    StudentProfileResponse,
)
from app.services.image_service import ImageService
from app.tasks.email_tasks import (
    send_certificate_received_email,
    send_mentorship_preferences_email,
    send_verification_status_update_email,
)


class RoleProfileService:

    def __init__(self, db: AsyncSession):
        self.repo = RoleProfileRepository(db)
        self.image_service = ImageService()

    # ------------------------------------------------------------------
    # Student profile
    # ------------------------------------------------------------------

    async def save_student_profile(
        self, user: User, data: dict
    ) -> StudentProfile:
        """Create or update the student profile for the authenticated user."""
        profile = await self.repo.upsert_student_profile(user_id=user.id, **data)
        return profile

    # ------------------------------------------------------------------
    # Alumni profile
    # ------------------------------------------------------------------

    async def save_alumni_profile(
        self,
        user: User,
        data: dict,
        certificate: UploadFile | None = None,
    ) -> AlumniProfile:
        """Create or update the alumni profile, handling optional certificate upload."""
        extra: dict = {}

        if certificate:
            uploaded = await self.image_service.upload(
                file=certificate, image_type="document"
            )
            extra["certificate_url"] = uploaded["url"]
            extra["certificate_public_id"] = uploaded["public_id"]
            extra["certificate_uploaded_at"] = datetime.now(timezone.utc)

            # Move verification status to pending
            await self.repo.set_verification_status(
                user.id, VerificationStatus.PENDING
            )

            # Notify alumni that certificate is under review
            first_name = user.full_name.split()[0]
            try:
                send_certificate_received_email(
                    to_email=user.email, first_name=first_name
                )
            except Exception:
                pass

        profile = await self.repo.upsert_alumni_profile(
            user_id=user.id, **data, **extra
        )
        return profile

    # ------------------------------------------------------------------
    # Professional profile
    # ------------------------------------------------------------------

    async def save_professional_profile(
        self, user: User, data: dict
    ) -> ProfessionalProfile:
        """Create or update the professional profile and mark as self-declared."""
        profile = await self.repo.upsert_professional_profile(user_id=user.id, **data)

        # Professionals are always self-declared
        await self.repo.set_verification_status(
            user.id, VerificationStatus.SELF_DECLARED
        )
        return profile

    # ------------------------------------------------------------------
    # Mentorship preferences
    # ------------------------------------------------------------------

    async def set_mentorship_preferences(
        self, user: User, data: dict
    ) -> MentorshipPreference:
        """Save mentorship preferences and send a summary email."""
        pref = await self.repo.upsert_mentorship_preference(user_id=user.id, **data)

        first_name = user.full_name.split()[0]
        try:
            send_mentorship_preferences_email(
                to_email=user.email,
                first_name=first_name,
                is_mentor=pref.is_mentor,
                is_mentee=pref.is_mentee,
                areas=pref.areas_of_interest or [],
                hours_per_week=pref.availability_hours_per_week,
                preferred_format=pref.preferred_format,
            )
        except Exception:
            pass

        return pref

    # ------------------------------------------------------------------
    # Full profile
    # ------------------------------------------------------------------

    async def get_full_profile(self, user: User) -> FullProfileResponse:
        """Return the full profile including role-specific data and mentorship prefs."""
        student = await self.repo.get_student_profile(user.id)
        alumni = await self.repo.get_alumni_profile(user.id)
        professional = await self.repo.get_professional_profile(user.id)
        pref = await self.repo.get_mentorship_preference(user.id)

        return FullProfileResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.user_role,
            verification_status=user.verification_status,
            is_verified=user.is_verified,
            student_profile=StudentProfileResponse.model_validate(student) if student else None,
            alumni_profile=AlumniProfileResponse.model_validate(alumni) if alumni else None,
            professional_profile=ProfessionalProfileResponse.model_validate(professional) if professional else None,
            mentorship_preferences=MentorshipPreferenceResponse.model_validate(pref) if pref else None,
        )

    # ------------------------------------------------------------------
    # Admin: update verification status
    # ------------------------------------------------------------------

    async def update_verification_status(
        self,
        target_user_id: int,
        new_status: VerificationStatus,
        admin: User,
    ) -> User:
        """Admin-only: update a user's verification status and notify them."""
        if admin.user_role not in ("ADMIN", "STAFF"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        user = await self.repo.set_verification_status(target_user_id, new_status)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        first_name = user.full_name.split()[0]
        try:
            send_verification_status_update_email(
                to_email=user.email,
                first_name=first_name,
                new_status=new_status.value,
            )
        except Exception:
            pass

        return user
