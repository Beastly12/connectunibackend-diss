from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.enums.event_registration_status import EventRegistrationStatus
from fastapi import HTTPException, status


class EventRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    async def create(self, organizer_id: int, **data) -> Event:
        event = Event(organizer_id=organizer_id, **data)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_by_id(self, event_id: int) -> Event | None:
        result = await self.db.execute(
            select(Event)
            .options(joinedload(Event.organizer))
            .where(Event.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_upcoming(self) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .options(joinedload(Event.organizer))
            .where(
                Event.event_date > datetime.now(timezone.utc),
                Event.is_active == True,
            )
            .order_by(Event.event_date.asc())
        )
        return result.scalars().all()

    async def get_past(self) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .options(joinedload(Event.organizer))
            .where(Event.event_date <= datetime.now(timezone.utc))
            .order_by(Event.event_date.desc())
        )
        return result.scalars().all()

    async def get_upcoming_by_type(self, event_type: str) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .options(joinedload(Event.organizer))
            .where(
                Event.event_type == event_type,
                Event.event_date > datetime.now(timezone.utc),
                Event.is_active == True,
            )
            .order_by(Event.event_date.asc())
        )
        return result.scalars().all()

    async def get_by_organizer(self, organizer_id: int) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .options(joinedload(Event.organizer))
            .where(Event.organizer_id == organizer_id)
            .order_by(Event.event_date.desc())
        )
        return result.scalars().all()

    async def update(self, event: Event, data: dict) -> Event:
        for field, value in data.items():
            setattr(event, field, value)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    # ------------------------------------------------------------------
    # Registrations
    # ------------------------------------------------------------------

    async def create_registration_safe(
        self,
        event_id: int,
        user_id: int,
        max_attendees: int | None,
    ) -> EventRegistration:
        """
        Atomically checks for duplicate registration and capacity, then inserts.
        Uses SELECT FOR UPDATE to lock relevant rows and prevent race conditions
        when multiple users try to RSVP to the same event simultaneously.
        """
        async with self.db.begin_nested():
            # Guard 3: check for duplicate registration (locked)
            existing_result = await self.db.execute(
                select(EventRegistration)
                .where(
                    EventRegistration.event_id == event_id,
                    EventRegistration.user_id == user_id,
                )
                .with_for_update()
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You have already registered for this event.",
                )

            # Guard 4: check capacity (locked)
            if max_attendees is not None:
                count_result = await self.db.execute(
                    select(EventRegistration.id)
                    .where(
                        EventRegistration.event_id == event_id,
                        EventRegistration.status == EventRegistrationStatus.REGISTERED,
                    )
                    .with_for_update()
                )
                if len(count_result.scalars().all()) >= max_attendees:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This event is fully booked.",
                    )

            # Safe to insert
            registration = EventRegistration(
                event_id=event_id,
                user_id=user_id,
                status=EventRegistrationStatus.REGISTERED,
            )
            self.db.add(registration)
            await self.db.flush()
            await self.db.refresh(registration)
            return registration

    async def create_registration(self, event_id: int, user_id: int) -> EventRegistration:
        registration = EventRegistration(
            event_id=event_id,
            user_id=user_id,
            status=EventRegistrationStatus.REGISTERED,
        )
        self.db.add(registration)
        await self.db.commit()
        await self.db.refresh(registration)
        return registration

    async def get_registration(self, event_id: int, user_id: int) -> EventRegistration | None:
        result = await self.db.execute(
            select(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_registration_count(self, event_id: int) -> int:
        result = await self.db.execute(
            select(func.count(EventRegistration.id))
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == EventRegistrationStatus.REGISTERED,
            )
        )
        return result.scalar()

    async def get_registrations_by_event(self, event_id: int) -> list[EventRegistration]:
        result = await self.db.execute(
            select(EventRegistration)
            .where(EventRegistration.event_id == event_id)
        )
        return result.scalars().all()

    async def get_registrations_by_user(self, user_id: int) -> list[EventRegistration]:
        result = await self.db.execute(
            select(EventRegistration)
            .where(EventRegistration.user_id == user_id)
        )
        return result.scalars().all()

    async def delete_registration(self, registration: EventRegistration) -> None:
        await self.db.delete(registration)
        await self.db.commit()