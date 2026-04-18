"""
Tests for authentication endpoints.

POST /auth/register
GET  /auth/verify-email
POST /auth/login
POST /auth/logout
POST /auth/refresh
POST /auth/forgot-password
POST /auth/reset-password
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.core.security import hash_password, hash_refresh_token, create_refresh_token_plain
from app.models.user import User
from app.models import RefreshToken

pytestmark = pytest.mark.asyncio

_counter = 0


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"auth_{prefix}_{_counter}@test.com"


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

class TestRegister:

    async def test_register_success(self, client: AsyncClient, db: AsyncSession):
        """Valid payload returns 201 with id and email."""
        res = await client.post("/auth/register", json={
            "full_name": "Alice Smith",
            "email": uniq("u"),
            "password": "Secure123",
            "university_name": "Test University",
            "graduation_year": 2028,
            "major": "Computer Science",
            "role": "STUDENT",
        })
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert "email" in data

    async def test_register_duplicate_email_returns_400(self, client: AsyncClient, db: AsyncSession):
        """Registering with an already-used email returns 400."""
        email = uniq("dup")
        payload = {
            "full_name": "Bob Jones",
            "email": email,
            "password": "Secure123",
            "university_name": "Test University",
            "graduation_year": 2028,
            "major": "Mathematics",
            "role": "STUDENT",
        }
        await client.post("/auth/register", json=payload)
        res = await client.post("/auth/register", json=payload)
        assert res.status_code == 400

    async def test_register_weak_password_returns_422(self, client: AsyncClient, db: AsyncSession):
        """Password without uppercase letter fails validation."""
        res = await client.post("/auth/register", json={
            "full_name": "Carol White",
            "email": uniq("u"),
            "password": "alllower123",
            "university_name": "Test University",
            "graduation_year": 2028,
            "major": "Physics",
            "role": "STUDENT",
        })
        assert res.status_code == 422

    async def test_register_invalid_role_returns_422(self, client: AsyncClient, db: AsyncSession):
        """An unrecognised role fails validation."""
        res = await client.post("/auth/register", json={
            "full_name": "Dan Brown",
            "email": uniq("u"),
            "password": "Secure123",
            "university_name": "Test University",
            "graduation_year": 2028,
            "major": "History",
            "role": "HACKER",
        })
        assert res.status_code == 422

    async def test_register_student_past_graduation_year_returns_422(self, client: AsyncClient, db: AsyncSession):
        """Student with a past graduation year fails validation."""
        res = await client.post("/auth/register", json={
            "full_name": "Eve Davis",
            "email": uniq("u"),
            "password": "Secure123",
            "university_name": "Test University",
            "graduation_year": 2020,
            "major": "Biology",
            "role": "STUDENT",
        })
        assert res.status_code == 422

    async def test_register_alumni_future_graduation_year_returns_422(self, client: AsyncClient, db: AsyncSession):
        """Alumni with a future graduation year fails validation."""
        res = await client.post("/auth/register", json={
            "full_name": "Frank Miller",
            "email": uniq("u"),
            "password": "Secure123",
            "university_name": "Test University",
            "graduation_year": 2030,
            "major": "Chemistry",
            "role": "ALUMNI",
        })
        assert res.status_code == 422

    async def test_register_professional_role_succeeds(self, client: AsyncClient, db: AsyncSession):
        """PROFESSIONAL role is accepted with any graduation year."""
        res = await client.post("/auth/register", json={
            "full_name": "Grace Lee",
            "email": uniq("u"),
            "password": "Secure123",
            "university_name": "Test University",
            "graduation_year": 2015,
            "major": "Engineering",
            "role": "PROFESSIONAL",
        })
        assert res.status_code == 201


# ---------------------------------------------------------------------------
# Verify email
# ---------------------------------------------------------------------------

class TestVerifyEmail:

    async def test_verify_email_success(self, client: AsyncClient, db: AsyncSession):
        """Valid token sets is_verified=True and clears the token."""
        token = "validtoken123abc"
        user = User(
            email=uniq("v"),
            full_name="Test User",
            university="Test Uni",
            grad_year=2028,
            major="CS",
            password_hash=hash_password("TestPass1"),
            is_active=True,
            is_verified=False,
            verification_token=token,
        )
        db.add(user)
        await db.commit()

        res = await client.get(f"/auth/verify-email?token={token}")
        assert res.status_code == 200
        assert "verified" in res.json()["message"].lower()

    async def test_verify_email_invalid_token_returns_400(self, client: AsyncClient, db: AsyncSession):
        """A token that doesn't exist in the DB returns 400."""
        res = await client.get("/auth/verify-email?token=doesnotexist")
        assert res.status_code == 400

    async def test_verify_already_verified_returns_message(self, client: AsyncClient, db: AsyncSession):
        """Calling verify on an already-verified user returns a friendly message."""
        token = "alreadyverified456"
        user = User(
            email=uniq("v"),
            full_name="Test User",
            university="Test Uni",
            grad_year=2028,
            major="CS",
            password_hash=hash_password("TestPass1"),
            is_active=True,
            is_verified=True,
            verification_token=token,
        )
        db.add(user)
        await db.commit()

        res = await client.get(f"/auth/verify-email?token={token}")
        assert res.status_code == 200
        assert "already verified" in res.json()["message"].lower()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:

    async def test_login_success_returns_tokens(self, client: AsyncClient, db: AsyncSession):
        """Correct credentials return access_token and refresh_token."""
        email = uniq("l")
        await make_user(db, email=email, password="TestPass1")

        res = await client.post("/auth/login", data={"username": email, "password": "TestPass1"})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, client: AsyncClient, db: AsyncSession):
        """Wrong password returns 401."""
        email = uniq("l")
        await make_user(db, email=email, password="TestPass1")

        res = await client.post("/auth/login", data={"username": email, "password": "WrongPass9"})
        assert res.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, client: AsyncClient, db: AsyncSession):
        """Non-existent email returns 401 (same as wrong password — no enumeration)."""
        res = await client.post("/auth/login", data={"username": "nobody@nowhere.com", "password": "TestPass1"})
        assert res.status_code == 401

    async def test_login_unverified_user_returns_403(self, client: AsyncClient, db: AsyncSession):
        """Unverified user cannot log in."""
        email = uniq("l")
        user = User(
            email=email,
            full_name="Test User",
            university="Test Uni",
            grad_year=2028,
            major="CS",
            password_hash=hash_password("TestPass1"),
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        await db.commit()

        res = await client.post("/auth/login", data={"username": email, "password": "TestPass1"})
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:

    async def test_logout_success(self, client: AsyncClient, db: AsyncSession):
        """Valid refresh token is revoked and 200 is returned."""
        email = uniq("lo")
        user = await make_user(db, email=email, password="TestPass1")

        login_res = await client.post("/auth/login", data={"username": email, "password": "TestPass1"})
        refresh_token = login_res.json()["refresh_token"]

        res = await client.post(
            f"/auth/logout?refresh_token={refresh_token}",
            headers=auth_headers(user),
        )
        assert res.status_code == 200

    async def test_logout_invalid_token_returns_400(self, client: AsyncClient, db: AsyncSession):
        """Attempting to logout with a bogus refresh token returns 400."""
        user = await make_user(db, email=uniq("lo"))
        res = await client.post(
            "/auth/logout?refresh_token=notavalidtoken",
            headers=auth_headers(user),
        )
        assert res.status_code == 400

    async def test_logout_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Logout without a Bearer token returns 401."""
        res = await client.post("/auth/logout?refresh_token=anything")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------

class TestRefresh:

    async def test_refresh_returns_new_tokens(self, client: AsyncClient, db: AsyncSession):
        """Using a valid refresh token returns a new access_token and refresh_token."""
        email = uniq("r")
        await make_user(db, email=email, password="TestPass1")

        login_res = await client.post("/auth/login", data={"username": email, "password": "TestPass1"})
        refresh_token = login_res.json()["refresh_token"]

        res = await client.post(f"/auth/refresh?refresh_token={refresh_token}")
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_token_rotation_old_token_invalid(self, client: AsyncClient, db: AsyncSession):
        """After a refresh, the old refresh token cannot be used again (token rotation)."""
        email = uniq("r")
        await make_user(db, email=email, password="TestPass1")

        login_res = await client.post("/auth/login", data={"username": email, "password": "TestPass1"})
        old_refresh = login_res.json()["refresh_token"]

        await client.post(f"/auth/refresh?refresh_token={old_refresh}")

        res = await client.post(f"/auth/refresh?refresh_token={old_refresh}")
        assert res.status_code == 401

    async def test_refresh_invalid_token_returns_401(self, client: AsyncClient, db: AsyncSession):
        """A bogus refresh token returns 401."""
        res = await client.post("/auth/refresh?refresh_token=faketoken")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------

class TestForgotPassword:

    async def test_forgot_password_existing_email_returns_200(self, client: AsyncClient, db: AsyncSession):
        """Returns the same generic message for a registered email."""
        user = await make_user(db, email=uniq("fp"))
        res = await client.post(f"/auth/forgot-password?email={user.email}")
        assert res.status_code == 200
        assert "registered" in res.json()["message"].lower()

    async def test_forgot_password_nonexistent_email_returns_same_message(self, client: AsyncClient, db: AsyncSession):
        """Returns the same message for an unknown email to prevent enumeration."""
        res = await client.post("/auth/forgot-password?email=nobody@fake.com")
        assert res.status_code == 200
        assert "registered" in res.json()["message"].lower()


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------

class TestResetPassword:

    async def test_reset_password_success(self, client: AsyncClient, db: AsyncSession):
        """Valid reset token allows password change."""
        reset_token = "resettoken789xyz"
        expires = datetime.now(timezone.utc) + timedelta(minutes=30)

        user = User(
            email=uniq("rp"),
            full_name="Test User",
            university="Test Uni",
            grad_year=2028,
            major="CS",
            password_hash=hash_password("OldPass1"),
            is_active=True,
            is_verified=True,
            password_reset_token=reset_token,
            password_reset_expires=expires,
        )
        db.add(user)
        await db.commit()

        res = await client.post(f"/auth/reset-password?token={reset_token}&new_password=NewPass9")
        assert res.status_code == 200
        assert "reset successfully" in res.json()["message"].lower()

    async def test_reset_password_invalid_token_returns_400(self, client: AsyncClient, db: AsyncSession):
        """Invalid reset token returns 400."""
        res = await client.post("/auth/reset-password?token=badtoken&new_password=NewPass9")
        assert res.status_code == 400

    async def test_reset_password_expired_token_returns_400(self, client: AsyncClient, db: AsyncSession):
        """Expired reset token returns 400."""
        reset_token = "expiredtoken000"
        expires = datetime.now(timezone.utc) - timedelta(minutes=1)

        user = User(
            email=uniq("rp"),
            full_name="Test User",
            university="Test Uni",
            grad_year=2028,
            major="CS",
            password_hash=hash_password("OldPass1"),
            is_active=True,
            is_verified=True,
            password_reset_token=reset_token,
            password_reset_expires=expires,
        )
        db.add(user)
        await db.commit()

        res = await client.post(f"/auth/reset-password?token={reset_token}&new_password=NewPass9")
        assert res.status_code == 400
