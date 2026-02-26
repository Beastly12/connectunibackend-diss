

from sqlalchemy import (
    String, DateTime, Integer, Text, ForeignKey,
 func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base




class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    avatar_url: Mapped[str | None] = mapped_column(String(500))
    headline: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)

    # Academic / professional
    university: Mapped[str | None] = mapped_column(String(320))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    major: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    job_title: Mapped[str | None] = mapped_column(String(255))
    goals: Mapped[str | None] = mapped_column(Text)

    # Arrays stored as JSONB for flexibility
    skills: Mapped[dict | None] = mapped_column(JSONB, default=list)
    interests: Mapped[dict | None] = mapped_column(JSONB, default=list)

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="profile")