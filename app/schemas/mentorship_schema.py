from datetime import datetime, date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.enums.mentorship_request_status import MentorshipRequestStatus
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus
from app.enums.mentorship_session_status import MentorshipSessionStatus
from app.enums.milestone_status import MilestoneStatus

ALLOWED_RESOURCE_CATEGORIES = {"Article", "Video", "Career Guide", "Interview"}


# ------------------------------------------------------------------
# Shared nested user summary
# ------------------------------------------------------------------

class MentorUserSummary(BaseModel):
    id: int
    full_name: str
    university_name: str

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def map_university(cls, data: Any) -> Any:
        if not isinstance(data, dict) and hasattr(data, "university"):
            data.university_name = data.university
        return data


class SharedBySummary(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mentor Profile
# ------------------------------------------------------------------

class MentorProfileCreate(BaseModel):
    bio: str | None = None
    linkedin_url: str | None = None
    expertise_areas: list[str] = Field(default_factory=list)
    mentorship_goals: list[str] = Field(default_factory=list)
    availability_slots: list[dict] | None = None
    max_mentees: int = Field(default=5, ge=1)


class MentorProfileUpdate(BaseModel):
    bio: str | None = None
    linkedin_url: str | None = None
    expertise_areas: list[str] | None = None
    mentorship_goals: list[str] | None = None
    availability_slots: list[dict] | None = None
    max_mentees: int | None = Field(default=None, ge=1)


class MentorProfileResponse(BaseModel):
    id: int
    user_id: int
    user: MentorUserSummary
    bio: str | None
    linkedin_url: str | None
    expertise_areas: list[str]
    mentorship_goals: list[str]
    availability_slots: list[dict] | None
    max_mentees: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Computed fields — populated by the service, not from DB columns
    average_rating: float | None = None
    total_reviews: int = 0
    match_percentage: int | None = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mentorship Request
# ------------------------------------------------------------------

class MentorshipRequestCreate(BaseModel):
    mentor_id: int
    goal: str = Field(..., min_length=1, max_length=500)
    meeting_frequency: str = Field(..., min_length=1, max_length=100)
    session_length_minutes: int = Field(..., ge=15)
    message: str = Field(..., min_length=1)

    @field_validator("goal", "meeting_frequency", "message")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class MentorshipRequestResponse(BaseModel):
    id: int
    mentee_id: int
    mentor_id: int
    mentee: MentorUserSummary
    mentor: MentorUserSummary
    goal: str
    meeting_frequency: str
    session_length_minutes: int
    message: str
    status: MentorshipRequestStatus
    attachment_file_path: str | None = None
    created_at: datetime
    # Computed — only populated on incoming requests list for the mentor
    match_percentage: int | None = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mentorship Relationship
# ------------------------------------------------------------------

class MentorshipRelationshipResponse(BaseModel):
    id: int
    mentor_id: int
    mentee_id: int
    mentor: MentorUserSummary
    mentee: MentorUserSummary
    goal: str
    meeting_frequency: str
    session_length_minutes: int
    status: MentorshipRelationshipStatus
    started_at: datetime
    ended_at: datetime | None
    # Computed from milestones — populated by service
    progress_percentage: int = 0

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mentorship Session
# ------------------------------------------------------------------

class MentorshipSessionCreate(BaseModel):
    scheduled_at: datetime
    notes: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if aware <= now:
            raise ValueError("scheduled_at must be in the future.")
        return v


class MentorshipSessionUpdate(BaseModel):
    scheduled_at: datetime | None = None
    notes: str | None = None
    status: MentorshipSessionStatus | None = None

    @field_validator("scheduled_at")
    @classmethod
    def must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        from datetime import timezone
        now = datetime.now(timezone.utc)
        aware = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if aware <= now:
            raise ValueError("scheduled_at must be in the future.")
        return v


class MentorshipSessionResponse(BaseModel):
    id: int
    relationship_id: int
    scheduled_at: datetime
    notes: str | None
    status: MentorshipSessionStatus
    created_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mentorship Resource
# ------------------------------------------------------------------

class MentorshipResourceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    category: str
    url: str = Field(..., min_length=1, max_length=2000)
    note: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.strip()
        if v not in ALLOWED_RESOURCE_CATEGORIES:
            raise ValueError(
                f"category must be one of: {', '.join(sorted(ALLOWED_RESOURCE_CATEGORIES))}"
            )
        return v

    @field_validator("title", "url")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class MentorshipResourceResponse(BaseModel):
    id: int
    relationship_id: int
    shared_by_id: int
    shared_by: SharedBySummary
    title: str
    category: str
    url: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mentorship Milestones  (2.1)
# ------------------------------------------------------------------

class MilestoneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    sort_order: int = Field(default=0, ge=0)
    target_date: date | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: MilestoneStatus | None = None
    sort_order: int | None = Field(default=None, ge=0)
    target_date: date | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class MilestoneResponse(BaseModel):
    id: int
    relationship_id: int
    title: str
    description: str | None
    status: MilestoneStatus
    sort_order: int
    target_date: date | None
    completed_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mentorship Reviews  (2.2)
# ------------------------------------------------------------------

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review_text: str | None = None


class ReviewResponse(BaseModel):
    id: int
    relationship_id: int
    reviewer_id: int
    reviewee_id: int
    reviewer_name: str
    rating: int
    review_text: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MentorRatingResponse(BaseModel):
    user_id: int
    average_rating: float | None
    total_reviews: int


# ------------------------------------------------------------------
# Dashboard stats  (2.4)
# ------------------------------------------------------------------

class UpcomingSessionSummary(BaseModel):
    session_id: int
    mentor_or_mentee_name: str
    title: str | None
    scheduled_at: datetime
    relationship_id: int


class DashboardStatsResponse(BaseModel):
    messages_unread: int
    upcoming_events: int
    upcoming_sessions: list[UpcomingSessionSummary]


# ------------------------------------------------------------------
# Mentorship stats  (2.4)
# ------------------------------------------------------------------

class MenteeStatsResponse(BaseModel):
    active_mentors: int
    pending_requests_sent: int
    completed_sessions: int
    overall_progress: int


class MentorStatsResponse(BaseModel):
    active_mentees: int
    pending_requests_received: int
    total_hours_mentored: float
    resources_shared: int
    total_sessions_completed: int
    average_rating: float | None
    total_reviews: int


class MentorshipStatsResponse(BaseModel):
    as_mentee: MenteeStatsResponse
    as_mentor: MentorStatsResponse


# ------------------------------------------------------------------
# Rich my-mentors / my-mentees  (2.4)
# ------------------------------------------------------------------

class MilestoneSummary(BaseModel):
    total: int
    completed: int
    in_progress: int


class MentorSummaryInRelationship(BaseModel):
    user_id: int
    name: str
    role: str
    job_title: str | None
    company: str | None
    avatar_url: str | None
    verification_status: str


class MyMentorResponse(BaseModel):
    relationship_id: int
    mentor: MentorSummaryInRelationship
    status: str
    started_at: datetime
    progress_percentage: int
    next_session: MentorshipSessionResponse | None
    milestone_summary: MilestoneSummary


class MenteeSummaryInRelationship(BaseModel):
    user_id: int
    name: str
    role: str
    avatar_url: str | None
    verification_status: str


class MyMenteeResponse(BaseModel):
    relationship_id: int
    mentee: MenteeSummaryInRelationship
    status: str
    started_at: datetime
    progress_percentage: int
    next_session: MentorshipSessionResponse | None
    milestone_summary: MilestoneSummary
