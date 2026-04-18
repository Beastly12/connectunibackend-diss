from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Form, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.event_dto import (
    EventUpdateDto,
    EventResponse,
    EventSummaryResponse,
    EventRegistrationResponse,
)
from app.enums.event_type import EventType
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["Events"])


def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(db)


@router.get(
    "/",
    response_model=list[EventResponse],
    summary="Get all upcoming events",
)
async def get_upcoming_events(
    event_type: str | None = Query(default=None, description="Filter by event type (e.g. academic, social, career, networking)"),
    service: EventService = Depends(get_event_service),
):
    if event_type:
        try:
            normalised = EventType(event_type.lower())
        except ValueError:
            normalised = EventType(event_type)  # let Pydantic raise the proper 422
        return await service.get_events_by_type(normalised)
    return await service.get_upcoming_events()


@router.get(
    "/past",
    response_model=list[EventSummaryResponse],
    summary="Get all past events",
)
async def get_past_events(
    service: EventService = Depends(get_event_service),
):
    return await service.get_past_events()


@router.get(
    "/rsvps",
    response_model=list[EventRegistrationResponse],
    summary="Get events RSVPd by the authenticated user",
)
async def get_events_rsvped(
    current_user: User = Depends(get_current_user),
    service: EventService = Depends(get_event_service),
):
    return await service.get_user_rsvped_events(current_user.id)


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Get a single event by ID",
)
async def get_event(
    event_id: int,
    service: EventService = Depends(get_event_service),
):
    return await service.get_event_by_id(event_id)


@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
)
async def create_event(
    # All fields sent as multipart/form-data so an optional image can be included
    title: str = Form(..., min_length=3, max_length=255),
    description: str = Form(..., min_length=10),
    location: str = Form(..., min_length=2, max_length=500),
    event_date: datetime = Form(...),
    event_type: EventType = Form(...),
    max_attendees: Optional[int] = Form(default=None, ge=10),
    cover_image: Optional[UploadFile] = File(default=None, description="Optional cover image — JPEG, PNG, WebP or GIF, max 10MB"),
    current_user: User = Depends(get_current_user),
    service: EventService = Depends(get_event_service),
):
    data = {
        "title": title,
        "description": description,
        "location": location,
        "event_date": event_date,
        "event_type": event_type,
        "max_attendees": max_attendees,
    }
    return await service.create_event(
        organizer_id=current_user.id,
        data=data,
        cover_image=cover_image,
    )


@router.patch(
    "/{event_id}",
    response_model=EventResponse,
    summary="Update an event",
)
async def update_event(
    event_id: int,
    payload: EventUpdateDto,
    current_user: User = Depends(get_current_user),
    service: EventService = Depends(get_event_service),
):
    return await service.update_event(
        event_id=event_id,
        user_id=current_user.id,
        data=payload.model_dump(exclude_none=True),
    )


@router.put(
    "/{event_id}/cover-image",
    response_model=EventResponse,
    summary="Upload or replace an event cover image",
)
async def update_cover_image(
    event_id: int,
    file: UploadFile = File(..., description="Image file — JPEG, PNG, WebP or GIF, max 10MB"),
    current_user: User = Depends(get_current_user),
    service: EventService = Depends(get_event_service),
):
    return await service.update_cover_image(
        event_id=event_id,
        user_id=current_user.id,
        file=file,
    )


@router.post(
    "/{event_id}/rsvp",
    response_model=EventRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RSVP to an event",
)
async def rsvp_to_event(
    event_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: EventService = Depends(get_event_service),
):
    return await service.rsvp(
        event_id=event_id,
        user_id=current_user.id,
        user_email=current_user.email,
        user_full_name=current_user.full_name,
        background_tasks=background_tasks,
    )


@router.delete(
    "/{event_id}/rsvp",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel RSVP",
)
async def cancel_rsvp(
    event_id: int,
    current_user: User = Depends(get_current_user),
    service: EventService = Depends(get_event_service),
):
    await service.cancel_rsvp(event_id=event_id, user_id=current_user.id)