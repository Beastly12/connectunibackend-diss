"""
Tests for mentorship milestone endpoints (2.1).

POST /mentorship/relationships/{relationship_id}/milestones
GET  /mentorship/relationships/{relationship_id}/milestones
PUT  /mentorship/milestones/{milestone_id}
DELETE /mentorship/milestones/{milestone_id}
"""
from datetime import date
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.models.mentorship_relationship import MentorshipRelationship
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# Relationships are created directly in the DB — no MentorProfile needed
# because milestone endpoints only check rel.mentor_id / rel.mentee_id.
# ---------------------------------------------------------------------------

async def make_mentor(db: AsyncSession, *, email="mentor@test.com", university="Test Uni"):
    user = await make_user(db, email=email, university=university)
    return user


async def make_active_relationship(
    db: AsyncSession,
    mentor_user,
    mentee_user,
) -> MentorshipRelationship:
    rel = MentorshipRelationship(
        mentor_id=mentor_user.id,
        mentee_id=mentee_user.id,
        goal="Career growth",
        meeting_frequency="weekly",
        session_length_minutes=60,
        status=MentorshipRelationshipStatus.ACTIVE,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


_counter = 0


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"{prefix}_{_counter}@test.com"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMilestones:

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_create_milestone_as_mentor_succeeds(self, mock_ws, client: AsyncClient, db: AsyncSession):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        payload = {"title": "Write CV", "sort_order": 1}
        res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json=payload,
            headers=auth_headers(mentor),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Write CV"
        assert data["status"] == "todo"
        assert data["sort_order"] == 1
        assert data["completed_date"] is None

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_create_milestone_as_mentee_forbidden(self, mock_ws, client: AsyncClient, db: AsyncSession):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Sneaky milestone"},
            headers=auth_headers(mentee),
        )
        assert res.status_code == 403

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_create_milestone_in_someone_elses_relationship_is_forbidden(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        outsider = await make_mentor(db, email=uniq("outsider"))
        rel = await make_active_relationship(db, mentor, mentee)

        res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Hack milestone"},
            headers=auth_headers(outsider),
        )
        assert res.status_code == 403

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_list_milestones_ordered_by_sort_order(self, mock_ws, client: AsyncClient, db: AsyncSession):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        for sort_order, title in [(3, "Third"), (1, "First"), (2, "Second")]:
            await client.post(
                f"/mentorship/relationships/{rel.id}/milestones",
                json={"title": title, "sort_order": sort_order},
                headers=auth_headers(mentor),
            )

        res = await client.get(
            f"/mentorship/relationships/{rel.id}/milestones",
            headers=auth_headers(mentee),
        )
        assert res.status_code == 200
        titles = [m["title"] for m in res.json()]
        assert titles == ["First", "Second", "Third"]

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_update_milestone_status_to_completed_sets_completed_date(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        create_res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Learn Python"},
            headers=auth_headers(mentor),
        )
        milestone_id = create_res.json()["id"]

        update_res = await client.put(
            f"/mentorship/milestones/{milestone_id}",
            json={"status": "completed"},
            headers=auth_headers(mentor),
        )
        assert update_res.status_code == 200
        data = update_res.json()
        assert data["status"] == "completed"
        assert data["completed_date"] == date.today().isoformat()

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_mentee_can_update_status(self, mock_ws, client: AsyncClient, db: AsyncSession):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        create_res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Network"},
            headers=auth_headers(mentor),
        )
        milestone_id = create_res.json()["id"]

        update_res = await client.put(
            f"/mentorship/milestones/{milestone_id}",
            json={"status": "in_progress"},
            headers=auth_headers(mentee),
        )
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "in_progress"

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_mentee_cannot_update_title(self, mock_ws, client: AsyncClient, db: AsyncSession):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        create_res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Original Title"},
            headers=auth_headers(mentor),
        )
        milestone_id = create_res.json()["id"]

        res = await client.put(
            f"/mentorship/milestones/{milestone_id}",
            json={"title": "Hacked Title"},
            headers=auth_headers(mentee),
        )
        assert res.status_code == 403

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_delete_milestone_as_mentor_succeeds(self, mock_ws, client: AsyncClient, db: AsyncSession):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        create_res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Delete me"},
            headers=auth_headers(mentor),
        )
        milestone_id = create_res.json()["id"]

        del_res = await client.delete(
            f"/mentorship/milestones/{milestone_id}",
            headers=auth_headers(mentor),
        )
        assert del_res.status_code == 204

        # Confirm it's gone
        list_res = await client.get(
            f"/mentorship/relationships/{rel.id}/milestones",
            headers=auth_headers(mentor),
        )
        assert list_res.json() == []

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_delete_milestone_as_mentee_forbidden(self, mock_ws, client: AsyncClient, db: AsyncSession):
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        create_res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Protected milestone"},
            headers=auth_headers(mentor),
        )
        milestone_id = create_res.json()["id"]

        res = await client.delete(
            f"/mentorship/milestones/{milestone_id}",
            headers=auth_headers(mentee),
        )
        assert res.status_code == 403

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_progress_percentage_in_relationship_response(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """2 of 4 milestones completed → progress_percentage == 50."""
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        for i in range(4):
            create_res = await client.post(
                f"/mentorship/relationships/{rel.id}/milestones",
                json={"title": f"Milestone {i}"},
                headers=auth_headers(mentor),
            )
            milestone_id = create_res.json()["id"]
            if i < 2:  # mark first two as completed
                await client.put(
                    f"/mentorship/milestones/{milestone_id}",
                    json={"status": "completed"},
                    headers=auth_headers(mentor),
                )

        rel_res = await client.get(
            f"/mentorship/relationships/{rel.id}",
            headers=auth_headers(mentor),
        )
        assert rel_res.status_code == 200
        assert rel_res.json()["progress_percentage"] == 50

    @patch("app.services.notification_service.ws_manager.send_to_user", new_callable=AsyncMock)
    async def test_milestone_completed_notification_sent(
        self, mock_ws, client: AsyncClient, db: AsyncSession
    ):
        """Completing a milestone triggers MILESTONE_COMPLETED notification to the other party."""
        mentor = await make_mentor(db, email=uniq("mentor"))
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_relationship(db, mentor, mentee)

        create_res = await client.post(
            f"/mentorship/relationships/{rel.id}/milestones",
            json={"title": "Notify me"},
            headers=auth_headers(mentor),
        )
        milestone_id = create_res.json()["id"]

        # Mock email so test doesn't try to send real SMTP
        with patch("app.services.mentorship_service.send_milestone_completed_email"):
            await client.put(
                f"/mentorship/milestones/{milestone_id}",
                json={"status": "completed"},
                headers=auth_headers(mentor),
            )

        # WebSocket notification should have been called (for the mentee)
        assert mock_ws.called
