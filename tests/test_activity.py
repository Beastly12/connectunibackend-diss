"""
Tests for activity endpoints.

GET /activity/me
GET /activity/me/{activity_type}
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.models.activity import Activity
from app.enums.activity_type import ActivityType

pytestmark = pytest.mark.asyncio

_counter = 0


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"act_{prefix}_{_counter}@test.com"


async def seed_activity(db: AsyncSession, user_id: int, activity_type: ActivityType, description: str = "test") -> Activity:
    """Insert an Activity row directly into the DB."""
    activity = Activity(
        user_id=user_id,
        activity_type=activity_type,
        description=description,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


class TestGetMyActivity:

    async def test_returns_empty_list_for_new_user(self, client: AsyncClient, db: AsyncSession):
        """A user with no activity gets an empty list."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get("/activity/me", headers=auth_headers(user))
        assert res.status_code == 200
        assert res.json() == []

    async def test_returns_activity_items(self, client: AsyncClient, db: AsyncSession):
        """Activity items created in the DB are returned."""
        user = await make_user(db, email=uniq("u"))
        await seed_activity(db, user.id, ActivityType.JOINED_COMMUNITY, "Joined global community")

        res = await client.get("/activity/me", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert data[0]["activity_type"] == ActivityType.JOINED_COMMUNITY

    async def test_returns_only_own_activity(self, client: AsyncClient, db: AsyncSession):
        """Users only see their own activity — not other users'."""
        user_a = await make_user(db, email=uniq("a"))
        user_b = await make_user(db, email=uniq("b"))

        await seed_activity(db, user_a.id, ActivityType.RSVP_EVENT, "User A RSVPed")

        res = await client.get("/activity/me", headers=auth_headers(user_b))
        assert res.status_code == 200
        for item in res.json():
            assert item.get("user_id", user_b.id) == user_b.id

    async def test_limit_parameter_respected(self, client: AsyncClient, db: AsyncSession):
        """?limit=1 returns at most 1 item."""
        user = await make_user(db, email=uniq("u"))
        for _ in range(3):
            await seed_activity(db, user.id, ActivityType.SENT_MESSAGE)

        res = await client.get("/activity/me?limit=1", headers=auth_headers(user))
        assert res.status_code == 200
        assert len(res.json()) <= 1

    async def test_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.get("/activity/me")
        assert res.status_code == 401


class TestGetMyActivityByType:

    async def test_returns_empty_list_when_no_matching_type(self, client: AsyncClient, db: AsyncSession):
        """Requesting an activity type the user has none of returns empty list."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get(
            f"/activity/me/{ActivityType.STARTED_MENTORSHIP}",
            headers=auth_headers(user),
        )
        assert res.status_code == 200
        assert res.json() == []

    async def test_filters_by_activity_type(self, client: AsyncClient, db: AsyncSession):
        """Only items matching the requested type are returned."""
        user = await make_user(db, email=uniq("u"))
        await seed_activity(db, user.id, ActivityType.JOINED_COMMUNITY, "Joined")
        await seed_activity(db, user.id, ActivityType.RSVP_EVENT, "RSVPed")

        # First confirm both activities are visible via the unfiltered endpoint.
        all_res = await client.get("/activity/me", headers=auth_headers(user))
        assert all_res.status_code == 200
        all_data = all_res.json()
        joined = [a for a in all_data if a["activity_type"] == ActivityType.JOINED_COMMUNITY.value]
        assert len(joined) >= 1, f"Seeded JOINED_COMMUNITY not found in /activity/me: {all_data}"

        # The filter endpoint must return only items of the requested type.
        res = await client.get(
            f"/activity/me/{ActivityType.JOINED_COMMUNITY.value}",
            headers=auth_headers(user),
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        for item in data:
            assert item["activity_type"] == ActivityType.JOINED_COMMUNITY.value

    async def test_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.get(f"/activity/me/{ActivityType.RSVP_EVENT}")
        assert res.status_code == 401
