from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(320), nullable=False)
    university: Mapped[str] = mapped_column(String(320), nullable=False)
    grad_year: Mapped[int] = mapped_column(Integer, nullable=False)  # Fixed: was String
    major: Mapped[str] = mapped_column(String(320), nullable=False)
    user_role: Mapped[str] = mapped_column(String(50), default='STUDENT', nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    profile = relationship("Profile", back_populates="user", uselist=False)
    roles = relationship("UserRoleMap", back_populates="user")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # ← False now
    verification_token: Mapped[str | None] = mapped_column(String(500), nullable=True)  # ← new
    password_reset_token: Mapped[str | None] = mapped_column(String(500), nullable=True)  # ← new
    password_reset_expires: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # ← new


    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # Fixed: removed string quotes