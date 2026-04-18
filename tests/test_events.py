"""
Tests for event endpoints.

GET    /events/
GET    /events/past
GET    /events/rsvps
GET    /events/{event_id}
POST   /events/
PATCH  /events/{event_id}
POST   /events/{event_id}/rsvp
DELETE /events/{event_id}/rsvp
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.models.event import Event
from app.enums.event_type import EventType

pytestmark = pytest.mark.asyncio

_counter = 0

FUTURE_DATE = "2028-06-01T10:00:00Z"


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"event_{prefix}_{_counter}@test.com"


def future_date_str(days: int = 400) -> str:
    """Return an ISO 8601 datetime string that is `days` days in the future."""
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


async def create_event(client: AsyncClient, user, *, days_ahead: int = 400) -> dict:
    """Helper: create a future event via the API and return its JSON."""
    res = await client.post(
        "/events/",
        data={
            "title": "Test Event",
            "description": "A detailed description of the test event",
            "location": "Test City",
            "event_date": future_date_str(days_ahead),
            "event_type": "academic",
        },
        headers=auth_headers(user),
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Create event
# ---------------------------------------------------------------------------

class TestCreateEvent:

    async def test_create_event_success(self, client: AsyncClient, db: AsyncSession):
        """Valid form payload returns 201 with the event data."""
        user = await make_user(db, email=uniq("u"))
        res = await client.post(
            "/events/",
            data={
                "title": "My Event",
                "description": "A great event for everyone",
                "location": "London",
                "event_date": future_date_str(),
                "event_type": "social",
            },
            headers=auth_headers(user),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "My Event"
        assert data["event_type"] == "social"
        assert data["organizer_id"] == user.id

    async def test_create_event_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated request returns 401."""
        res = await client.post(
            "/events/",
            data={
                "title": "No Auth",
                "description": "Should be rejected",
                "location": "Nowhere",
                "event_date": future_date_str(),
                "event_type": "academic",
            },
        )
        assert res.status_code == 401

    async def test_create_event_short_title_returns_422(self, client: AsyncClient, db: AsyncSession):
        """Title shorter than 3 characters fails validation."""
        user = await make_user(db, email=uniq("u"))
        res = await client.post(
            "/events/",
            data={
                "title": "AB",
                "description": "A great event for everyone",
                "location": "London",
                "event_date": future_date_str(),
                "event_type": "academic",
            },
            headers=auth_headers(user),
        )
        assert res.status_code == 422

    async def test_create_two_events_same_day_returns_409(self, client: AsyncClient, db: AsyncSession):
        """Organiser cannot have two events on the same day."""
        user = await make_user(db, email=uniq("u"))
        same_day = future_date_str(500)
        await client.post(
            "/events/",
            data={
                "title": "First Event",
                "description": "A great event for everyone",
                "location": "London",
                "event_date": same_day,
                "event_type": "academic",
            },
            headers=auth_headers(user),
        )
        res = await client.post(
            "/events/",
            data={
                "title": "Second Event",
                "description": "Another great event for everyone",
                "location": "Manchester",
                "event_date": same_day,
                "event_type": "social",
            },
            headers=auth_headers(user),
        )
        assert res.status_code == 409


# ---------------------------------------------------------------------------
# List events
# ---------------------------------------------------------------------------

class TestListEvents:

    async def test_get_upcoming_events_returns_list(self, client: AsyncClient, db: AsyncSession):
        """GET /events/ returns a list (may be empty)."""
        res = await client.get("/events/")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    async def test_created_event_appears_in_upcoming(self, client: AsyncClient, db: AsyncSession):
        """A newly created future event appears in the upcoming list."""
        user = await make_user(db, email=uniq("u"))
        event = await create_event(client, user)

        res = await client.get("/events/")
        ids = [e["id"] for e in res.json()]
        assert event["id"] in ids

    async def test_get_past_events_returns_list(self, client: AsyncClient, db: AsyncSession):
        """GET /events/past returns a list."""
        res = await client.get("/events/past")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    async def test_filter_events_by_type(self, client: AsyncClient, db: AsyncSession):
        """?event_type=academic filters correctly."""
        user = await make_user(db, email=uniq("u"))
        await client.post(
            "/events/",
            data={
                "title": "Academic Event",
                "description": "A great academic event",
                "location": "Oxford",
                "event_date": future_date_str(450),
                "event_type": "academic",
            },
            headers=auth_headers(user),
        )

        res = await client.get("/events/?event_type=academic")
        assert res.status_code == 200
        for event in res.json():
            assert event["event_type"] == "academic"


# ---------------------------------------------------------------------------
# Get single event
# ---------------------------------------------------------------------------

class TestGetEvent:

    async def test_get_event_by_id_success(self, client: AsyncClient, db: AsyncSession):
        """GET /events/{id} returns the full event details."""
        user = await make_user(db, email=uniq("u"))
        created = await create_event(client, user)

        res = await client.get(f"/events/{created['id']}")
        assert res.status_code == 200
        assert res.json()["id"] == created["id"]

    async def test_get_event_not_found_returns_404(self, client: AsyncClient, db: AsyncSession):
        """Non-existent event ID returns 404."""
        res = await client.get("/events/999999")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Update event
# ---------------------------------------------------------------------------

class TestUpdateEvent:

    async def test_update_event_success(self, client: AsyncClient, db: AsyncSession):
        """Organiser can update their event."""
        user = await make_user(db, email=uniq("u"))
        event = await create_event(client, user)

        res = await client.patch(
            f"/events/{event['id']}",
            json={"title": "Updated Title"},
            headers=auth_headers(user),
        )
        assert res.status_code == 200
        assert res.json()["title"] == "Updated Title"

    async def test_update_event_by_non_organiser_returns_403(self, client: AsyncClient, db: AsyncSession):
        """Non-organiser cannot update the event."""
        organiser = await make_user(db, email=uniq("org"))
        other = await make_user(db, email=uniq("other"))
        event = await create_event(client, organiser)

        res = await client.patch(
            f"/events/{event['id']}",
            json={"title": "Hacked Title"},
            headers=auth_headers(other),
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# RSVP
# ---------------------------------------------------------------------------

class TestRSVP:

    async def test_rsvp_success(self, client: AsyncClient, db: AsyncSession):
        """User can RSVP to an event they did not organise."""
        organiser = await make_user(db, email=uniq("org"))
        attendee = await make_user(db, email=uniq("att"))
        event = await create_event(client, organiser)

        with patch("app.services.event_service.send_rsvp_confirmation_email"):
            res = await client.post(
                f"/events/{event['id']}/rsvp",
                headers=auth_headers(attendee),
            )
        assert res.status_code == 201
        assert res.json()["event_id"] == event["id"]

    async def test_rsvp_own_event_returns_400(self, client: AsyncClient, db: AsyncSession):
        """Organiser cannot RSVP to their own event."""
        user = await make_user(db, email=uniq("u"))
        event = await create_event(client, user)

        res = await client.post(f"/events/{event['id']}/rsvp", headers=auth_headers(user))
        assert res.status_code == 400

    async def test_rsvp_duplicate_returns_409(self, client: AsyncClient, db: AsyncSession):
        """RSVPing twice to the same event returns 409."""
        organiser = await make_user(db, email=uniq("org"))
        attendee = await make_user(db, email=uniq("att"))
        event = await create_event(client, organiser)

        with patch("app.services.event_service.send_rsvp_confirmation_email"):
            await client.post(f"/events/{event['id']}/rsvp", headers=auth_headers(attendee))
            res = await client.post(f"/events/{event['id']}/rsvp", headers=auth_headers(attendee))
        assert res.status_code == 409

    async def test_rsvp_requires_auth(self, client: AsyncClient, db: AsyncSession):
        """Unauthenticated RSVP returns 401."""
        organiser = await make_user(db, email=uniq("org"))
        event = await create_event(client, organiser)
        res = await client.post(f"/events/{event['id']}/rsvp")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Cancel RSVP
# ---------------------------------------------------------------------------

class TestCancelRSVP:

    async def test_cancel_rsvp_success(self, client: AsyncClient, db: AsyncSession):
        """User can cancel their RSVP and gets 204."""
        organiser = await make_user(db, email=uniq("org"))
        attendee = await make_user(db, email=uniq("att"))
        event = await create_event(client, organiser)

        with patch("app.services.event_service.send_rsvp_confirmation_email"):
            await client.post(f"/events/{event['id']}/rsvp", headers=auth_headers(attendee))

        res = await client.delete(f"/events/{event['id']}/rsvp", headers=auth_headers(attendee))
        assert res.status_code == 204

    async def test_cancel_rsvp_not_registered_returns_404(self, client: AsyncClient, db: AsyncSession):
        """Cancelling an RSVP the user never made returns 404."""
        organiser = await make_user(db, email=uniq("org"))
        attendee = await make_user(db, email=uniq("att"))
        event = await create_event(client, organiser)

        res = await client.delete(f"/events/{event['id']}/rsvp", headers=auth_headers(attendee))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# My RSVPs
# ---------------------------------------------------------------------------

class TestMyRSVPs:

    async def test_get_rsvped_events_empty(self, client: AsyncClient, db: AsyncSession):
        """User with no RSVPs gets an empty list."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get("/events/rsvps", headers=auth_headers(user))
        assert res.status_code == 200
        assert res.json() == []

    async def test_get_rsvped_events_includes_registration(self, client: AsyncClient, db: AsyncSession):
        """RSVPed event appears in the user's RSVP list."""
        organiser = await make_user(db, email=uniq("org"))
        attendee = await make_user(db, email=uniq("att"))
        event = await create_event(client, organiser)

        with patch("app.services.event_service.send_rsvp_confirmation_email"):
            await client.post(f"/events/{event['id']}/rsvp", headers=auth_headers(attendee))

        res = await client.get("/events/rsvps", headers=auth_headers(attendee))
        assert res.status_code == 200
        event_ids = [r["event_id"] for r in res.json()]
        assert event["id"] in event_ids
