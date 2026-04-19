from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile, status

from app.models.profile import Profile
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile_dto import ProfileCompletionResponse
from app.services.image_service import ImageService


# Each field has a weight (all weights sum to 100)
# Essential fields carry more weight than optional ones
COMPLETION_WEIGHTS: dict[str, int] = {
    "avatar_url":      15,
    "headline":        15,
    "bio":             15,
    "university":      10,
    "major":           10,
    "graduation_year": 10,
    "skills":          10,
    "interests":        5,
    "goals":            5,
    "company":          3,
    "job_title":        2,
}

# Human-readable labels shown to the frontend
FIELD_LABELS: dict[str, str] = {
    "avatar_url":      "Profile photo",
    "headline":        "Headline",
    "bio":             "Bio",
    "university":      "University",
    "major":           "Major / course",
    "graduation_year": "Graduation year",
    "skills":          "Skills",
    "interests":       "Interests",
    "goals":           "Goals",
    "company":         "Company",
    "job_title":       "Job title",
}


class ProfileService:

    def __init__(self, db: AsyncSession):
        self.repo = ProfileRepository(db)
        self.image_service = ImageService()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_profile(self, user_id: int, data: dict) -> Profile:
        # Prevent creating a second profile for the same user
        existing = await self.repo.get_by_user_id(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Profile already exists for this user.",
            )
        return await self.repo.create(user_id=user_id, **data)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_profile(self, user_id: int) -> Profile:
        profile = await self.repo.get_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found.",
            )
        return profile

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_profile(self, user_id: int, data: dict) -> Profile:
        profile = await self.repo.get_by_user_id(user_id)
        updates = {k: v for k, v in data.items() if v is not None}
        if not profile:
            # Auto-create if the profile row doesn't exist yet (e.g. legacy users)
            return await self.repo.create(user_id=user_id, **updates)
        return await self.repo.update(profile, updates)

    # ------------------------------------------------------------------
    # Avatar upload
    # ------------------------------------------------------------------

    async def update_avatar(self, user_id: int, file: UploadFile) -> Profile:
        profile = await self.repo.get_by_user_id(user_id)

        result = await self.image_service.upload(
            file=file,
            image_type="avatar",
            old_public_id=profile.avatar_public_id if profile else None,
        )

        if not profile:
            return await self.repo.create(user_id=user_id, avatar_url=result["url"], avatar_public_id=result["public_id"])

        return await self.repo.update(profile, {
            "avatar_url": result["url"],
            "avatar_public_id": result["public_id"],
        })

    async def delete_profile(self, user_id: int) -> None:
        profile = await self.repo.get_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found.",
            )
        await self.repo.delete(profile)

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    async def get_completion(self, user_id: int) -> ProfileCompletionResponse:
        profile = await self.repo.get_by_user_id(user_id)
        if not profile:
            return ProfileCompletionResponse(
                percentage=0,
                missing_fields=list(FIELD_LABELS.values()),
                completed_fields=[],
            )
        return self._calculate_completion(profile)

    def _calculate_completion(self, profile: Profile) -> ProfileCompletionResponse:
        completed_fields = []
        missing_fields = []
        total_percentage = 0

        for field, weight in COMPLETION_WEIGHTS.items():
            value = getattr(profile, field, None)

            # A JSONB list field (skills/interests) counts as complete only if it has items
            is_complete = (
                bool(value) if isinstance(value, list)
                else value is not None
            )

            if is_complete:
                completed_fields.append(FIELD_LABELS[field])
                total_percentage += weight
            else:
                missing_fields.append(FIELD_LABELS[field])

        return ProfileCompletionResponse(
            percentage=total_percentage,
            missing_fields=missing_fields,
            completed_fields=completed_fields,
        );

