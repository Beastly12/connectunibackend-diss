from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.repositories.event_repository import EventRepository


class EventService:

    def __init__(self, db: AsyncSession):
        self.repo = EventRepository(db)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_event(self, organizer_id: int, data: dict) -> Event:
        # Check if organizer already has an event on the same date
        existing_events = await self.repo.get_by_organizer(organizer_id)
        for event in existing_events:
            if event.event_date.date() == data["event_date"].date():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You already have an event scheduled on this date."
                )

        return await self.repo.create(organizer_id=organizer_id, **data)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_upcoming_events(self) -> list[Event]:
        """Returns only events that haven't happened yet — used on the home/events screen."""
        return await self.repo.get_upcoming()

    async def get_past_events(self) -> list[Event]:
        """Returns events that have already passed — shown in a separate 'Past Events' section."""
        return await self.repo.get_past()

    async def get_event_by_id(self, event_id: int) -> Event:
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found."
            )
        return event

    async def get_events_by_type(self, event_type: str) -> list[Event]:
        """Supports the Academic / Social / Career / Networking filter tabs."""
        return await self.repo.get_upcoming_by_type(event_type)

    async def get_events_created_by(self, user_id: int) -> list[Event]:
        return await self.repo.get_by_organizer(user_id)

    # ------------------------------------------------------------------
    # RSVP
    # ------------------------------------------------------------------

    async def rsvp(self, event_id: int, user_id: int) -> EventRegistration:
        event = await self.get_event_by_id(event_id)

        # Guard 1: cannot RSVP to a past event
        if event.event_date <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot RSVP to an event that has already passed."
            )

        # Guard 2: cannot RSVP twice
        existing = await self.repo.get_registration(event_id=event_id, user_id=user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already registered for this event."
            )

        # Guard 3: check capacity if a max is set
        if event.max_attendees is not None:
            current_count = await self.repo.get_registration_count(event_id)
            if current_count >= event.max_attendees:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This event is fully booked."
                )

        return await self.repo.create_registration(event_id=event_id, user_id=user_id)

    # ------------------------------------------------------------------
    # Cancel RSVP
    # ------------------------------------------------------------------

    async def cancel_rsvp(self, event_id: int, user_id: int) -> None:
        event = await self.get_event_by_id(event_id)

        if event.event_date <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel registration for a past event."
            )

        registration = await self.repo.get_registration(event_id=event_id, user_id=user_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not registered for this event."
            )

        await self.repo.delete_registration(registration)

    async def get_user_rsvped_events(self, user_id: int) -> list[EventRegistration]:
        return await self.repo.get_registrations_by_user(user_id)