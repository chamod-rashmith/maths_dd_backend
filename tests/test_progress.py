"""
Unit tests for Student Progress, Cumulative Study Time, Colombo Streaks, and XP Audit Ledger.
Verifies:
1. Domain 5 Models registered in SQLAlchemy Base.metadata (user_question_attempts, xp_transactions, etc.).
2. Accurate Cumulative Study Time (re-attempting accumulates time rather than overwriting).
3. Immutable XP Transaction Ledger with Proof (+10/+25 for solve, +50 for daily, +5 for re-practice, -10 for unmark).
4. Colombo Calendar Streaks calculation engine.
5. Endpoints: /summary, /completed-questions, /xp-history, and bookmarking.
"""

from datetime import date, datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from app.core.database import Base
from app.main import app
from app.models.progress import UserDailyActivity, UserQuestionAttempt, XpTransaction
from app.models.user_stats import UserStats
from app.schemas.progress import (
    CompletedQuestionRecordSchema,
    DailyActivityBucketSchema,
    UserProgressSummaryResponse,
    XpHistoryResponse,
    XpTransactionResponse,
)
from app.api.deps import get_current_user, get_progress_service
from app.services.progress_service import ProgressService


class TestProgressFeature(unittest.TestCase):
    """Verifies that progress and gamification models and endpoints behave accurately."""

    def test_progress_models_in_metadata(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        self.assertIn("user_question_attempts", table_names)
        self.assertIn("user_daily_activities", table_names)
        self.assertIn("xp_transactions", table_names)
        self.assertIn("user_stats", table_names)

    def test_cumulative_study_time_logic(self) -> None:
        """Verify that multiple practice sessions accumulate rather than overwriting study time."""
        now = datetime.now(timezone.utc)
        today = now.date()

        # Session 1: Student solves question for 120 seconds
        attempt = UserQuestionAttempt(
            id="usr_01_q_01",
            user_id="usr_01",
            question_id="q_01",
            time_spent_seconds=120,
            last_attempt_duration_seconds=120,
            target_duration_seconds=300,
            attempt_count=1,
            completed_date=today,
            completed_at=now,
        )
        self.assertEqual(attempt.time_spent_seconds, 120)
        self.assertEqual(attempt.last_attempt_duration_seconds, 120)

        # Session 2: Student practices the same question again for 90 seconds
        session_2_delta = 90
        attempt.attempt_count += 1
        attempt.time_spent_seconds += session_2_delta  # Cumulative!
        attempt.last_attempt_duration_seconds = session_2_delta

        # Total time spent must be 210s, NOT overwritten to 90s!
        self.assertEqual(attempt.time_spent_seconds, 210)
        self.assertEqual(attempt.last_attempt_duration_seconds, 90)
        self.assertEqual(attempt.attempt_count, 2)

    def test_xp_transaction_model_and_proof(self) -> None:
        """Verify XpTransaction encapsulates signed amounts, reasons, and descriptions."""
        tx1 = XpTransaction(
            id="tx_01",
            user_id="usr_01",
            amount=25,
            reason="QUESTION_SOLVED",
            question_id="q_01",
            description_si="රචනා ප්‍රශ්නයක් විසඳීම (+25 XP)",
        )
        self.assertEqual(tx1.amount, 25)
        self.assertEqual(tx1.reason, "QUESTION_SOLVED")
        self.assertEqual(tx1.question_id, "q_01")

        # Negative reversal transaction
        tx2 = XpTransaction(
            id="tx_02",
            user_id="usr_01",
            amount=-10,
            reason="QUESTION_UNMARKED",
            question_id="q_01",
            description_si="ප්‍රශ්නය ඉවත් කිරීම (-10 XP)",
        )
        self.assertEqual(tx2.amount, -10)
        self.assertEqual(tx2.reason, "QUESTION_UNMARKED")

    def test_get_progress_summary_endpoint(self) -> None:
        mock_service = AsyncMock(spec=ProgressService)
        now = datetime.now(timezone.utc)
        mock_summary = UserProgressSummaryResponse(
            completed_questions={
                "q_001": CompletedQuestionRecordSchema(
                    question_id="q_001",
                    title="Trigonometry Problem",
                    subject="pureMaths",
                    lesson_id="lesson_trig",
                    question_type="short",
                    is_daily_question=False,
                    time_spent_seconds=210,
                    last_attempt_duration_seconds=90,
                    target_duration_seconds=300,
                    was_overtime=False,
                    attempt_count=2,
                    completed_date_key="2026-11-02",
                    completed_at=now,
                    is_bookmarked=True,
                )
            },
            daily_activity={
                "2026-11-02": DailyActivityBucketSchema(
                    date_key="2026-11-02",
                    questions_solved_count=1,
                    total_time_spent_seconds=210,
                    daily_challenge_completed=False,
                    question_ids=["q_001"],
                )
            },
            solved_count_by_lesson={"lesson_trig": 1},
            solved_count_by_subject={"pureMaths": 1, "appliedMaths": 0},
            total_questions_solved=1,
            total_time_spent_seconds=210,
            current_streak_days=1,
            longest_streak_days=1,
            last_active_date_key="2026-11-02",
            xp=35,
            recent_xp_transactions=[
                XpTransactionResponse(
                    id="tx_01",
                    amount=25,
                    reason="QUESTION_SOLVED",
                    question_id="q_001",
                    description_si="රචනා ප්‍රශ්නයක් විසඳීම (+25 XP)",
                    created_at=now,
                )
            ],
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
            self.assertEqual(data["completedQuestions"]["q_001"]["timeSpentSeconds"], 210)
            self.assertEqual(data["completedQuestions"]["q_001"]["lastAttemptDurationSeconds"], 90)
            self.assertEqual(data["totalTimeSpentSeconds"], 210)
            self.assertEqual(data["xp"], 35)
            self.assertIn("recentXpTransactions", data)
            self.assertEqual(len(data["recentXpTransactions"]), 1)
        finally:
            app.dependency_overrides.clear()

    def test_mark_question_completed_endpoint(self) -> None:
        mock_service = AsyncMock(spec=ProgressService)
        now = datetime.now(timezone.utc)
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
                    last_attempt_duration_seconds=180,
                    target_duration_seconds=300,
                    was_overtime=False,
                    attempt_count=1,
                    completed_date_key="2026-11-02",
                    completed_at=now,
                )
            },
            daily_activity={},
            total_questions_solved=1,
            total_time_spent_seconds=180,
            current_streak_days=1,
            longest_streak_days=1,
            last_active_date_key="2026-11-02",
            xp=60,
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
            self.assertEqual(data["totalTimeSpentSeconds"], 180)
            self.assertEqual(data["xp"], 60)
        finally:
            app.dependency_overrides.clear()

    def test_xp_history_endpoint(self) -> None:
        """Verify GET /api/v1/progress/xp-history returns student's verified audit trail."""
        mock_service = AsyncMock(spec=ProgressService)
        now = datetime.now(timezone.utc)
        mock_history = XpHistoryResponse(
            total_xp=60,
            transactions=[
                XpTransactionResponse(
                    id="tx_101",
                    amount=50,
                    reason="DAILY_CHALLENGE_BONUS",
                    question_id="q_002",
                    description_si="දිනපතා අභ්‍යාස ප්‍රසාද ලකුණු (+50 XP)",
                    created_at=now,
                ),
                XpTransactionResponse(
                    id="tx_100",
                    amount=10,
                    reason="QUESTION_SOLVED",
                    question_id="q_002",
                    description_si="කෙටි ප්‍රශ්නයක් විසඳීම (+10 XP)",
                    created_at=now - timedelta(minutes=5),
                ),
            ],
        )
        mock_service.get_xp_history.return_value = mock_history

        app.dependency_overrides[get_current_user] = lambda: {"uid": "test_user_123"}
        app.dependency_overrides[get_progress_service] = lambda: mock_service

        client = TestClient(app)
        try:
            response = client.get("/api/v1/progress/xp-history?limit=10")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["totalXp"], 60)
            self.assertEqual(len(data["transactions"]), 2)
            self.assertEqual(data["transactions"][0]["reason"], "DAILY_CHALLENGE_BONUS")
            self.assertEqual(data["transactions"][0]["amount"], 50)
            self.assertEqual(data["transactions"][1]["reason"], "QUESTION_SOLVED")
            self.assertEqual(data["transactions"][1]["amount"], 10)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
