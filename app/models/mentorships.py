
from sqlalchemy import (
    DateTime, Text, ForeignKey,
    Enum as SAEnum, func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.mentorship_status import MentorshipStatus


class Mentorship(Base):
    __tablename__ = "mentorships"

    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mentee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(MentorshipStatus, name="mentorship_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=MentorshipStatus.PENDING,
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text)  # initial request message
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("mentor_id", "mentee_id", name="uq_mentorship"),)

    mentor = relationship("User", foreign_keys=[mentor_id])
    mentee = relationship("User", foreign_keys=[mentee_id])