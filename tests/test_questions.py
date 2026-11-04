"""
Unit tests for Question Bank, Daily Challenge Packs, Solution Paywall, and Anti-Leak Protection.
Verifies logged-in authentication enforcement, reverse-chronological series browsing,
and anti-leak time-locks preventing future question leaks.
"""

import unittest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.api.deps import (
    get_current_user,
    get_question_service,
    get_user_repository,
)
from app.core.security import get_optional_current_user
from app.domain.exceptions import AuthenticationError, PermissionDeniedError
from app.main import app
from app.services.question_service import QuestionService


class TestQuestionsFeature(unittest.TestCase):
    """Verifies question catalog, daily challenge packs, anti-leak locks, paywall, and RBAC."""

    def setUp(self) -> None:
        self.mock_service = AsyncMock(spec=QuestionService)
        self.mock_user_repo = AsyncMock()
        self.mock_user = {
            "uid": "usr_student_01",
            "email": "student@maths.lk",
            "role": "USER",
        }
        self.mock_user_repo.get_by_uid.return_value = {
            "uid": "usr_student_01",
            "role": "USER",
            "is_premium": False,
        }
        # Default dependency overrides: Authenticated student session & mocked repos
        app.dependency_overrides[get_question_service] = lambda: self.mock_service
        app.dependency_overrides[get_user_repository] = lambda: self.mock_user_repo
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        app.dependency_overrides[get_optional_current_user] = lambda: self.mock_user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_list_questions_requires_authentication(self) -> None:
        """Verifies that unauthenticated requests to /api/v1/questions return 401 Unauthorized."""
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app)
        response = client.get("/api/v1/questions")
        self.assertEqual(response.status_code, 401)

    def test_list_questions_authenticated(self) -> None:
        """Verifies that authenticated students receive lightweight question summaries."""
        self.mock_service.list_questions.return_value = [
            {
                "id": "q_2023_01",
                "title": "2023 A/L Combined Mathematics Paper I - Q1",
                "subject_id": "sub_pmat",
                "type": "SHORT",
                "difficulty": "MEDIUM",
                "schedule": "REGULAR",
                "source": "PAST_PAPER",
                "allocated_marks": 25,
                "is_premium": False,
            }
        ]
        client = TestClient(app)
        response = client.get("/api/v1/questions?subject_id=sub_pmat")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "q_2023_01")

    def test_get_daily_challenge_pack_success(self) -> None:
        """Verifies fetching an unlocked daily challenge pack with multiple questions."""
        self.mock_service.get_daily_pack.return_value = {
            "day_number": 1,
            "challenge_title": "Day 01 Combined Maths Challenge",
            "scheduled_date": "2026-11-03",
            "total_questions": 2,
            "total_marks": 75,
            "questions": [
                {
                    "id": "q_pmat_01",
                    "title": "Pure Maths Short",
                    "subject_id": "sub_pmat",
                    "type": "SHORT",
                    "difficulty": "MEDIUM",
                    "schedule": "DAILY",
                    "source": "PAST_PAPER",
                    "allocated_marks": 25,
                    "is_premium": False,
                    "scheduled_date": "2026-11-03",
                    "day_number": 1,
                },
                {
                    "id": "q_pmat_02",
                    "title": "Pure Maths Essay",
                    "subject_id": "sub_pmat",
                    "type": "ESSAY",
                    "difficulty": "HARD",
                    "schedule": "DAILY",
                    "source": "PAST_PAPER",
                    "allocated_marks": 50,
                    "is_premium": False,
                    "scheduled_date": "2026-11-03",
                    "day_number": 1,
                },
            ],
        }
        client = TestClient(app)
        response = client.get("/api/v1/questions/daily/pack?day=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["day_number"], 1)
        self.assertEqual(data["total_questions"], 2)
        self.assertEqual(len(data["questions"]), 2)

    def test_get_daily_challenge_pack_anti_leak_lock(self) -> None:
        """Verifies that requesting a future locked day returns HTTP 403 Forbidden without leaking content."""
        self.mock_service.get_daily_pack.side_effect = PermissionDeniedError(
            "Day 2 Challenge Pack is locked until 2026-11-05 00:00 AM Sri Lanka Time."
        )
        client = TestClient(app)
        response = client.get("/api/v1/questions/daily/pack?day=2")
        self.assertEqual(response.status_code, 403)
        self.assertIn("locked until", response.json()["detail"])

    def test_list_daily_challenge_series_reverse_chronological(self) -> None:
        """Verifies daily series catalog with safe teaser metadata for tomorrow's challenge."""
        self.mock_service.list_daily_series.return_value = [
            {
                "day_number": 2,
                "scheduled_date": "2026-11-05",
                "title": "Day 02 Challenge Workout",
                "total_questions": 4,
                "short_questions_count": 2,
                "essay_questions_count": 2,
                "total_marks": 100,
                "target_duration_seconds": 3600,
                "is_unlocked": False,
                "unlocks_at": "2026-11-05T00:00:00+05:30",
            },
            {
                "day_number": 1,
                "scheduled_date": "2026-11-04",
                "title": "Day 01 Challenge Workout",
                "total_questions": 4,
                "short_questions_count": 2,
                "essay_questions_count": 2,
                "total_marks": 100,
                "target_duration_seconds": 3600,
                "is_unlocked": True,
                "unlocks_at": None,
            },
        ]
        client = TestClient(app)
        response = client.get("/api/v1/questions/daily/series")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        # Newest (Day 2 tomorrow) is at the top
        self.assertEqual(data[0]["day_number"], 2)
        self.assertFalse(data[0]["is_unlocked"])
        self.assertEqual(data[0]["short_questions_count"], 2)
        self.assertEqual(data[0]["essay_questions_count"], 2)
        # Active Today (Day 1) is next
        self.assertEqual(data[1]["day_number"], 1)
        self.assertTrue(data[1]["is_unlocked"])

    def test_solution_free_marking_scheme_accessible(self) -> None:
        self.mock_service.get_marking_scheme.return_value = {
            "id": "ms_free_01",
            "question_id": "q_free_01",
            "title": "Official Solution",
            "content_text": "Step 1: Simplify the equation...",
            "content_type": "markdown",
            "total_marks": 25,
            "is_official": True,
            "is_premium_only": False,
            "pdf_url": None,
        }
        client = TestClient(app)
        response = client.get("/api/v1/questions/q_free_01/solution")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_premium_only"], False)

    def test_solution_premium_marking_scheme_blocks_unauthenticated(self) -> None:
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app)
        response = client.get("/api/v1/questions/q_prem_01/solution")
        self.assertEqual(response.status_code, 401)

    def test_solution_premium_marking_scheme_blocks_free_user(self) -> None:
        self.mock_service.get_marking_scheme.side_effect = PermissionDeniedError(
            "A premium subscription is required to view this marking scheme."
        )
        client = TestClient(app)
        response = client.get("/api/v1/questions/q_prem_01/solution")
        self.assertEqual(response.status_code, 403)
        self.assertIn("A premium subscription is required", response.json()["detail"])

    def test_solution_premium_marking_scheme_allows_subscriber(self) -> None:
        self.mock_service.get_marking_scheme.return_value = {
            "id": "ms_prem_01",
            "question_id": "q_prem_01",
            "title": "Masterclass Step-by-Step Marking Scheme",
            "content_text": "Complete derivation and breakdown...",
            "content_type": "markdown",
            "total_marks": 50,
            "is_official": True,
            "is_premium_only": True,
            "pdf_url": None,
        }
        self.mock_user_repo.get_by_uid.return_value = {
            "uid": "usr_student_01",
            "role": "USER",
            "is_premium": True,
        }
        client = TestClient(app)
        response = client.get("/api/v1/questions/q_prem_01/solution")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_premium_only"])

    def test_create_question_blocks_standard_user(self) -> None:
        client = TestClient(app)
        payload = {
            "title": "Unauthorized Question",
            "subject_id": "sub_pmat",
            "content_text": "Solve for x",
            "solution_text": "x = 42",
        }
        response = client.post("/api/v1/questions", json=payload)
        self.assertEqual(response.status_code, 403)

    def test_create_question_allows_admin(self) -> None:
        admin_user = {"uid": "admin_01", "email": "admin@mathsdd.lk", "role": "ADMIN"}
        app.dependency_overrides[get_current_user] = lambda: admin_user
        self.mock_user_repo.get_by_uid.return_value = admin_user
        self.mock_service.create_question.return_value = {
            "question": {
                "id": "q_new_01",
                "title": "2024 Model Question",
                "subject_id": "sub_pmat",
                "content_text": "Prove by mathematical induction...",
                "type": "SHORT",
                "difficulty": "MEDIUM",
                "schedule": "REGULAR",
                "source": "MODEL_PAPER",
                "allocated_marks": 25,
                "is_premium": False,
            },
            "marking_scheme": {
                "id": "ms_new_01",
                "question_id": "q_new_01",
                "title": "Official Marking Scheme",
                "content_text": "Base case n=1...",
                "content_type": "markdown",
                "total_marks": 25,
                "is_official": True,
                "is_premium_only": False,
            },
        }

        client = TestClient(app)
        payload = {
            "title": "2024 Model Question",
            "subject_id": "sub_pmat",
            "content_text": "Prove by mathematical induction...",
            "solution_text": "Base case n=1...",
        }
        response = client.post("/api/v1/questions", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["question"]["id"], "q_new_01")


class TestQuestionServiceCaching(unittest.IsolatedAsyncioTestCase):
    """Verifies Redis/Memory hybrid caching, anti-leak time locks, and signed URL hydration."""

    def setUp(self) -> None:
        from app.core.cache import questions_cache

        questions_cache.clear()
        self.mock_repo = AsyncMock()
        self.service = QuestionService(self.mock_repo)

    def tearDown(self) -> None:
        from app.core.cache import questions_cache

        questions_cache.clear()

    async def test_get_daily_pack_caching_and_url_hydration(self) -> None:
        raw_pack = {
            "day_number": 1,
            "scheduled_date": "2026-11-03",
            "total_questions": 2,
            "total_marks": 50,
            "questions": [
                {
                    "id": "q_pack_1",
                    "title": "Question 1 with Image",
                    "content_url": "questions/diagram.png",
                    "allocated_marks": 25,
                },
                {
                    "id": "q_pack_2",
                    "title": "Question 2 plain",
                    "content_url": None,
                    "allocated_marks": 25,
                },
            ],
        }
        self.mock_repo.get_daily_pack.return_value = raw_pack

        # First request (Cache MISS -> Database query)
        pack1 = await self.service.get_daily_pack(day_number=1)
        self.assertIsNotNone(pack1)
        self.assertEqual(self.mock_repo.get_daily_pack.call_count, 1)
        self.assertTrue(pack1["questions"][0]["content_url"].startswith("http"))

        # Raw cache preserves storage path
        from app.core.cache import questions_cache
        cached_raw = questions_cache.get("daily_pack:day_1")
        self.assertIsNotNone(cached_raw)
        self.assertEqual(cached_raw["questions"][0]["content_url"], "questions/diagram.png")

        # Second request (Cache HIT -> Served from cache with fresh hydrated URL)
        pack2 = await self.service.get_daily_pack(day_number=1)
        self.assertIsNotNone(pack2)
        self.assertEqual(self.mock_repo.get_daily_pack.call_count, 1)
        self.assertTrue(pack2["questions"][0]["content_url"].startswith("http"))

    async def test_get_daily_pack_anti_leak_blocks_future_date_for_student(self) -> None:
        # Future date in 2099
        student_user = {"uid": "usr_student", "role": "USER"}
        with self.assertRaises(PermissionDeniedError):
            await self.service.get_daily_pack(
                target_date="2099-12-31",
                current_user=student_user,
            )

    async def test_get_daily_pack_anti_leak_allows_admin_preview(self) -> None:
        admin_user = {"uid": "usr_admin", "role": "ADMIN"}
        self.mock_repo.get_daily_pack.return_value = {
            "day_number": 99,
            "scheduled_date": "2099-12-31",
            "total_questions": 1,
            "total_marks": 25,
            "questions": [],
        }
        # Admin should NOT be blocked from previewing future challenges
        pack = await self.service.get_daily_pack(
            target_date="2099-12-31",
            current_user=admin_user,
        )
        self.assertIsNotNone(pack)
        self.assertEqual(pack["day_number"], 99)

    async def test_list_daily_series_caching(self) -> None:
        from app.core.cache import questions_cache

        series_data = [
            {"day_number": 1, "title": "Day 01", "total_questions": 4, "total_marks": 150, "is_unlocked": True}
        ]
        self.mock_repo.list_daily_series.return_value = series_data

        res1 = await self.service.list_daily_series(limit=30, offset=0)
        self.assertEqual(len(res1), 1)
        self.assertEqual(self.mock_repo.list_daily_series.call_count, 1)

        # Second request should be served from cache
        res2 = await self.service.list_daily_series(limit=30, offset=0)
        self.assertEqual(len(res2), 1)
        self.assertEqual(self.mock_repo.list_daily_series.call_count, 1)


if __name__ == "__main__":
    unittest.main()
