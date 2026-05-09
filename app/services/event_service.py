from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from typing import Optional

from app.enums.notification_type import NotificationType
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.repositories.event_repository import EventRepository
from app.services.activity_service import ActivityService
from app.services.image_service import ImageService
from app.services.notification_service import NotificationService
from app.tasks.email_tasks import send_rsvp_confirmation_email


class EventService:

    def __init__(self, db: AsyncSession):
        self.repo = EventRepository(db)
        self.activity = ActivityService(db)
        self.notifications = NotificationService(db)
        self.image_service = ImageService()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_event(
        self,
        organizer_id: int,
        data: dict,
        cover_image: Optional[UploadFile] = None,
    ) -> Event:
        # Guard: organizer cannot have two events on the same date
        existing_events = await self.repo.get_by_organizer(organizer_id)
        for event in existing_events:
            if event.event_date.date() == data["event_date"].date():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You already have an event scheduled on this date.",
                )

        # Upload cover image if provided
        if cover_image:
            result = await self.image_service.upload(
                file=cover_image,
                image_type="event_cover",
            )
            data["cover_image_url"] = result["url"]
            data["cover_image_public_id"] = result["public_id"]

        return await self.repo.create(organizer_id=organizer_id, **data)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_upcoming_events(self) -> list[Event]:
        """Returns only events that haven't happened yet — used on the home/events screen."""
        return await self.repo.get_upcoming()

    async def get_past_events(self) -> list[Event]:
        """Returns events that have already passed — shown in a separate Past Events section."""
        return await self.repo.get_past()

    async def get_event_by_id(self, event_id: int) -> Event:
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found.",
            )
        return event

    async def get_events_by_type(self, event_type: str) -> list[Event]:
        """Supports the Academic / Social / Career / Networking filter tabs."""
        return await self.repo.get_upcoming_by_type(event_type)

    async def get_events_created_by(self, user_id: int) -> list[Event]:
        return await self.repo.get_by_organizer(user_id)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_event(self, event_id: int, user_id: int, data: dict) -> Event:
        event = await self.get_event_by_id(event_id)

        if event.organizer_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this event.",
            )

        updates = {k: v for k, v in data.items() if v is not None}
        return await self.repo.update(event, updates)

    # ------------------------------------------------------------------
    # Cover image
    # ------------------------------------------------------------------

    async def update_cover_image(self, event_id: int, user_id: int, file: UploadFile) -> Event:
        event = await self.get_event_by_id(event_id)

        if event.organizer_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this event.",
            )

        result = await self.image_service.upload(
            file=file,
            image_type="event_cover",
            old_public_id=event.cover_image_public_id,
        )

        return await self.repo.update(event, {
            "cover_image_url": result["url"],
            "cover_image_public_id": result["public_id"],
        })

    # ------------------------------------------------------------------
    # RSVP
    # ------------------------------------------------------------------

    async def rsvp(
        self,
        event_id: int,
        user_id: int,
        user_email: str,
        user_full_name: str,
        background_tasks: BackgroundTasks,
    ) -> EventRegistration:
        event = await self.get_event_by_id(event_id)

        # Guard 1: organizer cannot RSVP to their own event
        if event.organizer_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot RSVP to an event you organised.",
            )

        # Guard 2: cannot RSVP to a past event
        # Normalise event_date: SQLite returns naive datetimes even for timezone=True columns.
        event_date = event.event_date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        if event_date <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot RSVP to an event that has already passed.",
            )

        # Guards 3 & 4 are handled atomically inside the repository
        # using SELECT FOR UPDATE to prevent race conditions on duplicate
        # registrations and capacity overbooking.
        registration = await self.repo.create_registration_safe(
            event_id=event_id,
            user_id=user_id,
            max_attendees=event.max_attendees,
        )

        # Notify the event organiser
        try:
            if event.organizer_id != user_id:
                await self.notifications.send(
                    recipient_id=event.organizer_id,
                    notification_type=NotificationType.EVENT_RSVP,
                    sender_id=user_id,
                    reference_id=event_id,
                )
        except Exception:
            pass

        # Schedule side effects after response is sent — no user-facing latency
        background_tasks.add_task(
            self.activity.log_rsvp,
            user_id=user_id,
            event_id=event_id,
            event_title=event.title,
        )
        first_name = user_full_name.split()[0]
        background_tasks.add_task(
            send_rsvp_confirmation_email,
            to_email=user_email,
            first_name=first_name,
            event_title=event.title,
            event_date=event.event_date,
            event_location=event.location,
        )

        return registration

    # ------------------------------------------------------------------
    # Cancel RSVP
    # ------------------------------------------------------------------

    async def cancel_rsvp(self, event_id: int, user_id: int) -> None:
        event = await self.get_event_by_id(event_id)

        event_date = event.event_date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        if event_date <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel registration for a past event.",
            )

        registration = await self.repo.get_registration(event_id=event_id, user_id=user_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not registered for this event.",
            )

        await self.repo.delete_registration(registration)

        # Log activity
        await self.activity.log_cancelled_rsvp(
            user_id=user_id,
            event_id=event_id,
            event_title=event.title,
        )

    async def get_user_rsvped_events(self, user_id: int) -> list[EventRegistration]:
        return await self.repo.get_registrations_by_user(user_id)