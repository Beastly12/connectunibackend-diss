"""
Tests for profile endpoints.

GET    /profiles/{user_id}       — full profile (public)
PATCH  /profiles/me              — update base profile fields
GET    /profiles/me/completion   — completion score
DELETE /profiles/me              — delete profile

GET  /profile/me                 — full profile (authenticated, canonical)
POST /profile/student            — student role profile
POST /profile/alumni             — alumni role profile
POST /profile/professional       — professional role profile
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.asyncio

_counter = 0


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"profile_{prefix}_{_counter}@test.com"


# ---------------------------------------------------------------------------
# GET /profiles/{user_id} — public full profile
# ---------------------------------------------------------------------------

class TestGetProfileById:

    async def test_get_profile_by_id_success(self, client: AsyncClient, db: AsyncSession):
        """Any user can retrieve another user's full profile without auth."""
        user = await make_user(db, email=uniq("u"))
        # Seed some base profile data via PATCH so there's something to read back
        await client.patch(
            "/profiles/me",
            json={"headline": "Public profile"},
            headers=auth_headers(user),
        )

        res = await client.get(f"/profiles/{user.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == user.id
        assert data["full_name"] == user.full_name
        assert data["headline"] == "Public profile"
        assert "avatar_url" in data
        assert "role" in data
        assert "verification_status" in data

    async def test_get_profile_by_id_not_found_returns_404(self, client: AsyncClient, db: AsyncSession):
        """Non-existent user_id returns 404."""
        res = await client.get("/profiles/999999")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /profiles/me — update base profile fields
# ---------------------------------------------------------------------------

class TestUpdateProfile:

    async def test_update_profile_success(self, client: AsyncClient, db: AsyncSession):
        """PATCH updates the specified fields and returns the updated profile."""
        user = await make_user(db, email=uniq("u"))

        res = await client.patch(
            "/profiles/me",
            json={"headline": "Updated headline", "bio": "New bio"},
            headers=auth_headers(user),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["headline"] == "Updated headline"
        assert data["bio"] == "New bio"

    async def test_update_profile_creates_if_not_exists(self, client: AsyncClient, db: AsyncSession):
        """PATCH auto-creates the profile row if it doesn't exist yet."""
        user = await make_user(db, email=uniq("u"))
        res = await client.patch(
            "/profiles/me",
            json={"headline": "Auto created"},
            headers=auth_headers(user),
        )
        assert res.status_code == 200
        assert res.json()["headline"] == "Auto created"

    async def test_update_profile_empty_string_returns_422(self, client: AsyncClient, db: AsyncSession):
        """Sending an empty string for a string field returns 422."""
        user = await make_user(db, email=uniq("u"))
        res = await client.patch(
            "/profiles/me",
            json={"headline": ""},
            headers=auth_headers(user),
        )
        assert res.status_code == 422

    async def test_update_profile_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.patch("/profiles/me", json={"headline": "X"})
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /profiles/me/completion
# ---------------------------------------------------------------------------

class TestProfileCompletion:

    async def test_get_completion_returns_structure(self, client: AsyncClient, db: AsyncSession):
        """Returns percentage, missing_fields, and completed_fields."""
        user = await make_user(db, email=uniq("u"))

        res = await client.get("/profiles/me/completion", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert "percentage" in data
        assert "missing_fields" in data
        assert "completed_fields" in data

    async def test_empty_profile_has_zero_completion(self, client: AsyncClient, db: AsyncSession):
        """A profile with no optional fields filled has 0% completion."""
        user = await make_user(db, email=uniq("u"))

        res = await client.get("/profiles/me/completion", headers=auth_headers(user))
        assert res.json()["percentage"] == 0

    async def test_completion_increases_with_filled_fields(self, client: AsyncClient, db: AsyncSession):
        """Filling in headline and bio increases completion above 0."""
        user = await make_user(db, email=uniq("u"))
        await client.patch(
            "/profiles/me",
            json={"headline": "Engineer", "bio": "I build things"},
            headers=auth_headers(user),
        )

        res = await client.get("/profiles/me/completion", headers=auth_headers(user))
        assert res.json()["percentage"] > 0

    async def test_completion_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.get("/profiles/me/completion")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /profile/me — canonical full profile (role_profile router)
# ---------------------------------------------------------------------------

class TestGetMyFullProfile:

    async def test_returns_full_profile_with_base_fields(self, client: AsyncClient, db: AsyncSession):
        """GET /profile/me returns the full profile including base profile fields."""
        user = await make_user(db, email=uniq("u"))
        await client.patch(
            "/profiles/me",
            json={"headline": "My headline", "bio": "My bio"},
            headers=auth_headers(user),
        )

        res = await client.get("/profile/me", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["full_name"] == user.full_name
        assert data["headline"] == "My headline"
        assert data["bio"] == "My bio"
        assert "avatar_url" in data
        assert "role" in data
        assert "verification_status" in data
        assert "student_profile" in data
        assert "alumni_profile" in data
        assert "professional_profile" in data
        assert "mentorship_preferences" in data

    async def test_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.get("/profile/me")
        assert res.status_code == 401
