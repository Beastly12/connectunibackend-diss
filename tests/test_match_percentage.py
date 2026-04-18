"""
Unit tests for the match percentage algorithm (2.3).
Tests the pure static method directly — no DB or HTTP needed.
"""
import pytest
from unittest.mock import MagicMock

from app.services.mentorship_service import MentorshipService
from app.enums.preferred_format import PreferredFormat

pytestmark = pytest.mark.asyncio


def _make_user(university: str = "Test Uni") -> MagicMock:
    user = MagicMock()
    user.university = university
    return user


def _make_mentor_profile(expertise_areas: list[str], university: str = "Test Uni") -> MagicMock:
    profile = MagicMock()
    profile.expertise_areas = expertise_areas
    profile.user = _make_user(university)
    return profile


def _make_prefs(areas: list[str] | None, fmt: str = "video") -> MagicMock:
    prefs = MagicMock()
    prefs.areas_of_interest = areas
    prefs.preferred_format = fmt
    return prefs


class TestMatchPercentage:

    def test_full_overlap_and_same_university_and_same_format(self):
        """
        Full area overlap (70) + same university (15) + same format (15) = 100.
        """
        mentee = _make_user("Oxford")
        mentee_prefs = _make_prefs(["Python", "Machine Learning"], fmt=PreferredFormat.VIDEO)
        mentor_profile = _make_mentor_profile(["Python", "Machine Learning"], university="Oxford")
        mentor_prefs = _make_prefs(["Python"], fmt=PreferredFormat.VIDEO)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        assert score == 100

    def test_no_area_overlap_gives_zero_area_score(self):
        """No matching areas → area contribution is 0."""
        mentee = _make_user("Oxford")
        mentee_prefs = _make_prefs(["Python"], fmt=PreferredFormat.VIDEO)
        mentor_profile = _make_mentor_profile(["Java"], university="Cambridge")
        mentor_prefs = _make_prefs(["Java"], fmt=PreferredFormat.IN_PERSON)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        assert score == 0

    def test_same_university_adds_15_points(self):
        """When areas don't match and format doesn't match, same university alone adds 15."""
        mentee = _make_user("Oxford")
        mentee_prefs = _make_prefs(["Python"], fmt=PreferredFormat.VIDEO)
        mentor_profile = _make_mentor_profile(["Java"], university="Oxford")
        mentor_prefs = _make_prefs(["Java"], fmt=PreferredFormat.CHAT)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        assert score == 15

    def test_different_university_no_bonus(self):
        """Different universities → no 15-point bonus."""
        mentee = _make_user("Oxford")
        mentee_prefs = _make_prefs(["Python"], fmt=PreferredFormat.VIDEO)
        mentor_profile = _make_mentor_profile(["Python"], university="Cambridge")
        mentor_prefs = _make_prefs(["Python"], fmt=PreferredFormat.VIDEO)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        # 70 (full area overlap) + 0 (different uni) + 15 (same format) = 85
        assert score == 85

    def test_same_format_adds_15_points(self):
        """When only format matches, score is 15."""
        mentee = _make_user("A")
        mentee_prefs = _make_prefs(["Python"], fmt=PreferredFormat.VIDEO)
        mentor_profile = _make_mentor_profile(["Java"], university="B")
        mentor_prefs = _make_prefs(["Java"], fmt=PreferredFormat.VIDEO)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        assert score == 15

    def test_score_capped_at_100(self):
        """Score cannot exceed 100 even with theoretical over-counting."""
        mentee = _make_user("Oxford")
        mentee_prefs = _make_prefs(["A", "B", "C"], fmt=PreferredFormat.VIDEO)
        mentor_profile = _make_mentor_profile(["A", "B", "C"], university="Oxford")
        mentor_prefs = _make_prefs(["A"], fmt=PreferredFormat.VIDEO)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        assert score == 100

    def test_no_mentee_preferences_returns_zero_area_and_format_score(self):
        """When the mentee has no preferences, area score and format score are 0."""
        mentee = _make_user("Oxford")
        mentor_profile = _make_mentor_profile(["Python"], university="Cambridge")

        score = MentorshipService._compute_match_percentage(
            mentee, None, mentor_profile, None
        )
        assert score == 0  # no prefs → no area match, no uni match (different), no format match

    def test_partial_area_overlap(self):
        """
        Mentee has 4 areas of interest, mentor covers 2 of them.
        Area score: (2/4) * 70 = 35.
        """
        mentee = _make_user("Cambridge")
        mentee_prefs = _make_prefs(
            ["Python", "Machine Learning", "Data Science", "Cloud"],
            fmt=PreferredFormat.CHAT,
        )
        mentor_profile = _make_mentor_profile(["Python", "Machine Learning"], university="Oxford")
        mentor_prefs = _make_prefs(["Python"], fmt=PreferredFormat.IN_PERSON)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        assert score == 35  # 35 areas only, no bonus

    def test_case_insensitive_area_matching(self):
        """Area matching is case-insensitive."""
        mentee = _make_user("X")
        mentee_prefs = _make_prefs(["python"], fmt=PreferredFormat.VIDEO)
        mentor_profile = _make_mentor_profile(["Python"], university="Y")
        mentor_prefs = _make_prefs(["Python"], fmt=PreferredFormat.CHAT)

        score = MentorshipService._compute_match_percentage(
            mentee, mentee_prefs, mentor_profile, mentor_prefs
        )
        assert score == 70  # full area overlap (70), different format, different uni
