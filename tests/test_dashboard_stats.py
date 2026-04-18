"""
Tests for the dashboard and mentorship stats endpoints (2.4).

GET /dashboard/stats
GET /mentorship/stats/me
"""
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.models.mentorship_relationship import MentorshipRelationship
from app.models.mentorship_session import MentorshipSession
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus
from app.enums.mentorship_session_status import MentorshipSessionStatus

pytestmark = pytest.mark.asyncio

_counter = 0


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"dash_{prefix}_{_counter}@test.com"


async def make_mentor_user(db, email=""):
    user = await make_user(db, email=email or uniq("mentor"))
    return user


async def make_active_rel(db, mentor, mentee) -> MentorshipRelationship:
    rel = MentorshipRelationship(
        mentor_id=mentor.id,
        mentee_id=mentee.id,
        goal="Goal",
        meeting_frequency="weekly",
        session_length_minutes=60,
        status=MentorshipRelationshipStatus.ACTIVE,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


class TestDashboardStats:

    async def test_dashboard_stats_structure(self, client: AsyncClient, db: AsyncSession):
        """GET /dashboard/stats returns the expected keys."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get("/dashboard/stats", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert "messages_unread" in data
        assert "upcoming_events" in data
        assert "upcoming_sessions" in data
        assert isinstance(data["upcoming_sessions"], list)

    async def test_dashboard_stats_placeholders_are_zero(self, client: AsyncClient, db: AsyncSession):
        """Until messaging/events integration, placeholder counts are 0."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get("/dashboard/stats", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert data["messages_unread"] == 0
        assert data["upcoming_events"] == 0

    async def test_dashboard_upcoming_sessions_included(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Upcoming future sessions appear in dashboard stats."""
        from datetime import datetime, timezone, timedelta

        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        rel = await make_active_rel(db, mentor, mentee)

        future = datetime.now(timezone.utc) + timedelta(days=3)
        session = MentorshipSession(
            relationship_id=rel.id,
            scheduled_at=future,
            status=MentorshipSessionStatus.UPCOMING,
        )
        db.add(session)
        await db.commit()

        res = await client.get("/dashboard/stats", headers=auth_headers(mentee))
        assert res.status_code == 200
        sessions = res.json()["upcoming_sessions"]
        assert len(sessions) >= 1
        assert sessions[0]["relationship_id"] == rel.id


class TestMentorshipStatsMe:

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_stats_structure(self, mock_ws, client: AsyncClient, db: AsyncSession):
        """GET /mentorship/stats/me returns as_mentee and as_mentor objects."""
        user = await make_user(db, email=uniq("u"))
        res = await client.get("/mentorship/stats/me", headers=auth_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert "as_mentee" in data
        assert "as_mentor" in data

        mentee_data = data["as_mentee"]
        assert "active_mentors" in mentee_data
        assert "pending_requests_sent" in mentee_data
        assert "completed_sessions" in mentee_data
        assert "overall_progress" in mentee_data

        mentor_data = data["as_mentor"]
        assert "active_mentees" in mentor_data
        assert "total_hours_mentored" in mentor_data
        assert "average_rating" in mentor_data
        assert "total_reviews" in mentor_data

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_active_mentors_count(self, mock_ws, client: AsyncClient, db: AsyncSession):
        """as_mentee.active_mentors reflects actual active relationships."""
        mentor1 = await make_mentor_user(db)
        mentor2 = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        await make_active_rel(db, mentor1, mentee)
        await make_active_rel(db, mentor2, mentee)

        res = await client.get("/mentorship/stats/me", headers=auth_headers(mentee))
        assert res.json()["as_mentee"]["active_mentors"] == 2

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_active_mentees_count(self, mock_ws, client: AsyncClient, db: AsyncSession):
        """as_mentor.active_mentees reflects actual active mentees."""
        mentor = await make_mentor_user(db)
        m1 = await make_user(db, email=uniq("m1"))
        m2 = await make_user(db, email=uniq("m2"))
        await make_active_rel(db, mentor, m1)
        await make_active_rel(db, mentor, m2)

        res = await client.get("/mentorship/stats/me", headers=auth_headers(mentor))
        assert res.json()["as_mentor"]["active_mentees"] == 2

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_resources_shared_count(self, mock_ws, client: AsyncClient, db: AsyncSession):
        """as_mentor.resources_shared counts resources created by this user."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        rel = await make_active_rel(db, mentor, mentee)

        with patch("app.services.mentorship_service.send_resource_shared_email"):
            for _ in range(3):
                await client.post(
                    f"/mentorship/relationships/{rel.id}/resources",
                    json={"title": "Resource", "category": "Article", "url": "https://example.com"},
                    headers=auth_headers(mentor),
                )

        res = await client.get("/mentorship/stats/me", headers=auth_headers(mentor))
        assert res.json()["as_mentor"]["resources_shared"] == 3
