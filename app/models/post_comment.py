
from sqlalchemy import (
    DateTime, Text, ForeignKey,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PostComment(Base):
    __tablename__ = "post_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    post = relationship("CommunityPost", back_populates="comments")
    author = relationship("User")