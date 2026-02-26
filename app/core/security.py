from datetime import datetime, timedelta, timezone
from jose import jwt
from argon2 import PasswordHasher
import secrets, hashlib
from app.core.config import settings

ph = PasswordHasher()

def hash_password(p: str) -> str:
    return ph.hash(p)

def verify_password(p: str, h: str) -> bool:
    try:
        return ph.verify(h, p)
    except Exception:
        return False

def create_access_token(subject: str, user_id: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    return jwt.encode(
        {"sub": subject, "uid": user_id, "type": "access", "exp": int(exp.timestamp())},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALG,
    )

def create_refresh_token_plain() -> str:
    return secrets.token_urlsafe(48)

def hash_refresh_token(token_plain: str) -> str:
    return hashlib.sha256(token_plain.encode("utf-8")).hexdigest()
