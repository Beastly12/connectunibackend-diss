from ast import List
from typing import List as MappedList
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    hash_password, verify_password,
    create_access_token,
    create_refresh_token_plain, hash_refresh_token
)
from app.models import User, RefreshToken
from app.schemas.signup_dto import SignUpDto
from app.schemas.token_response import TokenResponse
from app.schemas.userResponse import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", status_code=201)
async def register(user: SignUpDto, db: AsyncSession = Depends(get_db)):
    exists = (
        await db.execute(select(User).where(User.email == user.email))
    ).scalar_one_or_none()

    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        full_name=user.full_name,
        university=user.university_name,
        grad_year=user.graduation_year,
        major=user.major,
        user_role=user.role,
        password_hash=hash_password(user.password),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email}


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "Account inactive or unverified"},
    }
)
async def login(
        # OAuth2PasswordRequestForm gives you a standard form with username/password fields
        # FastAPI's built-in /docs will render a proper login form for this
        form_data: OAuth2PasswordRequestForm = Depends(),
        service: AuthService = Depends(get_auth_service),
):
    # OAuth2PasswordRequestForm uses "username" field — we treat it as email
    return await service.login(email=form_data.username, password=form_data.password)


@router.post("/refresh")
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(refresh_token)

    rt = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not rt or rt.revoked or rt.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    # revoke used token (rotation)
    await db.execute(update(RefreshToken).where(RefreshToken.id == rt.id).values(revoked=True))

    user = (await db.execute(select(User).where(User.id == rt.user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive")

    access = create_access_token(subject=user.email, user_id=user.id)

    new_refresh_plain = create_refresh_token_plain()
    new_refresh_hash = hash_refresh_token(new_refresh_plain)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_DAYS)

    db.add(RefreshToken(user_id=user.id, token_hash=new_refresh_hash, expires_at=expires))
    await db.commit()

    return {"access_token": access, "refresh_token": new_refresh_plain, "token_type": "bearer"}


@router.get("/users", response_model=MappedList[UserResponse])
async def get_users(
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=20, ge=1, le=100),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users
