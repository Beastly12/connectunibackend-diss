"""
Tests for profile endpoints.

POST   /profiles/
GET    /profiles/me
GET    /profiles/{user_id}
PATCH  /profiles/me
GET    /profiles/me/completion
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
# Create
# ---------------------------------------------------------------------------

class TestCreateProfile:

    async def test_create_profile_success(self, client: AsyncClient, db: AsyncSession):
        """Creating a profile returns 201 with the profile data."""
        user = await make_user(db, email=uniq("u"))
        res = await client.post(
            "/profiles/",
            json={"headline": "Software Engineer", "bio": "Loves Python"},
            headers=auth_headers(user),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["user_id"] == user.id
        assert data["headline"] == "Software Engineer"
        assert data["bio"] == "Loves Python"

    async def test_create_profile_minimal_payload(self, client: AsyncClient, db: AsyncSession):
        """Creating a profile with no fields still succeeds (all optional)."""
        user = await make_user(db, email=uniq("u"))
        res = await client.post("/profiles/", json={}, headers=auth_headers(user))
        assert res.status_code == 201
        assert res.json()["user_id"] == user.id

    async def test_create_duplicate_profile_returns_409(self, client: AsyncClient, db: AsyncSession):
        """Creating a second profile for the same user returns 409."""
        user = await make_user(db, email=uniq("u"))
        await client.post("/profiles/", json={"headline": "First"}, headers=auth_headers(user))
        res = await client.post("/profiles/", json={"headline": "Second"}, headers=auth_headers(user))
        assert res.status_code == 409

    async def test_create_profile_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.post("/profiles/", json={})
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Read — /profiles/me
# ---------------------------------------------------------------------------

class TestGetMyProfile:

    async def test_get_my_profile_success(self, client: AsyncClient, db: AsyncSession):
        """Returns 200 with the user's profile."""
        user = await make_user(db, email=uniq("u"))
        await client.post("/profiles/", json={"bio": "My bio"}, headers=auth_headers(user))

        res = await client.get("/profiles/me", headers=auth_headers(user))
        assert res.status_code == 200
        assert res.json()["bio"] == "My bio"

    async def test_get_my_profile_not_found_returns_404(self, client: AsyncClient, db: AsyncSession):
        """User without a profile gets 404."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get("/profiles/me", headers=auth_headers(user))
        assert res.status_code == 404

    async def test_get_my_profile_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.get("/profiles/me")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Read — /profiles/{user_id} (public)
# ---------------------------------------------------------------------------

class TestGetProfileById:

    async def test_get_profile_by_id_success(self, client: AsyncClient, db: AsyncSession):
        """Any user can retrieve another user's profile without auth."""
        user = await make_user(db, email=uniq("u"))
        await client.post(
            "/profiles/",
            json={"headline": "Public profile"},
            headers=auth_headers(user),
        )

        res = await client.get(f"/profiles/{user.id}")
        assert res.status_code == 200
        assert res.json()["headline"] == "Public profile"

    async def test_get_profile_by_id_not_found_returns_404(self, client: AsyncClient, db: AsyncSession):
        """Non-existent user_id returns 404."""
        res = await client.get("/profiles/999999")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class TestUpdateProfile:

    async def test_update_profile_success(self, client: AsyncClient, db: AsyncSession):
        """PATCH updates the specified fields."""
        user = await make_user(db, email=uniq("u"))
        await client.post(
            "/profiles/",
            json={"headline": "Original headline"},
            headers=auth_headers(user),
        )

        res = await client.patch(
            "/profiles/me",
            json={"headline": "Updated headline", "bio": "New bio"},
            headers=auth_headers(user),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["headline"] == "Updated headline"
        assert data["bio"] == "New bio"

    async def test_update_profile_not_found_returns_404(self, client: AsyncClient, db: AsyncSession):
        """PATCH on a non-existent profile returns 404."""
        user = await make_user(db, email=uniq("u"))
        res = await client.patch(
            "/profiles/me",
            json={"headline": "No profile exists"},
            headers=auth_headers(user),
        )
        assert res.status_code == 404

    async def test_update_profile_empty_string_returns_422(self, client: AsyncClient, db: AsyncSession):
        """Sending an empty string for a string field returns 422."""
        user = await make_user(db, email=uniq("u"))
        await client.post("/profiles/", json={}, headers=auth_headers(user))

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
# Completion
# ---------------------------------------------------------------------------

class TestProfileCompletion:

    async def test_get_completion_returns_structure(self, client: AsyncClient, db: AsyncSession):
        """Returns percentage, missing_fields, and completed_fields."""
        user = await make_user(db, email=uniq("u"))
        await client.post("/profiles/", json={}, headers=auth_headers(user))

        res = await client.get("/profiles/me/completion", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert "percentage" in data
        assert "missing_fields" in data
        assert "completed_fields" in data

    async def test_empty_profile_has_low_completion(self, client: AsyncClient, db: AsyncSession):
        """A profile with no fields filled has 0% completion."""
        user = await make_user(db, email=uniq("u"))
        await client.post("/profiles/", json={}, headers=auth_headers(user))

        res = await client.get("/profiles/me/completion", headers=auth_headers(user))
        assert res.json()["percentage"] == 0

    async def test_completion_increases_with_filled_fields(self, client: AsyncClient, db: AsyncSession):
        """Filling in headline and bio increases completion above 0."""
        user = await make_user(db, email=uniq("u"))
        await client.post(
            "/profiles/",
            json={"headline": "Engineer", "bio": "I build things"},
            headers=auth_headers(user),
        )

        res = await client.get("/profiles/me/completion", headers=auth_headers(user))
        assert res.json()["percentage"] > 0

    async def test_completion_no_profile_returns_404(self, client: AsyncClient, db: AsyncSession):
        """Requesting completion for a user with no profile returns 404."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get("/profiles/me/completion", headers=auth_headers(user))
        assert res.status_code == 404
