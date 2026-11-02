"""
PostgreSQL implementation of ProgressRepository using SQLAlchemy 2.0 ORM.
Decoupled telemetry: updates isolated UserStats table instead of locking Users.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.repositories.progress_repository import ProgressRepository
from app.models.progress import UserDailyActivity, UserQuestionAttempt
from app.models.question import Question
from app.models.user_stats import UserStats
from app.schemas.progress import (
    CompletedQuestionRecordSchema,
    DailyActivityBucketSchema,
    MarkQuestionCompletedRequest,
    UserProgressSummaryResponse,
)

_COLOMBO_TZ = ZoneInfo("Asia/Colombo")


def _get_colombo_today() -> date:
    return datetime.now(_COLOMBO_TZ).date()


def _normalize_subject(subject_id: Optional[str]) -> str:
    if not subject_id:
        return "pureMaths"
    s = subject_id.lower()
    if "applied" in s or "amat" in s:
        return "appliedMaths"
    return "pureMaths"


def _normalize_question_type(q_type: Optional[str]) -> str:
    if not q_type:
        return "short"
    return "essay" if q_type.upper() == "ESSAY" else "short"


class PostgresProgressRepository(ProgressRepository):
    """Postgres implementation handling student attempts, streaks, and heatmap aggregation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_progress_summary(
        self, user_id: str
    ) -> UserProgressSummaryResponse:
        # 1. Fetch all question attempts with joined question
        stmt = (
            select(UserQuestionAttempt)
            .options(selectinload(UserQuestionAttempt.question))
            .where(UserQuestionAttempt.user_id == user_id)
            .order_by(UserQuestionAttempt.completed_at.desc())
        )
        result = await self.session.execute(stmt)
        attempts = result.scalars().all()

        completed_questions: Dict[str, CompletedQuestionRecordSchema] = {}
        solved_count_by_lesson: Dict[str, int] = {}
        solved_count_by_subject: Dict[str, int] = {
            "pureMaths": 0,
            "appliedMaths": 0,
        }
        total_time_spent = 0
        date_to_question_ids: Dict[str, List[str]] = {}

        for a in attempts:
            q: Optional[Question] = a.question
            title = q.title if q else f"Question {a.question_id}"
            subject_str = _normalize_subject(q.subject_id if q else None)
            lesson_id = q.lesson_id if q else None
            q_type = _normalize_question_type(q.type if q else None)
            date_key = a.completed_date.isoformat() if a.completed_date else ""

            if a.attempt_count > 0:
                completed_questions[a.question_id] = CompletedQuestionRecordSchema(
                    question_id=a.question_id,
                    title=title,
                    subject=subject_str,
                    lesson_id=lesson_id,
                    question_type=q_type,
                    is_daily_question=a.is_daily_question,
                    time_spent_seconds=a.time_spent_seconds,
                    target_duration_seconds=a.target_duration_seconds,
                    was_overtime=a.was_overtime,
                    attempt_count=max(a.attempt_count, 1),
                    completed_date_key=date_key,
                    completed_at=a.completed_at,
                    is_bookmarked=a.is_bookmarked,
                    confidence=a.confidence,
                    student_notes=a.student_notes,
                )
                total_time_spent += a.time_spent_seconds
                solved_count_by_subject[subject_str] = (
                    solved_count_by_subject.get(subject_str, 0) + 1
                )
                if lesson_id:
                    solved_count_by_lesson[lesson_id] = (
                        solved_count_by_lesson.get(lesson_id, 0) + 1
                    )
                if date_key:
                    date_to_question_ids.setdefault(date_key, []).append(a.question_id)

        # 2. Fetch daily activities
        stmt_act = (
            select(UserDailyActivity)
            .where(UserDailyActivity.user_id == user_id)
            .order_by(UserDailyActivity.date_key.asc())
        )
        res_act = await self.session.execute(stmt_act)
        activities = res_act.scalars().all()

        daily_activity: Dict[str, DailyActivityBucketSchema] = {}
        for act in activities:
            q_ids = date_to_question_ids.get(act.date_key, [])
            daily_activity[act.date_key] = DailyActivityBucketSchema(
                date_key=act.date_key,
                questions_solved_count=act.questions_solved_count,
                total_time_spent_seconds=act.total_time_spent_seconds,
                daily_challenge_completed=act.daily_challenge_completed,
                question_ids=q_ids,
            )

        # If any dates from attempts aren't in daily_activity, ensure they appear
        for dk, qids in date_to_question_ids.items():
            if dk not in daily_activity:
                daily_activity[dk] = DailyActivityBucketSchema(
                    date_key=dk,
                    questions_solved_count=len(qids),
                    total_time_spent_seconds=0,
                    daily_challenge_completed=False,
                    question_ids=qids,
                )

        # 3. Calculate Streaks
        current_streak, longest_streak, last_active_key = self._compute_streaks(
            daily_activity
        )

        # 4. Fetch User XP
        stmt_xp = select(UserStats.xp).where(UserStats.user_id == user_id)
        res_xp = await self.session.execute(stmt_xp)
        user_xp = res_xp.scalar_one_or_none() or 0

        return UserProgressSummaryResponse(
            completed_questions=completed_questions,
            daily_activity=daily_activity,
            solved_count_by_lesson=solved_count_by_lesson,
            solved_count_by_subject=solved_count_by_subject,
            total_questions_solved=len(completed_questions),
            total_time_spent_seconds=total_time_spent,
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
            last_active_date_key=last_active_key,
            xp=user_xp,
        )

    async def mark_question_completed(
        self, user_id: str, request: MarkQuestionCompletedRequest
    ) -> UserProgressSummaryResponse:
        today = _get_colombo_today()
        today_key = today.isoformat()
        now_utc = datetime.now(timezone.utc)

        # Find existing attempt
        stmt = select(UserQuestionAttempt).where(
            UserQuestionAttempt.user_id == user_id,
            UserQuestionAttempt.question_id == request.question_id,
        )
        result = await self.session.execute(stmt)
        attempt = result.scalar_one_or_none()
        is_new_solve = attempt is None

        # Determine question type to calculate earned XP
        q_stmt = select(Question.type).where(Question.id == request.question_id)
        q_res = await self.session.execute(q_stmt)
        q_row = q_res.first()
        q_type = str(q_row[0]).upper() if (q_row and q_row[0]) else "SHORT"

        base_xp = 25 if q_type == "ESSAY" else 10
        earned_xp = base_xp if is_new_solve else 5
        if request.is_daily_question and is_new_solve:
            earned_xp += 50

        time_delta = request.time_spent_seconds

        if attempt:
            attempt.attempt_count += 1
            if request.time_spent_seconds > 0:
                attempt.time_spent_seconds = request.time_spent_seconds
            attempt.target_duration_seconds = request.target_duration_seconds
            attempt.was_overtime = request.was_overtime
            attempt.is_daily_question = request.is_daily_question
            attempt.completed_date = today
            attempt.completed_at = now_utc
            if request.confidence is not None:
                attempt.confidence = request.confidence
            if request.student_notes is not None:
                attempt.student_notes = request.student_notes
            if request.is_bookmarked is not None:
                attempt.is_bookmarked = request.is_bookmarked
        else:
            attempt = UserQuestionAttempt(
                id=f"{user_id}_{request.question_id}",
                user_id=user_id,
                question_id=request.question_id,
                time_spent_seconds=request.time_spent_seconds,
                target_duration_seconds=request.target_duration_seconds,
                was_overtime=request.was_overtime,
                attempt_count=1,
                is_daily_question=request.is_daily_question,
                completed_date=today,
                completed_at=now_utc,
                is_bookmarked=request.is_bookmarked if request.is_bookmarked is not None else False,
                confidence=request.confidence,
                student_notes=request.student_notes,
            )
            self.session.add(attempt)

        # Update or create DailyActivityBucket for today
        stmt_act = select(UserDailyActivity).where(
            UserDailyActivity.user_id == user_id,
            UserDailyActivity.date_key == today_key,
        )
        res_act = await self.session.execute(stmt_act)
        activity = res_act.scalar_one_or_none()

        if activity:
            activity.questions_solved_count += 1
            activity.total_time_spent_seconds += max(time_delta, 0)
            if request.is_daily_question:
                activity.daily_challenge_completed = True
        else:
            activity = UserDailyActivity(
                id=f"{user_id}_{today_key}",
                user_id=user_id,
                date_key=today_key,
                questions_solved_count=1,
                total_time_spent_seconds=max(time_delta, 0),
                daily_challenge_completed=request.is_daily_question,
            )
            self.session.add(activity)

        await self.session.commit()

        # Update isolated UserStats (zero locks on users table)
        summary = await self.get_user_progress_summary(user_id)
        stmt_stats = select(UserStats).where(UserStats.user_id == user_id)
        stats_res = await self.session.execute(stmt_stats)
        stats = stats_res.scalar_one_or_none()

        if stats:
            stats.total_solved_count = summary.total_questions_solved
            stats.total_study_time_seconds = summary.total_time_spent_seconds
            stats.current_streak_days = summary.current_streak_days
            stats.longest_streak_days = summary.longest_streak_days
            stats.last_active_date = today
            stats.xp = (stats.xp or 0) + earned_xp
        else:
            stats = UserStats(
                user_id=user_id,
                total_solved_count=summary.total_questions_solved,
                total_study_time_seconds=summary.total_time_spent_seconds,
                current_streak_days=summary.current_streak_days,
                longest_streak_days=summary.longest_streak_days,
                last_active_date=today,
                xp=earned_xp,
            )
            self.session.add(stats)

        await self.session.commit()
        summary.xp = stats.xp
        return summary

    async def unmark_question_completed(
        self, user_id: str, question_id: str
    ) -> UserProgressSummaryResponse:
        stmt = select(UserQuestionAttempt).where(
            UserQuestionAttempt.user_id == user_id,
            UserQuestionAttempt.question_id == question_id,
        )
        result = await self.session.execute(stmt)
        attempt = result.scalar_one_or_none()

        if attempt:
            completed_date_key = (
                attempt.completed_date.isoformat() if attempt.completed_date else None
            )
            time_spent = attempt.time_spent_seconds
            await self.session.delete(attempt)

            # Adjust daily activity bucket
            if completed_date_key:
                stmt_act = select(UserDailyActivity).where(
                    UserDailyActivity.user_id == user_id,
                    UserDailyActivity.date_key == completed_date_key,
                )
                res_act = await self.session.execute(stmt_act)
                act = res_act.scalar_one_or_none()
                if act:
                    act.questions_solved_count = max(0, act.questions_solved_count - 1)
                    act.total_time_spent_seconds = max(
                        0, act.total_time_spent_seconds - time_spent
                    )
            await self.session.commit()

        # Update isolated UserStats
        summary = await self.get_user_progress_summary(user_id)
        stmt_stats = select(UserStats).where(UserStats.user_id == user_id)
        stats_res = await self.session.execute(stmt_stats)
        stats = stats_res.scalar_one_or_none()

        if stats:
            stats.total_solved_count = summary.total_questions_solved
            stats.total_study_time_seconds = summary.total_time_spent_seconds
            stats.current_streak_days = summary.current_streak_days
            stats.longest_streak_days = summary.longest_streak_days
            stats.xp = max(0, (stats.xp or 0) - 10)
            await self.session.commit()
            summary.xp = stats.xp

        return summary

    async def toggle_bookmark(
        self, user_id: str, question_id: str, is_bookmarked: bool
    ) -> bool:
        stmt = select(UserQuestionAttempt).where(
            UserQuestionAttempt.user_id == user_id,
            UserQuestionAttempt.question_id == question_id,
        )
        result = await self.session.execute(stmt)
        attempt = result.scalar_one_or_none()

        today = _get_colombo_today()
        now_utc = datetime.now(timezone.utc)

        if attempt:
            attempt.is_bookmarked = is_bookmarked
        else:
            attempt = UserQuestionAttempt(
                id=f"{user_id}_{question_id}",
                user_id=user_id,
                question_id=question_id,
                time_spent_seconds=0,
                target_duration_seconds=0,
                was_overtime=False,
                attempt_count=0,
                is_daily_question=False,
                completed_date=today,
                completed_at=now_utc,
                is_bookmarked=is_bookmarked,
            )
            self.session.add(attempt)

        await self.session.commit()
        return is_bookmarked

    def _compute_streaks(
        self, daily_activity: Dict[str, DailyActivityBucketSchema]
    ) -> tuple[int, int, Optional[str]]:
        active_dates = [
            date.fromisoformat(k)
            for k, b in daily_activity.items()
            if b.questions_solved_count > 0 or b.total_time_spent_seconds > 0
        ]
        active_dates.sort()

        if not active_dates:
            return 0, 0, None

        # Longest streak
        longest = 1
        running = 1
        for i in range(1, len(active_dates)):
            diff = (active_dates[i] - active_dates[i - 1]).days
            if diff == 1:
                running += 1
                if running > longest:
                    longest = running
            elif diff > 1:
                running = 1

        # Current streak
        today = _get_colombo_today()
        yesterday = today - timedelta(days=1)
        active_set = set(active_dates)

        current = 0
        cursor = None
        if today in active_set:
            cursor = today
        elif yesterday in active_set:
            cursor = yesterday

        while cursor and cursor in active_set:
            current += 1
            cursor = cursor - timedelta(days=1)

        last_active_key = active_dates[-1].isoformat()
        return current, longest, last_active_key
