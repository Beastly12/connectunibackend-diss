from sqlalchemy import (
    DateTime, ForeignKey, Enum as SAEnum,
    func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.enums.community_role import CommunityRole


class CommunityMember(Base):
    """Tracks which users belong to which communities and their role."""
    __tablename__ = "community_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        SAEnum(CommunityRole, name="community_role_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CommunityRole.MEMBER,
    )
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("community_id", "user_id", name="uq_community_member"),)

    community = relationship("Community", back_populates="members")
    user = relationship("User")
