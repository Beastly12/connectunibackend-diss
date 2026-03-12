import secrets
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    hash_password,
    create_access_token,
    create_refresh_token_plain,
    hash_refresh_token,
)
from app.models import User, RefreshToken
from app.schemas.signup_dto import SignUpDto
from app.schemas.token_response import TokenResponse
from app.schemas.userResponse import UserResponse
from app.services.auth_service import AuthService
from app.tasks.email_tasks import (
    send_welcome_email,
    send_verification_email,
    send_password_reset_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: SignUpDto, db: AsyncSession = Depends(get_db)):
    # Check for duplicate email
    exists = (
        await db.execute(select(User).where(User.email == user.email))
    ).scalar_one_or_none()

    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    # Generate a secure random verification token
    verification_token = secrets.token_urlsafe(32)

    new_user = User(
        email=user.email,
        full_name=user.full_name,
        university=user.university_name,
        grad_year=user.graduation_year,
        major=user.major,
        user_role=user.role,
        password_hash=hash_password(user.password),
        is_verified=False,
        verification_token=verification_token,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send welcome + verification emails after successful DB commit
    first_name = new_user.full_name.split()[0]
    try:
        send_welcome_email(to_email=new_user.email, first_name=first_name)
        send_verification_email(
            to_email=new_user.email,
            first_name=first_name,
            verification_token=verification_token,
        )
    except Exception:
        # Email failure should not roll back registration
        # User can request a resend later
        pass

    return {"id": new_user.id, "email": new_user.email}


# ---------------------------------------------------------------------------
# Verify email
# ---------------------------------------------------------------------------

@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(User.verification_token == token))
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )

    if user.is_verified:
        return {"message": "Email already verified. You can log in."}

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(is_verified=True, verification_token=None)
    )
    await db.commit()

    return {"message": "Email verified successfully. You can now log in."}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "Account inactive or unverified"},
    },
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
):
    return await service.login(email=form_data.username, password=form_data.password)


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(refresh_token)
    rt = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not rt or rt.revoked or rt.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token.")

    # Revoke used token (rotation — each refresh token can only be used once)
    await db.execute(
        update(RefreshToken).where(RefreshToken.id == rt.id).values(revoked=True)
    )

    user = (
        await db.execute(select(User).where(User.id == rt.user_id))
    ).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive.")

    access = create_access_token(subject=user.email, user_id=user.id)
    new_refresh_plain = create_refresh_token_plain()
    new_refresh_hash = hash_refresh_token(new_refresh_plain)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_DAYS)

    db.add(RefreshToken(user_id=user.id, token_hash=new_refresh_hash, expires_at=expires))
    await db.commit()

    return {
        "access_token": access,
        "refresh_token": new_refresh_plain,
        "token_type": "bearer",
    }


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()

    # Always return the same response whether the email exists or not
    # This prevents attackers from enumerating which emails are registered
    if not user:
        return {"message": "If that email is registered, you will receive a reset link shortly."}

    reset_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(password_reset_token=reset_token, password_reset_expires=expires)
    )
    await db.commit()

    first_name = user.full_name.split()[0]
    try:
        send_password_reset_email(
            to_email=user.email,
            first_name=first_name,
            reset_token=reset_token,
        )
    except Exception:
        pass

    return {"message": "If that email is registered, you will receive a reset link shortly."}


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
):
    user = (
        await db.execute(select(User).where(User.password_reset_token == token))
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    if user.password_reset_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link has expired. Please request a new one.",
        )

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            password_hash=hash_password(new_password),
            password_reset_token=None,
            password_reset_expires=None,
        )
    )
    await db.commit()

    return {"message": "Password reset successfully. You can now log in."}


# ---------------------------------------------------------------------------
# Dev utility — list users
# ---------------------------------------------------------------------------

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()