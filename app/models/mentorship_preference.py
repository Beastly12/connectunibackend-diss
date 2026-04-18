from sqlalchemy import Boolean, DateTime, Integer, ForeignKey, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.preferred_format import PreferredFormat


class MentorshipPreference(Base):
    __tablename__ = "mentorship_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    is_mentor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_mentee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    areas_of_interest: Mapped[list | None] = mapped_column(JSONB, default=list)
    availability_hours_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_format: Mapped[str] = mapped_column(
        SAEnum(PreferredFormat, name="preferred_format_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
