"""
Unit tests for Question Bank, Daily Challenge, Solution Paywall, and Admin Question CRUD.
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
    """Verifies question catalog, paywall protection on marking schemes, and admin RBAC."""

    def setUp(self) -> None:
        self.mock_service = AsyncMock(spec=QuestionService)
        app.dependency_overrides[get_question_service] = lambda: self.mock_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_list_questions(self) -> None:
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

    def test_get_daily_question(self) -> None:
        self.mock_service.get_daily_question.return_value = {
            "id": "q_daily_today",
            "title": "Daily Challenge - Complex Numbers",
            "subject_id": "sub_pmat",
            "content_text": "Solve $(z - 1)^4 = 1$",
            "type": "SHORT",
            "difficulty": "HARD",
            "schedule": "DAILY",
            "source": "MODEL_PAPER",
            "allocated_marks": 25,
            "is_premium": False,
            "scheduled_date": "2026-11-02",
        }
        client = TestClient(app)
        response = client.get("/api/v1/questions/daily")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "q_daily_today")
        self.assertEqual(response.json()["schedule"], "DAILY")

    def test_solution_free_marking_scheme_accessible_to_everyone(self) -> None:
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
        self.mock_service.get_marking_scheme.side_effect = AuthenticationError(
            "Authentication is required to access this premium solution."
        )
        client = TestClient(app)
        response = client.get("/api/v1/questions/q_prem_01/solution")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication is required", response.json()["detail"])

    def test_solution_premium_marking_scheme_blocks_free_user(self) -> None:
        self.mock_service.get_marking_scheme.side_effect = PermissionDeniedError(
            "A premium subscription is required to view this marking scheme."
        )
        standard_user = {"uid": "usr_free", "email": "free@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_optional_current_user] = lambda: standard_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = {
            "uid": "usr_free",
            "role": "USER",
            "is_premium": False,
        }
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        response = client.get(
            "/api/v1/questions/q_prem_01/solution",
            headers={"Authorization": "Bearer fake_token"},
        )
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
        sub_user = {"uid": "usr_pro", "email": "pro@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_optional_current_user] = lambda: sub_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = {
            "uid": "usr_pro",
            "role": "USER",
            "is_premium": True,
        }
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        response = client.get(
            "/api/v1/questions/q_prem_01/solution",
            headers={"Authorization": "Bearer fake_token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_premium_only"])

    def test_create_question_blocks_standard_user(self) -> None:
        standard_user = {"uid": "usr_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = standard_user
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

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
    """Verifies Date-Based Redis/Memory hybrid caching, on-the-fly signing, and invalidation."""

    def setUp(self) -> None:
        from app.core.cache import questions_cache

        questions_cache.clear()
        self.mock_repo = AsyncMock()
        self.service = QuestionService(self.mock_repo)

    def tearDown(self) -> None:
        from app.core.cache import questions_cache

        questions_cache.clear()

    async def test_get_daily_question_caches_and_avoids_duplicate_db_query(self) -> None:
        raw_db_row = {
            "id": "q_daily_cached",
            "title": "Cached Daily Challenge",
            "subject_id": "sub_pmat",
            "content_text": "Solve $x^2 = 4$",
            "content_url": None,
            "type": "SHORT",
            "difficulty": "EASY",
            "schedule": "DAILY",
            "source": "PAST_PAPER",
            "allocated_marks": 10,
            "is_premium": False,
            "scheduled_date": "2026-11-03",
        }
        self.mock_repo.get_daily_question.return_value = raw_db_row

        # First request (Cache MISS -> Database query)
        q1 = await self.service.get_daily_question(target_date="2026-11-03")
        self.assertIsNotNone(q1)
        self.assertEqual(q1["id"], "q_daily_cached")
        self.assertEqual(self.mock_repo.get_daily_question.call_count, 1)

        # Second request (Cache HIT -> Served directly from cache, NO database query)
        q2 = await self.service.get_daily_question(target_date="2026-11-03")
        self.assertIsNotNone(q2)
        self.assertEqual(q2["id"], "q_daily_cached")
        self.assertEqual(self.mock_repo.get_daily_question.call_count, 1)

    async def test_cached_question_hydrates_signed_url_without_mutating_raw_cache(self) -> None:
        raw_db_row = {
            "id": "q_image_daily",
            "title": "Geometry Challenge",
            "subject_id": "sub_pmat",
            "content_text": "Find angle ABC",
            "content_url": "questions/diagram_01.png",
            "type": "STRUCTURED",
            "difficulty": "MEDIUM",
            "schedule": "DAILY",
            "source": "MODEL_PAPER",
            "allocated_marks": 25,
            "is_premium": False,
            "scheduled_date": "2026-11-03",
        }
        self.mock_repo.get_daily_question.return_value = raw_db_row

        result = await self.service.get_daily_question(target_date="2026-11-03")
        self.assertIsNotNone(result)
        # Hydrated result has signed URL
        self.assertTrue(result["content_url"].startswith("http"))

        # Cached raw item in questions_cache preserves the raw storage path
        from app.core.cache import questions_cache
        cached_entry = questions_cache.get("daily_question:2026-11-03")
        self.assertIsNotNone(cached_entry)
        self.assertEqual(cached_entry["content_url"], "questions/diagram_01.png")

    async def test_create_and_delete_question_invalidates_daily_cache(self) -> None:
        from app.core.cache import questions_cache
        from app.schemas.question import QuestionCreate

        # Pre-seed cache
        questions_cache.set("daily_question:2026-11-03", {"id": "stale_daily"})
        self.assertIsNotNone(questions_cache.get("daily_question:2026-11-03"))

        # Create question -> should invalidate
        self.mock_repo.create_question_with_solution.return_value = {"id": "new_q"}
        payload = QuestionCreate(
            title="New Question",
            subject_id="sub_pmat",
            content_text="Solve",
            solution_text="Solution",
        )
        await self.service.create_question(payload)
        self.assertIsNone(questions_cache.get("daily_question:2026-11-03"))

        # Pre-seed again
        questions_cache.set("daily_question:2026-11-03", {"id": "stale_daily_2"})
        self.assertIsNotNone(questions_cache.get("daily_question:2026-11-03"))

        # Delete question -> should invalidate
        self.mock_repo.delete_question.return_value = {"deleted": True}
        await self.service.delete_question("some_id")
        self.assertIsNone(questions_cache.get("daily_question:2026-11-03"))


if __name__ == "__main__":
    unittest.main()
