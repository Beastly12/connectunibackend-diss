
from sqlalchemy import (
    String, DateTime, Text, ForeignKey,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    image_url: Mapped[str | None] = mapped_column(String(500))
    image_public_id: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    community = relationship("Community", back_populates="posts")
    author = relationship("User")
    comments = relationship("PostComment", back_populates="post")
    likes = relationship("PostLike", back_populates="post")