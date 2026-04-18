from sqlalchemy import (
    String, Boolean, DateTime, Text, Integer, ForeignKey,
    Enum as SAEnum, func,
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
        SAEnum(CommunityType, name="community_type_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    # Only populated when type == UNIVERSITY
    university: Mapped[str | None] = mapped_column(String(320))
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    cover_image_public_id: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    creator = relationship("User", foreign_keys=[creator_id])
    posts = relationship("CommunityPost", back_populates="community")
    members = relationship("CommunityMember", back_populates="community")
    invites = relationship("CommunityInvite", back_populates="community")
    messages = relationship("CommunityMessage", back_populates="community")
