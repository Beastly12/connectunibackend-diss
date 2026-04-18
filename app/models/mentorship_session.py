from sqlalchemy import DateTime, Integer, Text, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.mentorship_session_status import MentorshipSessionStatus


class MentorshipSession(Base):
    __tablename__ = "mentorship_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    relationship_id: Mapped[int] = mapped_column(
        ForeignKey("mentorship_relationships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        SAEnum(
            MentorshipSessionStatus,
            name="mentorship_session_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MentorshipSessionStatus.UPCOMING,
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    mentorship_relationship = relationship("MentorshipRelationship", back_populates="sessions")
