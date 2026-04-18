"""
Shared test fixtures.

Uses an in-memory SQLite database so no external PostgreSQL is needed.
The `get_db` FastAPI dependency is overridden to use this DB for every test.
JWT tokens are generated with the real create_access_token helper so auth
flows through the real middleware unchanged.
"""

import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

# SQLite lacks PostgreSQL-specific types; map them to TEXT for tests.
SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "TEXT"  # type: ignore[attr-defined]
SQLiteTypeCompiler.visit_ARRAY = lambda self, type_, **kw: "TEXT"  # type: ignore[attr-defined]

from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.main import app
from app.models.user import User

# --------------------------------------------------------------------------
# In-memory SQLite engine (shared for the whole test session)
# --------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
_TestSession = async_sessionmaker(_engine, expire_on_commit=False)


# --------------------------------------------------------------------------
# Session-scoped: create / drop all tables once
# --------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# --------------------------------------------------------------------------
# Function-scoped: one DB session per test, rolled back after
# --------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db() -> AsyncSession:
    async with _TestSession() as session:
        yield session


# --------------------------------------------------------------------------
# HTTP client with get_db overridden
# --------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client(db: AsyncSession) -> AsyncClient:
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


# --------------------------------------------------------------------------
# Helper: create a User row directly (no email verification needed)
# --------------------------------------------------------------------------

async def make_user(
    db: AsyncSession,
    *,
    email: str = "user@test.com",
    full_name: str = "Test User",
    university: str = "Test University",
    grad_year: int = 2025,
    major: str = "CS",
    password: str = "password123",
) -> User:
    user = User(
        email=email,
        full_name=full_name,
        university=university,
        grad_year=grad_year,
        major=major,
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    token = create_access_token(subject=user.email, user_id=user.id)
    return {"Authorization": f"Bearer {token}"}
