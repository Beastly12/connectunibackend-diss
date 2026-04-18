"""
Tests for mentorship notification triggers (2.6).

Covers:
- SESSION_CANCELLED notification on session update
- RESOURCE_SHARED notification on resource creation
- RELATIONSHIP_ENDED notification on relationship end
- MENTEE_CANCELLED_REQUEST notification on request cancellation
- MILESTONE_COMPLETED notification on milestone completion
"""
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.models.mentorship_relationship import MentorshipRelationship
from app.models.mentorship_session import MentorshipSession
from app.models.mentorship_request import MentorshipRequest
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus
from app.enums.mentorship_session_status import MentorshipSessionStatus
from app.enums.mentorship_request_status import MentorshipRequestStatus
from app.enums.notification_type import NotificationType
from app.repositories.notification_repository import NotificationRepository

pytestmark = pytest.mark.asyncio

_counter = 0


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"notif_{prefix}_{_counter}@test.com"


async def make_mentor_user(db, email=""):
    user = await make_user(db, email=email or uniq("mentor"))
    return user


async def make_active_rel(db, mentor, mentee) -> MentorshipRelationship:
    rel = MentorshipRelationship(
        mentor_id=mentor.id,
        mentee_id=mentee.id,
        goal="Growth",
        meeting_frequency="weekly",
        session_length_minutes=60,
        status=MentorshipRelationshipStatus.ACTIVE,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


async def get_notifications_for_user(db, user_id: int, notif_type: str) -> list:
    repo = NotificationRepository(db)
    all_notifs = await repo.get_for_user(user_id=user_id, limit=50)
    return [n for n in all_notifs if n.type == notif_type]


class TestMentorshipNotifications:

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_session_cancelled_notifies_other_participant(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """When mentor cancels a session, the mentee receives SESSION_CANCELLED notification."""
        from datetime import datetime, timezone, timedelta

        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        rel = await make_active_rel(db, mentor, mentee)

        future = datetime.now(timezone.utc) + timedelta(days=2)
        session = MentorshipSession(
            relationship_id=rel.id,
            scheduled_at=future,
            status=MentorshipSessionStatus.UPCOMING,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        with patch("app.services.mentorship_service.send_session_cancelled_email"):
            res = await client.patch(
                f"/mentorship/relationships/{rel.id}/sessions/{session.id}",
                json={"status": "cancelled"},
                headers=auth_headers(mentor),
            )
        assert res.status_code == 200

        # Verify in-app notification was created for the mentee
        notifs = await get_notifications_for_user(db, mentee.id, NotificationType.SESSION_CANCELLED)
        assert len(notifs) >= 1

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_resource_shared_notifies_other_participant(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """When mentor shares a resource, the mentee receives RESOURCE_SHARED notification."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        rel = await make_active_rel(db, mentor, mentee)

        with patch("app.services.mentorship_service.send_resource_shared_email"):
            res = await client.post(
                f"/mentorship/relationships/{rel.id}/resources",
                json={
                    "title": "Python Book",
                    "category": "Article",
                    "url": "https://example.com",
                },
                headers=auth_headers(mentor),
            )
        assert res.status_code == 201

        notifs = await get_notifications_for_user(db, mentee.id, NotificationType.RESOURCE_SHARED)
        assert len(notifs) >= 1

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_relationship_ended_notifies_other_participant(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """When mentor ends a relationship, the mentee receives RELATIONSHIP_ENDED notification."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        rel = await make_active_rel(db, mentor, mentee)

        with patch("app.services.mentorship_service.send_relationship_ended_email"):
            res = await client.patch(
                f"/mentorship/relationships/{rel.id}/end",
                headers=auth_headers(mentor),
            )
        assert res.status_code == 200

        notifs = await get_notifications_for_user(db, mentee.id, NotificationType.RELATIONSHIP_ENDED)
        assert len(notifs) >= 1

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_mentee_cancelled_request_notifies_mentor(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """When mentee cancels a request, the mentor receives MENTEE_CANCELLED_REQUEST notification."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))

        # Create a pending request directly in DB
        req = MentorshipRequest(
            mentee_id=mentee.id,
            mentor_id=mentor.id,
            goal="Learn things",
            meeting_frequency="weekly",
            session_length_minutes=60,
            message="Please mentor me",
            status=MentorshipRequestStatus.PENDING,
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)

        with patch("app.services.mentorship_service.send_mentee_cancelled_request_email"):
            res = await client.delete(
                f"/mentorship/requests/{req.id}",
                headers=auth_headers(mentee),
            )
        assert res.status_code == 204

        notifs = await get_notifications_for_user(
            db, mentor.id, NotificationType.MENTEE_CANCELLED_REQUEST
        )
        assert len(notifs) >= 1

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_milestone_completed_notifies_other_participant(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """When mentee marks a milestone completed, the mentor receives MILESTONE_COMPLETED."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        rel = await make_active_rel(db, mentor, mentee)

        # Mentor creates milestone
        create_res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Big goal"},
            headers=auth_headers(mentor),
        )
        assert create_res.status_code == 201
        milestone_id = create_res.json()["id"]

        # Mentee marks it complete
        with patch("app.services.mentorship_service.send_milestone_completed_email"):
            res = await client.put(
                f"/mentorship/milestones/{milestone_id}",
                json={"status": "completed"},
                headers=auth_headers(mentee),
            )
        assert res.status_code == 200

        # Mentor should receive MILESTONE_COMPLETED notification
        notifs = await get_notifications_for_user(
            db, mentor.id, NotificationType.MILESTONE_COMPLETED
        )
        assert len(notifs) >= 1

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_session_reminder_notification_on_create(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """Creating a session triggers SESSION_REMINDER notifications for both participants."""
        from datetime import datetime, timezone, timedelta

        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))
        rel = await make_active_rel(db, mentor, mentee)

        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        res = await client.post(
            f"/mentorship/relationships/{rel.id}/sessions",
            json={"scheduled_at": future},
            headers=auth_headers(mentor),
        )
        assert res.status_code == 201

        # Both should receive SESSION_REMINDER
        mentor_notifs = await get_notifications_for_user(
            db, mentor.id, NotificationType.SESSION_REMINDER
        )
        mentee_notifs = await get_notifications_for_user(
            db, mentee.id, NotificationType.SESSION_REMINDER
        )
        assert len(mentor_notifs) >= 1
        assert len(mentee_notifs) >= 1
