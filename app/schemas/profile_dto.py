from pydantic import BaseModel
from typing import Any


class ProfileCreateDto(BaseModel):
    # avatar_url is intentionally excluded — set via PUT /profiles/me/avatar
    headline: str | None = None
    bio: str | None = None
    university: str | None = None
    graduation_year: int | None = None
    major: str | None = None
    company: str | None = None
    job_title: str | None = None
    goals: str | None = None
    skills: list[Any] | None = None
    interests: list[Any] | None = None


class ProfileUpdateDto(BaseModel):
    # avatar_url is intentionally excluded — set via PUT /profiles/me/avatar
    headline: str | None = None
    bio: str | None = None
    university: str | None = None
    graduation_year: int | None = None
    major: str | None = None
    company: str | None = None
    job_title: str | None = None
    goals: str | None = None
    skills: list[Any] | None = None
    interests: list[Any] | None = None


class ProfileResponse(BaseModel):
    id: int
    user_id: int
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


class ProfileCompletionResponse(BaseModel):
    percentage: int
    missing_fields: list[str]
    completed_fields: list[str]