from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.mentorship_request_status import MentorshipRequestStatus


class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    mentee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mentor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal: Mapped[str] = mapped_column(String(500), nullable=False)
    meeting_frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    session_length_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            MentorshipRequestStatus,
            name="mentorship_request_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MentorshipRequestStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    mentee = relationship("User", foreign_keys=[mentee_id])
    mentor = relationship("User", foreign_keys=[mentor_id])
