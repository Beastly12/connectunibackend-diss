from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.enums.event_type import EventType
from app.enums.event_registration_status import EventRegistrationStatus

# ------------------------------------------------------------------
# Base — shared fields, no validation logic here
# ------------------------------------------------------------------

class EventBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    location: str = Field(..., min_length=2, max_length=500)
    event_date: datetime = Field(...)
    event_type: EventType = Field(...)
    max_attendees: int | None = Field(default=None, ge=10)


# ------------------------------------------------------------------
# Create — what the client sends when creating an event
# organizer_id is injected from the auth token, not the request body
# ------------------------------------------------------------------

class EventCreateDto(EventBase):

    @field_validator("event_date")
    @classmethod
    def event_date_must_be_future(cls, v: datetime) -> datetime:
        if v <= datetime.now(v.tzinfo):
            raise ValueError("Event date must be in the future.")
        return v

    @field_validator("max_attendees")
    @classmethod
    def max_attendees_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 10:
            raise ValueError("max_attendees must be at least 10.")
        return v


# ------------------------------------------------------------------
# Update — all fields optional so partial updates are supported
# ------------------------------------------------------------------

class EventUpdateDto(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    location: str | None = Field(default=None, min_length=2, max_length=500)
    event_date: datetime | None = Field(default=None)
    event_type: EventType | None = Field(default=None)
    max_attendees: int | None = Field(default=None, gt=0)
    is_active: bool | None = Field(default=None)

    @field_validator("event_date")
    @classmethod
    def event_date_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is not None and v <= datetime.now(v.tzinfo):
            raise ValueError("Event date must be in the future.")
        return v


# ------------------------------------------------------------------
# Response — what the API returns to the client
# ------------------------------------------------------------------

class OrganizerSummary(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    id: int
    organizer_id: int
    organizer: OrganizerSummary
    title: str
    description: str
    location: str
    event_date: datetime
    event_type: EventType
    max_attendees: int | None
    is_active: bool
    cover_image_url: str | None
    cover_image_public_id: str | None
    created_at: datetime
    attendee_count: int = Field(default=0)

    model_config = {"from_attributes": True}


class EventSummaryResponse(BaseModel):
    """Lightweight version for lists and cards on the events screen."""
    id: int
    title: str
    event_type: EventType
    event_date: datetime
    location: str
    organizer: OrganizerSummary
    attendee_count: int = Field(default=0)
    max_attendees: int | None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Event Registration
# ------------------------------------------------------------------

class EventRegistrationResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    status: EventRegistrationStatus
    registered_at: datetime

    model_config = {"from_attributes": True}