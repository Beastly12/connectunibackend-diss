from sqlalchemy import (
    String, Boolean, DateTime, Integer, Text, ForeignKey,
    func, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.event_type import EventType


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
        SAEnum(EventType, name="event_type_enum"), nullable=False
    )
    max_attendees: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    cover_image_public_id: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organizer = relationship("User")
    registrations = relationship("EventRegistration", back_populates="event")
