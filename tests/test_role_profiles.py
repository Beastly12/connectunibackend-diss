"""
Tests for role-profile endpoints and the verification-status flow.

POST /profile/student
POST /profile/alumni
POST /profile/professional
POST /profile/mentorship/preferences
GET  /profile/me
PUT  /profile/{user_id}/verification
"""
import io
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, make_user
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def make_student_user(db: AsyncSession, *, email="student@uni.ac.uk") -> User:
    return await make_user(db, email=email, full_name="Alice Student")


async def make_alumni_user(db: AsyncSession, *, email="alumni@test.com") -> User:
    return await make_user(db, email=email, full_name="Bob Alumni", grad_year=2020)


async def make_professional_user(db: AsyncSession, *, email="pro@corp.com") -> User:
    return await make_user(db, email=email, full_name="Carol Pro", grad_year=2018)


_admin_counter = 0


async def make_admin_user(db: AsyncSession) -> User:
    global _admin_counter
    _admin_counter += 1
    user = await make_user(
        db,
        email=f"admin{_admin_counter}@connectuni.com",
        full_name="Admin User",
    )
    user.user_role = "ADMIN"
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Student profile
# ---------------------------------------------------------------------------

class TestStudentProfile:
    async def test_create_student_profile(self, client: AsyncClient, db: AsyncSession):
        user = await make_student_user(db, email="student1@test.com")
        resp = await client.post(
            "/profile/student",
            json={
                "university_name": "Oxford University",
                "course_title": "Computer Science",
                "year_of_study": 2,
                "expected_graduation": 2027,
            },
            headers=auth_headers(user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["university_name"] == "Oxford University"
        assert data["course_title"] == "Computer Science"
        assert data["year_of_study"] == 2
        assert data["user_id"] == user.id

    async def test_update_student_profile(self, client: AsyncClient, db: AsyncSession):
        user = await make_student_user(db, email="student2@test.com")
        headers = auth_headers(user)
        await client.post(
            "/profile/student",
            json={
                "university_name": "Oxford University",
                "course_title": "Computer Science",
                "year_of_study": 2,
                "expected_graduation": 2027,
            },
            headers=headers,
        )
        resp = await client.post(
            "/profile/student",
            json={
                "university_name": "Cambridge University",
                "course_title": "Mathematics",
                "year_of_study": 3,
                "expected_graduation": 2028,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["university_name"] == "Cambridge University"
        assert resp.json()["year_of_study"] == 3

    async def test_student_profile_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/profile/student",
            json={
                "university_name": "Oxford",
                "course_title": "CS",
                "year_of_study": 1,
                "expected_graduation": 2027,
            },
        )
        assert resp.status_code == 401

    async def test_student_profile_invalid_year(self, client: AsyncClient, db: AsyncSession):
        user = await make_student_user(db, email="student3@test.com")
        resp = await client.post(
            "/profile/student",
            json={
                "university_name": "Oxford",
                "course_title": "CS",
                "year_of_study": 0,  # below minimum (ge=1)
                "expected_graduation": 2027,
            },
            headers=auth_headers(user),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Alumni profile
# ---------------------------------------------------------------------------

class TestAlumniProfile:
    async def test_create_alumni_profile_no_certificate(
        self, client: AsyncClient, db: AsyncSession
    ):
        user = await make_alumni_user(db, email="alumni1@test.com")
        with patch("app.services.role_profile_service.send_certificate_received_email"):
            resp = await client.post(
                "/profile/alumni",
                data={
                    "university_name": "Imperial College London",
                    "course_completed": "Electrical Engineering",
                    "graduation_year": "2020",
                },
                headers=auth_headers(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["graduation_year"] == 2020
        assert data["certificate_url"] is None

    async def test_create_alumni_profile_with_certificate(
        self, client: AsyncClient, db: AsyncSession
    ):
        user = await make_alumni_user(db, email="alumni2@test.com")
        fake_file = io.BytesIO(b"fake pdf content")

        with (
            patch(
                "app.services.role_profile_service.send_certificate_received_email"
            ),
            patch(
                "app.services.image_service.ImageService.upload",
                return_value={
                    "url": "https://cloudinary.com/cert.pdf",
                    "public_id": "cert_abc",
                },
            ),
        ):
            resp = await client.post(
                "/profile/alumni",
                data={
                    "university_name": "UCL",
                    "course_completed": "Physics",
                    "graduation_year": "2021",
                },
                files={"certificate": ("cert.pdf", fake_file, "application/pdf")},
                headers=auth_headers(user),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["certificate_url"] == "https://cloudinary.com/cert.pdf"

    async def test_alumni_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/profile/alumni",
            data={
                "university_name": "UCL",
                "course_completed": "Physics",
                "graduation_year": "2021",
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Professional profile
# ---------------------------------------------------------------------------

class TestProfessionalProfile:
    async def test_create_professional_profile(
        self, client: AsyncClient, db: AsyncSession
    ):
        user = await make_professional_user(db, email="pro1@corp.com")
        resp = await client.post(
            "/profile/professional",
            json={
                "job_title": "Software Engineer",
                "company": "Acme Ltd",
                "industry_sector": "Technology",
                "years_of_experience": 5,
                "linkedin_url": None,
            },
            headers=auth_headers(user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_title"] == "Software Engineer"
        assert data["company"] == "Acme Ltd"

    async def test_professional_profile_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/profile/professional",
            json={
                "job_title": "Engineer",
                "company": "Corp",
                "industry_sector": "Tech",
                "years_of_experience": 3,
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Mentorship preferences
# ---------------------------------------------------------------------------

class TestMentorshipPreferences:
    async def test_set_mentorship_preferences(
        self, client: AsyncClient, db: AsyncSession
    ):
        user = await make_user(db, email="mentor1@test.com", full_name="Dave Mentor")
        with patch(
            "app.services.role_profile_service.send_mentorship_preferences_email"
        ):
            resp = await client.post(
                "/profile/mentorship/preferences",
                json={
                    "is_mentor": True,
                    "is_mentee": False,
                    "areas_of_interest": ["backend", "cloud"],
                    "availability_hours_per_week": 3,
                    "preferred_format": "video",
                },
                headers=auth_headers(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_mentor"] is True
        assert data["areas_of_interest"] == ["backend", "cloud"]
        assert data["preferred_format"] == "video"

    async def test_must_be_mentor_or_mentee(
        self, client: AsyncClient, db: AsyncSession
    ):
        user = await make_user(db, email="mentor2@test.com", full_name="Eve User")
        resp = await client.post(
            "/profile/mentorship/preferences",
            json={
                "is_mentor": False,
                "is_mentee": False,  # neither — should fail validation
                "areas_of_interest": ["design"],
                "availability_hours_per_week": 2,
                "preferred_format": "chat",
            },
            headers=auth_headers(user),
        )
        assert resp.status_code == 422

    async def test_areas_of_interest_required(
        self, client: AsyncClient, db: AsyncSession
    ):
        user = await make_user(db, email="mentor3@test.com", full_name="Frank User")
        resp = await client.post(
            "/profile/mentorship/preferences",
            json={
                "is_mentor": True,
                "is_mentee": False,
                "areas_of_interest": [],  # empty — should fail
                "availability_hours_per_week": 2,
                "preferred_format": "in_person",
            },
            headers=auth_headers(user),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Full profile
# ---------------------------------------------------------------------------

class TestFullProfile:
    async def test_get_full_profile_empty(self, client: AsyncClient, db: AsyncSession):
        user = await make_user(db, email="full1@test.com", full_name="Grace User")
        resp = await client.get("/profile/me", headers=auth_headers(user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "full1@test.com"
        assert data["student_profile"] is None
        assert data["alumni_profile"] is None
        assert data["professional_profile"] is None
        assert data["mentorship_preferences"] is None

    async def test_get_full_profile_with_student(
        self, client: AsyncClient, db: AsyncSession
    ):
        user = await make_user(db, email="full2@test.com", full_name="Henry Student")
        headers = auth_headers(user)
        await client.post(
            "/profile/student",
            json={
                "university_name": "Leeds",
                "course_title": "Physics",
                "year_of_study": 1,
                "expected_graduation": 2028,
            },
            headers=headers,
        )
        resp = await client.get("/profile/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["student_profile"]["university_name"] == "Leeds"
        assert data["alumni_profile"] is None

    async def test_get_full_profile_requires_auth(self, client: AsyncClient):
        resp = await client.get("/profile/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Admin: update verification status
# ---------------------------------------------------------------------------

class TestVerificationStatusUpdate:
    async def test_admin_can_update_verification_status(
        self, client: AsyncClient, db: AsyncSession
    ):
        admin = await make_admin_user(db)
        target = await make_user(db, email="target1@test.com", full_name="Target User")

        with patch(
            "app.services.role_profile_service.send_verification_status_update_email"
        ):
            resp = await client.put(
                f"/profile/{target.id}/verification",
                json={"verification_status": "verified"},
                headers=auth_headers(admin),
            )
        assert resp.status_code == 200
        assert resp.json()["verification_status"] == "verified"

    async def test_non_admin_cannot_update_verification(
        self, client: AsyncClient, db: AsyncSession
    ):
        regular = await make_user(db, email="regular1@test.com", full_name="Regular User")
        target = await make_user(db, email="target2@test.com", full_name="Target User2")

        resp = await client.put(
            f"/profile/{target.id}/verification",
            json={"verification_status": "verified"},
            headers=auth_headers(regular),
        )
        assert resp.status_code == 403

    async def test_update_nonexistent_user_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ):
        admin = await make_admin_user(db)
        # Use a second admin or refresh the existing one if already exists
        with patch(
            "app.services.role_profile_service.send_verification_status_update_email"
        ):
            resp = await client.put(
                "/profile/999999/verification",
                json={"verification_status": "verified"},
                headers=auth_headers(admin),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# .ac.uk institutional verification (auth flow)
# ---------------------------------------------------------------------------

class TestAcUkVerification:
    async def test_acuk_student_gets_verified_on_email_click(
        self, client: AsyncClient, db: AsyncSession
    ):
        """
        A student with an .ac.uk email should have verification_status set to
        'verified' as soon as they click the verification link.
        """
        import secrets
        token = secrets.token_urlsafe(32)
        user = User(
            email="alice@student.oxford.ac.uk",
            full_name="Alice Oxford",
            university="Oxford",
            grad_year=2027,
            major="CS",
            password_hash="hashed",
            is_active=True,
            is_verified=False,
            verification_token=token,
            user_role="STUDENT",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        resp = await client.get(f"/auth/verify-email?token={token}")
        assert resp.status_code == 200

        await db.refresh(user)
        assert user.is_verified is True
        assert user.verification_status == "verified"

    async def test_non_acuk_student_stays_unverified_after_email_click(
        self, client: AsyncClient, db: AsyncSession
    ):
        import secrets
        token = secrets.token_urlsafe(32)
        user = User(
            email="bob@gmail.com",
            full_name="Bob Gmail",
            university="Some Uni",
            grad_year=2027,
            major="History",
            password_hash="hashed",
            is_active=True,
            is_verified=False,
            verification_token=token,
            user_role="STUDENT",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        resp = await client.get(f"/auth/verify-email?token={token}")
        assert resp.status_code == 200

        await db.refresh(user)
        assert user.is_verified is True
        # Non .ac.uk student stays unverified (only email verified, not institution)
        assert user.verification_status == "unverified"
