from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authDependencies import get_current_user
from app.models.user import User
from app.schemas.event_dto import (
    EventCreateDto,
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
    response_model=list[EventSummaryResponse],
    summary="Get all upcoming events"
)
async def get_upcoming_events(
        event_type: EventType | None = Query(default=None, description="Filter by event type"),
        service: EventService = Depends(get_event_service),
):
    if event_type:
        return await service.get_events_by_type(event_type)
    return await service.get_upcoming_events()



@router.get(
    "/past",
    response_model=list[EventSummaryResponse],
    summary="Get all past events"
)
async def get_past_events(
        service: EventService = Depends(get_event_service),
):
    return await service.get_past_events()


@router.get("/rsvps", response_model=list[EventRegistrationResponse], summary="Get events rsvped by a user")
async def get_events_rsvped(
        current_user: User = Depends(get_current_user),
        service: EventService = Depends(get_event_service),
):
    return await service.get_user_rsvped_events(current_user.id)

@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Get a single event by ID"
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
    summary="Create a new event"
)
async def create_event(
        payload: EventCreateDto,
        current_user: User = Depends(get_current_user),
        service: EventService = Depends(get_event_service),
):
    # organizer_id comes from the auth token, not the request body
    return await service.create_event(
        organizer_id=current_user.id,
        data=payload.model_dump()
    )




@router.patch(
    "/{event_id}",
    response_model=EventResponse,
    summary="Update an event"
)
async def update_event(
        event_id: int,
        payload: EventUpdateDto,
        current_user: User = Depends(get_current_user),
        service: EventService = Depends(get_event_service),
):
    return await service.update_event(
        event_id=event_id,
        organizer_id=current_user.id,
        data=payload.model_dump(exclude_none=True)
    )


@router.post(
    "/{event_id}/rsvp",
    response_model=EventRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RSVP to an event"
)
async def rsvp_to_event(
        event_id: int,
        current_user: User = Depends(get_current_user),
        service: EventService = Depends(get_event_service),
):
    return await service.rsvp(event_id=event_id, user_id=current_user.id)


@router.delete(
    "/{event_id}/rsvp",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel RSVP"
)
async def cancel_rsvp(
        event_id: int,
        current_user: User = Depends(get_current_user),
        service: EventService = Depends(get_event_service),
):
    await service.cancel_rsvp(event_id=event_id, user_id=current_user.id)


