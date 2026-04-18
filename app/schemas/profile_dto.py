from pydantic import BaseModel, field_validator, Field, model_validator
from typing import Annotated, Any

StrField = Annotated[str, Field(min_length=1, strict=False)] | None

class ProfileCreateDto(BaseModel):
    headline: StrField = None
    bio: StrField = None
    university: StrField = None
    major: StrField = None
    company: StrField = None
    job_title: StrField = None
    goals: StrField = None
    graduation_year: int | None = None
    skills: list[Any] | None = None
    interests: list[Any] | None = None

    @field_validator("headline", "bio", "university", "major", "company", "job_title", "goals")
    @classmethod
    def reject_empty_strings(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError("This field cannot be an empty or whitespace-only string")
        return v

class ProfileUpdateDto(BaseModel):
    # avatar_url is intentionally excluded — set via PUT /profiles/me/avatar
    headline: StrField = None
    bio: StrField = None
    university: StrField = None
    graduation_year: int | None = None
    major: StrField = None
    company: StrField = None
    job_title: StrField = None
    goals: StrField = None
    skills: list[Any] | None = None
    interests: list[Any] | None = None

    @field_validator("headline", "bio", "university", "major", "company", "job_title", "goals")
    @classmethod
    def reject_empty_strings(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError("This field cannot be an empty or whitespace-only string")
        return v


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str | None = None
    avatar_url: str | None        # set by image service after Cloudinary upload
    avatar_public_id: str | None  # needed internally for deletion on replace
    headline: str | None
    bio: str | None
    university: str | None
    graduation_year: int | None
    major: str | None
    company: str | None
    job_title: str | None
    goals: str | None
    skills: list[Any] | None
    interests: list[Any] | None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_full_name(cls, data: Any) -> Any:
        if not isinstance(data, dict) and hasattr(data, "user") and data.user is not None:
            data.full_name = data.user.full_name
        return data


class ProfileCompletionResponse(BaseModel):
    percentage: int
    missing_fields: list[str]
    completed_fields: list[str]