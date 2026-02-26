from sqlalchemy import (
    String, Boolean, DateTime, Text, Enum as SAEnum, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.community_type import CommunityType


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(
        SAEnum(CommunityType, name="community_type_enum"), nullable=False
    )
    # Only populated when type == UNIVERSITY; matched against User.university to gate joining
    university: Mapped[str | None] = mapped_column(String(320))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    posts = relationship("CommunityPost", back_populates="community")
    members = relationship("CommunityMember", back_populates="community")