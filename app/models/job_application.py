
from sqlalchemy import (
    String, DateTime, Text, ForeignKey,
    Enum as SAEnum, func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.job_application_status import JobApplicationStatus


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    applicant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cover_letter: Mapped[str | None] = mapped_column(Text)
    resume_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        SAEnum(JobApplicationStatus, name="job_application_status_enum"),
        default=JobApplicationStatus.PENDING,
        nullable=False,
    )
    applied_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("job_id", "applicant_id", name="uq_job_application"),)

    job = relationship("Job", back_populates="applications")
    applicant = relationship("User")
