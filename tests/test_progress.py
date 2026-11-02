"""
Unit tests for Student Progress, Question Attempts, and Activity Heatmap endpoints and models.
"""

from datetime import date, datetime, timezone
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from app.core.database import Base
from app.main import app
from app.models.progress import UserDailyActivity, UserQuestionAttempt
from app.schemas.progress import (
    CompletedQuestionRecordSchema,
    DailyActivityBucketSchema,
    UserProgressSummaryResponse,
)
from app.api.deps import get_current_user, get_progress_service
from app.services.progress_service import ProgressService


class TestProgressFeature(unittest.TestCase):
    """Verifies that progress models register with SQLAlchemy metadata and endpoints behave as expected."""

    def test_progress_models_in_metadata(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        self.assertIn("user_question_attempts", table_names)
        self.assertIn("user_daily_activities", table_names)

    def test_get_progress_summary_endpoint(self) -> None:
        mock_service = AsyncMock(spec=ProgressService)
        mock_summary = UserProgressSummaryResponse(
            completed_questions={
                "q_001": CompletedQuestionRecordSchema(
                    question_id="q_001",
                    title="Trigonometry Problem",
                    subject="pureMaths",
                    lesson_id="lesson_trig",
                    question_type="short",
                    is_daily_question=False,
                    time_spent_seconds=120,
                    target_duration_seconds=300,
                    was_overtime=False,
                    attempt_count=1,
                    completed_date_key="2026-11-02",
                    completed_at=datetime.now(timezone.utc),
                    is_bookmarked=True,
                )
            },
            daily_activity={
                "2026-11-02": DailyActivityBucketSchema(
                    date_key="2026-11-02",
                    questions_solved_count=1,
                    total_time_spent_seconds=120,
                    daily_challenge_completed=False,
                    question_ids=["q_001"],
                )
            },
            solved_count_by_lesson={"lesson_trig": 1},
            solved_count_by_subject={"pureMaths": 1, "appliedMaths": 0},
            total_questions_solved=1,
            total_time_spent_seconds=120,
            current_streak_days=1,
            longest_streak_days=1,
            last_active_date_key="2026-11-02",
        )
        mock_service.get_progress_summary.return_value = mock_summary

        app.dependency_overrides[get_current_user] = lambda: {"uid": "test_user_123"}
        app.dependency_overrides[get_progress_service] = lambda: mock_service

        client = TestClient(app)
        try:
            response = client.get("/api/v1/progress/summary")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("completedQuestions", data)
            self.assertIn("q_001", data["completedQuestions"])
            self.assertEqual(data["completedQuestions"]["q_001"]["title"], "Trigonometry Problem")
            self.assertEqual(data["totalQuestionsSolved"], 1)
            self.assertEqual(data["currentStreakDays"], 1)
        finally:
            app.dependency_overrides.clear()

    def test_mark_question_completed_endpoint(self) -> None:
        mock_service = AsyncMock(spec=ProgressService)
        mock_summary = UserProgressSummaryResponse(
            completed_questions={
                "q_002": CompletedQuestionRecordSchema(
                    question_id="q_002",
                    title="Integration Problem",
                    subject="pureMaths",
                    lesson_id="lesson_int",
                    question_type="short",
                    is_daily_question=True,
                    time_spent_seconds=180,
                    target_duration_seconds=300,
                    was_overtime=False,
                    attempt_count=1,
                    completed_date_key="2026-11-02",
                    completed_at=datetime.now(timezone.utc),
                )
            },
            daily_activity={},
            total_questions_solved=1,
            total_time_spent_seconds=180,
            current_streak_days=1,
            longest_streak_days=1,
            last_active_date_key="2026-11-02",
        )
        mock_service.mark_question_completed.return_value = mock_summary

        app.dependency_overrides[get_current_user] = lambda: {"uid": "test_user_123"}
        app.dependency_overrides[get_progress_service] = lambda: mock_service

        client = TestClient(app)
        try:
            payload = {
                "questionId": "q_002",
                "timeSpentSeconds": 180,
                "targetDurationSeconds": 300,
                "wasOvertime": False,
                "isDailyQuestion": True,
            }
            response = client.post("/api/v1/progress/completed-questions", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["totalQuestionsSolved"], 1)
            self.assertIn("q_002", data["completedQuestions"])
        finally:
            app.dependency_overrides.clear()
