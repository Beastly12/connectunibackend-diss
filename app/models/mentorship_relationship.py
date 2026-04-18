from sqlalchemy import String, DateTime, Integer, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus


class MentorshipRelationship(Base):
    __tablename__ = "mentorship_relationships"

    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mentee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal: Mapped[str] = mapped_column(String(500), nullable=False)
    meeting_frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    session_length_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(
            MentorshipRelationshipStatus,
            name="mentorship_relationship_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MentorshipRelationshipStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mentor = relationship("User", foreign_keys=[mentor_id])
    mentee = relationship("User", foreign_keys=[mentee_id])
    sessions = relationship("MentorshipSession", back_populates="mentorship_relationship")
    resources = relationship("MentorshipResource", back_populates="mentorship_relationship")
    milestones = relationship("MentorshipMilestone", back_populates="mentorship_relationship", order_by="MentorshipMilestone.sort_order")
