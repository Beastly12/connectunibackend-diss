from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CommunityMessage(Base):
    __tablename__ = "community_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("community_messages.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    community = relationship("Community", back_populates="messages")
    sender = relationship("User")
    attachments = relationship(
        "CommunityMessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
    )
    reactions = relationship(
        "CommunityMessageReaction",
        back_populates="message",
        cascade="all, delete-orphan",
    )
