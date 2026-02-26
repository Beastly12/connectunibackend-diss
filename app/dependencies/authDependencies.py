from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import jwt
from app.core.config import settings
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def decode_access(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])

async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = decode_access(token)
        if payload.get("type") != "access":
            raise HTTPException(401, "Wrong token type")
        uid = payload.get("uid")
    except JWTError:
        raise HTTPException(401, "Invalid token")

    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user


# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from jose import JWTError, jwt
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from app.core.database import get_db
# from app.core.config import settings
# from app.models import User
#
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
#
#
# def decode_access_token(token: str) -> dict:
#     """
#     Decode and validate a JWT access token.
#
#     Args:
#         token: JWT token string
#
#     Returns:
#         Decoded token payload
#
#     Raises:
#         JWTError: If token is invalid or expired
#     """
#     try:
#         payload = jwt.decode(
#             token,
#             settings.JWT_SECRET,
#             algorithms=[settings.JWT_ALG]
#         )
#         return payload
#     except JWTError as e:
#         raise JWTError(f"Token validation failed: {str(e)}")
#
#
# async def get_current_user(
#         token: str = Depends(oauth2_scheme),
#         db: AsyncSession = Depends(get_db)
# ) -> User:
#     """
#     Dependency to get the current authenticated user from JWT token.
#
#     Validates token signature, type, and user existence/status.
#
#     Args:
#         token: JWT token from Authorization header
#         db: Database session
#
#     Returns:
#         Current authenticated user
#
#     Raises:
#         HTTPException: 401 if token is invalid, wrong type, or user not found/inactive
#
#     Usage:
#         @router.get("/protected")
#         async def protected_route(current_user: User = Depends(get_current_user)):
#             return {"user_id": current_user.id}
#     """
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Invalid authentication credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#
#     try:
#         payload = decode_access_token(token)
#     except JWTError:
#         raise credentials_exception
#
#     # Validate token type
#     if payload.get("type") != "access":
#         raise credentials_exception
#
#     # Extract user ID from token
#     user_id = payload.get("sub")
#     if user_id is None:
#         raise credentials_exception
#
#     # Fetch user from database
#     user = await db.scalar(
#         select(User).where(User.id == user_id)
#     )
#
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#
#     if not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User account is inactive",
#         )
#
#     return user