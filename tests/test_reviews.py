"""
Tests for mentorship reviews and ratings (2.2).

POST /mentorship/relationships/{relationship_id}/review
GET  /mentorship/mentors/{user_id}/reviews
GET  /mentorship/mentors/{user_id}/rating
"""
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.models.mentorship_relationship import MentorshipRelationship
from app.enums.mentorship_relationship_status import MentorshipRelationshipStatus

pytestmark = pytest.mark.asyncio

_counter = 0


def uniq(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"rev_{prefix}_{_counter}@test.com"


async def make_mentor_user(db, *, email=""):
    """Create a user who acts as a mentor — no MentorProfile needed for review endpoints."""
    user = await make_user(db, email=email or uniq("mentor"))
    return user


async def make_active_rel(db, mentor, mentee) -> MentorshipRelationship:
    rel = MentorshipRelationship(
        mentor_id=mentor.id,
        mentee_id=mentee.id,
        goal="Career growth",
        meeting_frequency="weekly",
        session_length_minutes=60,
        status=MentorshipRelationshipStatus.ACTIVE,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


class TestReviews:

    async def test_mentee_can_leave_review(self, client: AsyncClient, db: AsyncSession):
        """Mentee leaves a rating-5 review — should succeed with 201."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_rel(db, mentor, mentee)

        res = await client.post(
            f"/mentorship/relationships/{rel.id}/review",
            json={"rating": 5, "review_text": "Excellent mentor!"},
            headers=auth_headers(mentee),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["rating"] == 5
        assert data["review_text"] == "Excellent mentor!"
        assert data["reviewer_id"] == mentee.id
        assert data["reviewee_id"] == mentor.id

    async def test_mentor_cannot_leave_review(self, client: AsyncClient, db: AsyncSession):
        """Mentor trying to review their own relationship returns 403."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_rel(db, mentor, mentee)

        res = await client.post(
            f"/mentorship/relationships/{rel.id}/review",
            json={"rating": 4},
            headers=auth_headers(mentor),
        )
        assert res.status_code == 403

    async def test_duplicate_review_returns_conflict(self, client: AsyncClient, db: AsyncSession):
        """Second review on the same relationship returns 409."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_rel(db, mentor, mentee)

        await client.post(
            f"/mentorship/relationships/{rel.id}/review",
            json={"rating": 3},
            headers=auth_headers(mentee),
        )
        res = await client.post(
            f"/mentorship/relationships/{rel.id}/review",
            json={"rating": 5},
            headers=auth_headers(mentee),
        )
        assert res.status_code == 409

    async def test_rating_boundary_validation(self, client: AsyncClient, db: AsyncSession):
        """Rating must be between 1 and 5 inclusive."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("mentee"))
        rel = await make_active_rel(db, mentor, mentee)

        for bad_rating in [0, 6]:
            res = await client.post(
                f"/mentorship/relationships/{rel.id}/review",
                json={"rating": bad_rating},
                headers=auth_headers(mentee),
            )
            assert res.status_code == 422

    async def test_get_mentor_reviews(self, client: AsyncClient, db: AsyncSession):
        """GET /mentorship/mentors/{user_id}/reviews returns all reviews for that mentor."""
        mentor = await make_mentor_user(db)
        mentee1 = await make_user(db, email=uniq("m1"))
        mentee2 = await make_user(db, email=uniq("m2"))
        rel1 = await make_active_rel(db, mentor, mentee1)
        rel2 = await make_active_rel(db, mentor, mentee2)

        await client.post(
            f"/mentorship/relationships/{rel1.id}/review",
            json={"rating": 5, "review_text": "Great!"},
            headers=auth_headers(mentee1),
        )
        await client.post(
            f"/mentorship/relationships/{rel2.id}/review",
            json={"rating": 3, "review_text": "OK"},
            headers=auth_headers(mentee2),
        )

        # Anyone (even the mentor) can see reviews — use mentee1 as viewer
        res = await client.get(
            f"/mentorship/mentors/{mentor.id}/reviews",
            headers=auth_headers(mentee1),
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        ratings = {r["rating"] for r in data}
        assert ratings == {5, 3}

    async def test_get_mentor_rating_aggregation(self, client: AsyncClient, db: AsyncSession):
        """GET /mentorship/mentors/{user_id}/rating returns average_rating and total_reviews."""
        mentor = await make_mentor_user(db)
        mentee1 = await make_user(db, email=uniq("r1"))
        mentee2 = await make_user(db, email=uniq("r2"))
        rel1 = await make_active_rel(db, mentor, mentee1)
        rel2 = await make_active_rel(db, mentor, mentee2)

        await client.post(
            f"/mentorship/relationships/{rel1.id}/review",
            json={"rating": 4},
            headers=auth_headers(mentee1),
        )
        await client.post(
            f"/mentorship/relationships/{rel2.id}/review",
            json={"rating": 2},
            headers=auth_headers(mentee2),
        )

        res = await client.get(
            f"/mentorship/mentors/{mentor.id}/rating",
            headers=auth_headers(mentee1),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_reviews"] == 2
        assert data["average_rating"] == 3.0  # (4 + 2) / 2

    async def test_get_rating_no_reviews(self, client: AsyncClient, db: AsyncSession):
        """Mentor with no reviews returns null average_rating and 0 total_reviews."""
        mentor = await make_mentor_user(db)
        mentee = await make_user(db, email=uniq("m"))

        res = await client.get(
            f"/mentorship/mentors/{mentor.id}/rating",
            headers=auth_headers(mentee),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["average_rating"] is None
        assert data["total_reviews"] == 0
