from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.enums.preferred_format import PreferredFormat
from app.enums.verification_status import VerificationStatus


# ---------------------------------------------------------------------------
# Student profile
# ---------------------------------------------------------------------------

class StudentProfileCreate(BaseModel):
    university_name: str = Field(..., min_length=2, max_length=255)
    course_title: str = Field(..., min_length=2, max_length=255)
    year_of_study: int = Field(..., ge=1, le=10)
    expected_graduation: int = Field(..., ge=2024, le=2040)


class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    university_name: str
    course_title: str
    year_of_study: int
    expected_graduation: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Alumni profile
# ---------------------------------------------------------------------------

class AlumniProfileCreate(BaseModel):
    university_name: str = Field(..., min_length=2, max_length=255)
    course_completed: str = Field(..., min_length=2, max_length=255)
    graduation_year: int = Field(..., le=2025)


class AlumniProfileResponse(BaseModel):
    id: int
    user_id: int
    university_name: str
    course_completed: str
    graduation_year: int
    certificate_url: str | None
    certificate_uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Professional profile
# ---------------------------------------------------------------------------

class ProfessionalProfileCreate(BaseModel):
    job_title: str = Field(..., min_length=2, max_length=255)
    company: str = Field(..., min_length=2, max_length=255)
    industry_sector: str = Field(..., min_length=2, max_length=255)
    years_of_experience: int = Field(..., ge=0, le=60)
    linkedin_url: str | None = Field(default=None, max_length=500)


class ProfessionalProfileResponse(BaseModel):
    id: int
    user_id: int
    job_title: str
    company: str
    industry_sector: str
    years_of_experience: int
    linkedin_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Mentorship preferences
# ---------------------------------------------------------------------------

class MentorshipPreferenceCreate(BaseModel):
    is_mentor: bool = False
    is_mentee: bool = False
    areas_of_interest: list[str] = Field(default_factory=list)
    availability_hours_per_week: int = Field(..., ge=1, le=168)
    preferred_format: PreferredFormat

    @field_validator("areas_of_interest")
    @classmethod
    def at_least_one_area(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Provide at least one area of interest.")
        return v

    @model_validator(mode="after")
    def must_be_mentor_or_mentee(self) -> MentorshipPreferenceCreate:
        if not self.is_mentor and not self.is_mentee:
            raise ValueError("Must be a mentor, a mentee, or both.")
        return self


class MentorshipPreferenceResponse(BaseModel):
    id: int
    user_id: int
    is_mentor: bool
    is_mentee: bool
    areas_of_interest: list[str]
    availability_hours_per_week: int
    preferred_format: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Full profile response (GET /profile/me)
# ---------------------------------------------------------------------------

class FullProfileResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    verification_status: str
    is_verified: bool
    student_profile: StudentProfileResponse | None = None
    alumni_profile: AlumniProfileResponse | None = None
    professional_profile: ProfessionalProfileResponse | None = None
    mentorship_preferences: MentorshipPreferenceResponse | None = None


# ---------------------------------------------------------------------------
# Verification status update (admin)
# ---------------------------------------------------------------------------

class VerificationUpdateRequest(BaseModel):
    verification_status: VerificationStatus
