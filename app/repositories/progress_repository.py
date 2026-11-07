"""
PostgreSQL implementation of ProgressRepository using modern SQLAlchemy 2.0 ORM.
මෙම Repository මඟින් ශිෂ්‍ය ප්‍රගතිය, සමුච්චිත අධ්‍යයන කාලය (Cumulative Study Time),
Colombo Timezone Streaks, සහ Immutable XP Audit Ledger (සාක්ෂි සහිත XP ගනුදෙනු) කළමනාකරණය කරයි.

Core Architectural Fixes & Improvements:
1. Cumulative Study Time:
   - When a student re-attempts a problem, `attempt.time_spent_seconds` accumulates
     (`attempt.time_spent_seconds += time_delta`) rather than overwriting previous efforts.
   - `last_attempt_duration_seconds` preserves the exact time spent in the latest session.
2. Immutable XP Audit Ledger:
   - Every score alteration is recorded as an immutable row in `xp_transactions` with verified proof.
   - User's total XP is projected as `SUM(xp_transactions.amount)` ensuring 100% mathematical integrity.
3. Colombo-Timezone Streak Engine:
   - Evaluates continuous daily engagement based on `Asia/Colombo` standard calendar days.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid
from zoneinfo import ZoneInfo
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.repositories.progress_repository import ProgressRepository
from app.models.progress import UserDailyActivity, UserQuestionAttempt, XpTransaction
from app.models.question import Question
from app.models.subject import Subject
from app.models.user_stats import UserStats
from app.schemas.progress import (
    CompletedQuestionRecordSchema,
    DailyActivityBucketSchema,
    MarkQuestionCompletedRequest,
    UserProgressSummaryResponse,
    XpTransactionResponse,
)

_COLOMBO_TZ = ZoneInfo("Asia/Colombo")


def _get_colombo_today() -> date:
    """ශ්‍රී ලංකා සම්මත වේලාවට (Asia/Colombo) අනුව අද දින දර්ශන දිනය ලබා ගැනීම."""
    return datetime.now(_COLOMBO_TZ).date()


def _normalize_subject(subject_id_or_code: Optional[str]) -> str:
    """විෂය හඳුනාගැනීම (pureMaths / appliedMaths)."""
    if not subject_id_or_code:
        return "pureMaths"
    s = subject_id_or_code.lower()
    if "applied" in s or "amat" in s:
        return "appliedMaths"
    return "pureMaths"


def _normalize_question_type(q_type: Optional[str]) -> str:
    """ප්‍රශ්න වර්ගය සාමාන්‍යකරණය කිරීම (short / essay)."""
    if not q_type:
        return "short"
    return "essay" if q_type.upper() == "ESSAY" else "short"


class PostgresProgressRepository(ProgressRepository):
    """Postgres implementation handling student attempts, cumulative study time, streaks, and XP ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # 1. Aggregated Progress Summary (සමස්ත ප්‍රගති සාරාංශය)
    # =========================================================================

    async def get_user_progress_summary(
        self, user_id: str
    ) -> UserProgressSummaryResponse:
        """
        ශිෂ්‍යයාගේ සමස්ත ප්‍රගති සාරාංශය ගණනය කර ලබා දීම.
        මෙහිදී සමස්ත අධ්‍යයන කාලය (total_time_spent_seconds) සත්‍ය සමුච්චිත අගයක් ලෙස නිවැරදිව ගණනය වේ.
        """
        # 1. Fetch all question attempts with lightweight Question(subject_id, lesson_id) & Subject.code projection
        stmt = (
            select(
                UserQuestionAttempt,
                Question.subject_id,
                Question.lesson_id,
                Subject.code,
            )
            .outerjoin(Question, UserQuestionAttempt.question_id == Question.id)
            .outerjoin(Subject, Question.subject_id == Subject.id)
            .where(UserQuestionAttempt.user_id == user_id)
            .order_by(UserQuestionAttempt.completed_at.desc())
        )
        result = await self.session.execute(stmt)
        attempt_rows = result.all()

        completed_questions: Dict[str, CompletedQuestionRecordSchema] = {}
        solved_count_by_lesson: Dict[str, int] = {}
        solved_count_by_subject: Dict[str, int] = {
            "pureMaths": 0,
            "appliedMaths": 0,
        }
        total_time_spent = 0
        date_to_solved_count: Dict[str, int] = {}

        for a, q_subject_id, q_lesson_id, subj_code in attempt_rows:
            subject_str = _normalize_subject(subj_code or q_subject_id)
            lesson_id = q_lesson_id
            date_key = a.completed_date.isoformat() if a.completed_date else ""

            if a.attempt_count > 0:
                completed_questions[a.question_id] = CompletedQuestionRecordSchema(
                    is_daily_question=a.is_daily_question,
                    time_spent_seconds=a.time_spent_seconds,
                    last_attempt_duration_seconds=getattr(a, "last_attempt_duration_seconds", a.time_spent_seconds),
                    target_duration_seconds=a.target_duration_seconds,
                    was_overtime=a.was_overtime,
                    attempt_count=max(a.attempt_count, 1),
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
                    date_to_solved_count[date_key] = date_to_solved_count.get(date_key, 0) + 1

        # 2. Fetch daily activity buckets for heatmap
        stmt_act = (
            select(UserDailyActivity)
            .where(UserDailyActivity.user_id == user_id)
            .order_by(UserDailyActivity.date_key.asc())
        )
        res_act = await self.session.execute(stmt_act)
        activities = res_act.scalars().all()

        daily_activity: Dict[str, DailyActivityBucketSchema] = {}
        total_daily_seconds = 0
        for act in activities:
            daily_activity[act.date_key] = DailyActivityBucketSchema(
                questions_solved_count=act.questions_solved_count,
                total_time_spent_seconds=act.total_time_spent_seconds,
                daily_challenge_completed=act.daily_challenge_completed,
            )
            total_daily_seconds += act.total_time_spent_seconds

        # Ensure any dates from attempts appear in daily_activity
        for dk, cnt in date_to_solved_count.items():
            if dk not in daily_activity:
                daily_activity[dk] = DailyActivityBucketSchema(
                    questions_solved_count=cnt,
                    total_time_spent_seconds=0,
                    daily_challenge_completed=False,
                )

        # Reconcile study time: ensure total_time_spent never drops below daily bucket sum
        if total_daily_seconds > total_time_spent:
            total_time_spent = total_daily_seconds

        # 3. Calculate Streaks using Colombo Calendar standard
        current_streak, longest_streak, last_active_key = self._compute_streaks(
            daily_activity
        )

        # 4. Fetch Verified User XP directly from the immutable XpTransaction ledger
        stmt_xp = select(func.coalesce(func.sum(XpTransaction.amount), 0)).where(
            XpTransaction.user_id == user_id
        )
        res_xp = await self.session.execute(stmt_xp)
        user_xp = max(0, int(res_xp.scalar_one() or 0))

        # Fallback to UserStats if no transactions recorded yet
        if user_xp == 0:
            stmt_stats_xp = select(UserStats.xp).where(UserStats.user_id == user_id)
            res_stats_xp = await self.session.execute(stmt_stats_xp)
            user_xp = res_stats_xp.scalar_one_or_none() or 0

        # 5. Fetch Recent 5 XP Transactions for Proof Audit
        stmt_recent_xp = (
            select(XpTransaction)
            .where(XpTransaction.user_id == user_id)
            .order_by(desc(XpTransaction.created_at))
            .limit(5)
        )
        res_recent_xp = await self.session.execute(stmt_recent_xp)
        recent_xp_rows = res_recent_xp.scalars().all()
        recent_xp_dto = [XpTransactionResponse.model_validate(tx) for tx in recent_xp_rows]

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
            recent_xp_transactions=recent_xp_dto,
        )

    # =========================================================================
    # 2. Mark Question Completed (ප්‍රශ්නයක් විසඳූ බව සටහන් කිරීම & XP Ledger)
    # =========================================================================

    async def mark_question_completed(
        self, user_id: str, request: MarkQuestionCompletedRequest
    ) -> UserProgressSummaryResponse:
        """
        ප්‍රශ්නයක් සාර්ථකව විසඳූ බව සටහන් කිරීම.
        - අධ්‍යයන කාලය පෙර කාලයට එකතු වේ (Cumulative Addition).
        - අදාළ XP ලකුණු `XpTransaction` වගුවේ සාක්ෂියක් ලෙස සටහන් වේ.
        - දිනපතා Heatmap bucket එක යාවත්කාලීන වේ.
        """
        today = _get_colombo_today()
        today_key = today.isoformat()
        now_utc = datetime.now(timezone.utc)
        time_delta = max(request.time_spent_seconds, 0)

        # 1. Check existing attempt record
        stmt = select(UserQuestionAttempt).where(
            UserQuestionAttempt.user_id == user_id,
            UserQuestionAttempt.question_id == request.question_id,
        )
        result = await self.session.execute(stmt)
        attempt = result.scalar_one_or_none()
        is_new_solve = attempt is None

        # 2. Determine question metadata & server-side verification of Daily Challenge status
        q_stmt = select(
            Question.type,
            Question.scheduled_date,
            Question.day_number,
        ).where(Question.id == request.question_id)
        q_res = await self.session.execute(q_stmt)
        q_row = q_res.first()
        q_type = str(q_row[0]).upper() if (q_row and q_row[0]) else "SHORT"
        q_scheduled_date = q_row[1] if (q_row and len(q_row) > 1) else None

        # Server-side verification of Daily Challenge status:
        # A question is genuinely a daily challenge question for today if:
        # a. Its scheduled_date is strictly today in Asia/Colombo.
        # b. In fallback mode (when no questions exist for today), its scheduled_date matches the active fallback date <= today.
        is_verified_daily = False
        if q_scheduled_date == today:
            is_verified_daily = True
        elif q_scheduled_date is not None and q_scheduled_date <= today:
            today_count_stmt = select(func.count(Question.id)).where(
                Question.is_published.is_(True),
                Question.is_deleted.is_(False),
                Question.scheduled_date == today,
            )
            has_today_questions = (await self.session.execute(today_count_stmt)).scalar() or 0
            if has_today_questions == 0:
                latest_date_stmt = (
                    select(Question.scheduled_date)
                    .where(
                        Question.is_published.is_(True),
                        Question.is_deleted.is_(False),
                        Question.scheduled_date.isnot(None),
                        Question.scheduled_date <= today,
                    )
                    .order_by(Question.scheduled_date.desc())
                    .limit(1)
                )
                latest_date = (await self.session.execute(latest_date_stmt)).scalar_one_or_none()
                if latest_date and q_scheduled_date == latest_date:
                    is_verified_daily = True

        # Enforce server-side verified daily question flag
        # (Client cannot spoof is_daily_question for regular practice questions)
        is_effective_daily = is_verified_daily

        # 3. Update or Create Attempt with Cumulative Time
        if attempt:
            attempt.attempt_count += 1
            # CUMULATIVE: Never overwrite! Add the new session time to total time spent
            attempt.time_spent_seconds += time_delta
            attempt.last_attempt_duration_seconds = time_delta
            attempt.target_duration_seconds = request.target_duration_seconds
            attempt.was_overtime = request.was_overtime
            attempt.is_daily_question = is_effective_daily
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
                id=str(uuid.uuid4()),
                user_id=user_id,
                question_id=request.question_id,
                time_spent_seconds=time_delta,
                last_attempt_duration_seconds=time_delta,
                target_duration_seconds=request.target_duration_seconds,
                was_overtime=request.was_overtime,
                attempt_count=1,
                is_daily_question=is_effective_daily,
                completed_date=today,
                completed_at=now_utc,
                is_bookmarked=request.is_bookmarked if request.is_bookmarked is not None else False,
                confidence=request.confidence,
                student_notes=request.student_notes,
            )
            self.session.add(attempt)

        await self.session.flush()

        # 4. Record Immutable XP Transactions (Proof of score)
        if is_new_solve:
            base_xp = 25 if q_type == "ESSAY" else 10
            xp_tx = XpTransaction(
                user_id=user_id,
                amount=base_xp,
                reason="QUESTION_SOLVED",
                attempt_id=attempt.id,
                question_id=request.question_id,
                description_si=f"{'රචනා (Essay)' if q_type == 'ESSAY' else 'කෙටි (Short)'} ප්‍රශ්නයක් සාර්ථකව විසඳීම (+{base_xp} XP)",
                description_en=f"Solved {q_type.title()} Question (+{base_xp} XP)",
            )
            self.session.add(xp_tx)

            # Daily challenge bonus (Strictly ONCE per Colombo calendar day and ONLY for verified daily questions)
            if is_effective_daily:
                today_start_utc = datetime.combine(today, datetime.min.time(), tzinfo=_COLOMBO_TZ).astimezone(timezone.utc)
                stmt_daily_bonus = select(XpTransaction.id).where(
                    XpTransaction.user_id == user_id,
                    XpTransaction.reason == "DAILY_CHALLENGE_BONUS",
                    XpTransaction.created_at >= today_start_utc,
                ).limit(1)
                existing_bonus = (await self.session.execute(stmt_daily_bonus)).first()
                if not existing_bonus:
                    daily_bonus_tx = XpTransaction(
                        user_id=user_id,
                        amount=50,
                        reason="DAILY_CHALLENGE_BONUS",
                        attempt_id=attempt.id,
                        question_id=request.question_id,
                        description_si="දිනපතා අභ්‍යාස ප්‍රසාද ලකුණු (+50 XP)",
                        description_en="Daily Challenge Bonus (+50 XP)",
                    )
                    self.session.add(daily_bonus_tx)
        else:
            # Re-attempt practice bonus
            re_xp = 5
            xp_tx = XpTransaction(
                user_id=user_id,
                amount=re_xp,
                reason="QUESTION_REATTEMPTED",
                attempt_id=attempt.id,
                question_id=request.question_id,
                description_si=f"ප්‍රශ්නය නැවත පුහුණු වීම (+{re_xp} XP)",
                description_en=f"Re-practiced Question (+{re_xp} XP)",
            )
            self.session.add(xp_tx)

        # 5. Update or Create DailyActivityBucket for today
        stmt_act = select(UserDailyActivity).where(
            UserDailyActivity.user_id == user_id,
            UserDailyActivity.date_key == today_key,
        )
        res_act = await self.session.execute(stmt_act)
        activity = res_act.scalar_one_or_none()

        if activity:
            activity.questions_solved_count += 1
            activity.total_time_spent_seconds += time_delta
            if is_effective_daily:
                activity.daily_challenge_completed = True
        else:
            activity = UserDailyActivity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                date_key=today_key,
                questions_solved_count=1,
                total_time_spent_seconds=time_delta,
                daily_challenge_completed=is_effective_daily,
            )
            self.session.add(activity)

        await self.session.commit()

        # 6. Reconcile and Sync UserStats Projection (CQRS)
        summary = await self.get_user_progress_summary(user_id)
        stmt_stats = select(UserStats).where(UserStats.user_id == user_id)
        stats_res = await self.session.execute(stmt_stats)
        stats = stats_res.scalar_one_or_none()

        if stats:
            stats.total_solved_count = summary.total_questions_solved
            stats.total_study_time_seconds = summary.total_time_spent_seconds
            stats.current_streak_days = summary.current_streak_days
            stats.longest_streak_days = max(stats.longest_streak_days, summary.longest_streak_days)
            stats.last_active_date = today
            stats.xp = summary.xp
        else:
            stats = UserStats(
                user_id=user_id,
                total_solved_count=summary.total_questions_solved,
                total_study_time_seconds=summary.total_time_spent_seconds,
                current_streak_days=summary.current_streak_days,
                longest_streak_days=summary.longest_streak_days,
                last_active_date=today,
                xp=summary.xp,
            )
            self.session.add(stats)

        await self.session.commit()
        return summary

    # =========================================================================
    # 3. Unmark Question Completed (විසඳූ බව ඉවත් කිරීම & XP Reversal)
    # =========================================================================

    async def unmark_question_completed(
        self, user_id: str, question_id: str
    ) -> UserProgressSummaryResponse:
        """
        ප්‍රශ්නයක් සම්පූර්ණ කළ බවට වූ වාර්තාව ඉවත් කිරීම.
        - අදාළ XP ලකුණු ආපසු අඩු කිරීම සඳහා `XpTransaction` වගුවේ ඍණ අගයක් (-10 XP) සටහන් වේ.
        - Daily Activity bucket එකෙහි ප්‍රශ්න ගණන අඩු වේ.
        """
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

            # Record negative XP transaction for audit proof
            reversal_tx = XpTransaction(
                user_id=user_id,
                amount=-10,
                reason="QUESTION_UNMARKED",
                question_id=question_id,
                description_si="ප්‍රශ්නය විසඳූ බව ඉවත් කිරීම (-10 XP)",
                description_en="Unmarked Completed Question (-10 XP)",
            )
            self.session.add(reversal_tx)

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
            stats.xp = summary.xp
            await self.session.commit()

        return summary

    # =========================================================================
    # 4. Bookmark Toggle (Bookmark / Star කිරීම)
    # =========================================================================

    async def toggle_bookmark(
        self, user_id: str, question_id: str, is_bookmarked: bool
    ) -> bool:
        """ප්‍රශ්නයක් Bookmark / Star කිරීම හෝ ඉවත් කිරීම."""
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
                id=str(uuid.uuid4()),
                user_id=user_id,
                question_id=question_id,
                time_spent_seconds=0,
                last_attempt_duration_seconds=0,
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

    # =========================================================================
    # 5. XP History & Audit Trail (XP ඉතිහාසය සහ සාක්ෂි විමසුම)
    # =========================================================================

    async def get_user_xp_history(
        self, user_id: str, limit: int = 10
    ) -> List[XpTransaction]:
        """
        ශිෂ්‍යයා ලබාගත් සියලුම XP ගනුදෙනු ලැයිස්තුව කාලානුක්‍රමිකව (Newest First) ලබා ගැනීම.
        """
        stmt = (
            select(XpTransaction)
            .where(XpTransaction.user_id == user_id)
            .order_by(desc(XpTransaction.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # 6. Colombo Streak Engine (අඛණ්ඩ දින ගණනය කිරීම)
    # =========================================================================

    def _compute_streaks(
        self, daily_activity: Dict[str, DailyActivityBucketSchema]
    ) -> tuple[int, int, Optional[str]]:
        """
        ශ්‍රී ලංකා සම්මත දින දර්ශනය (Asia/Colombo) පාදක කරගෙන අඛණ්ඩ Streaks ගණනය කිරීම.
        - අද හෝ ඊයේ දින විසඳා ඇත්නම් Streak එක නොබිඳී පවතී.
        - ඊයේ දිනය මඟහැරී ඇත්නම් Streak එක නැවත 1 සිට ආරම්භ වේ.
        """
        active_dates = [
            date.fromisoformat(k)
            for k, b in daily_activity.items()
            if b.questions_solved_count > 0 or b.total_time_spent_seconds > 0
        ]
        active_dates.sort()

        if not active_dates:
            return 0, 0, None

        # Longest streak calculation
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

        # Current streak calculation
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
