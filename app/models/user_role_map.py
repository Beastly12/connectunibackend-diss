from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import (
    ForeignKey,
    Enum as SAEnum, UniqueConstraint
)

from app.core.database import Base
from app.enums.user_role import UserRole


class UserRoleMap(Base):
    """
    Allows a single user to hold multiple roles (e.g. Alumni + Mentor).
    """
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        SAEnum(UserRole, name="user_role_enum"), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_role"),)

    user = relationship("User", back_populates="roles")
