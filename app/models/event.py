from sqlalchemy import (
    String, Boolean, DateTime, Integer, Text, ForeignKey,
    func, Enum as SAEnum, select, table, column, cast
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property

from app.core.database import Base
from app.enums.event_type import EventType

# Reference to event_registrations table without importing the model
# This avoids a circular import between event.py and event_registration.py
_registrations = table(
    "event_registrations",
    column("id"),
    column("event_id"),
    column("status"),
)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    organizer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(500))
    event_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(
        SAEnum(EventType, name="event_type_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    max_attendees: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    cover_image_public_id: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Computed — counts rows in event_registrations for this event
    # Cast the status column to text to avoid enum type mismatch in PostgreSQL
    attendee_count: Mapped[int] = column_property(
        select(func.count(_registrations.c.id))
        .where(_registrations.c.event_id == id)
        .where(cast(_registrations.c.status, String) == "registered")
        .correlate_except(_registrations)
        .scalar_subquery()
    )

    organizer = relationship("User")
    registrations = relationship("EventRegistration", back_populates="event")