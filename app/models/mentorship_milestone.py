from sqlalchemy import Date, DateTime, Integer, String, Text, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.milestone_status import MilestoneStatus


class MentorshipMilestone(Base):
    __tablename__ = "mentorship_milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    relationship_id: Mapped[int] = mapped_column(
        ForeignKey("mentorship_relationships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            MilestoneStatus,
            name="milestone_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MilestoneStatus.TODO,
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    mentorship_relationship = relationship("MentorshipRelationship", back_populates="milestones")
