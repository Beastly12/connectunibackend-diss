
from sqlalchemy import (
    DateTime, ForeignKey,
    Enum as SAEnum, func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.event_registration_status import EventRegistrationStatus


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(EventRegistrationStatus, name="event_registration_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=EventRegistrationStatus.REGISTERED,
        nullable=False,
    )
    registered_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_registration"),)

    event = relationship("Event", back_populates="registrations")
    user = relationship("User")