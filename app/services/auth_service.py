from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token_plain,
    hash_refresh_token,
)
from app.core.config import settings
from app.repositories.auth_repository import AuthRepository


class AuthService:

    def __init__(self, db: AsyncSession):
        self.repo = AuthRepository(db)

    async def login(self, email: str, password: str) -> dict:
        # Step 1: find user
        user = await self.repo.get_user_by_email(email)

        # Step 2: validate credentials
        # Deliberately vague — never reveal which field was wrong
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Step 3: check account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact support.",
            )

        # Step 4: check account is verified
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in.",
            )

        # Step 5: issue tokens
        access_token = create_access_token(subject=user.email, user_id=user.id)

        refresh_plain = create_refresh_token_plain()
        refresh_hash = hash_refresh_token(refresh_plain)
        expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_DAYS)

        await self.repo.save_refresh_token(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_plain,
            "token_type": "bearer",
        }