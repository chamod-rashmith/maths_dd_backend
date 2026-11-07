"""
SQLAlchemy 2.0 ORM models for Student Progress, Question Attempts, Daily Activity, and XP Ledger.
මෙම මොඩියුලය මඟින් ශිෂ්‍යයාගේ ගැටළු විසඳීමේ ප්‍රගතිය (Question Attempts), දිනපතා අධ්‍යයන කාලය (Daily Activity),
සහ Gamification ලකුණු පිළිබඳ විගණන ලේඛනය (XP Transaction Ledger with Proof) පූර්ණ සාමාන්‍යකරණයෙන් කළමනාකරණය කරයි.

Key Architectural Improvements (Domain 5):
1. Cumulative Study Time:
   - `time_spent_seconds` in `UserQuestionAttempt` accumulates across multiple practice sessions,
     ensuring total study time never decreases or gets overwritten on re-attempts.
   - `last_attempt_duration_seconds` tracks the specific elapsed time of the most recent session.
2. Immutable XP Audit Ledger (`XpTransaction`):
   - Every single XP award or deduction creates an immutable transaction entry with proof (`reason`, `amount`, `question_id`).
   - Eliminates untracked XP inflation or arbitrary score tampering.
3. Streak Calculation & Colombo Timezone:
   - Evaluates continuous daily engagement based on `Asia/Colombo` standard calendar days.
"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.question import Question


class UserQuestionAttempt(Base):
    """
    ශිෂ්‍යයෙකු විසින් ප්‍රශ්නයක් විසඳීමේ වාර්තාව (Student Question Completion Attempt).
    මෙහි `time_spent_seconds` යනු ශිෂ්‍යයා එම ප්‍රශ්නය සඳහා මේ දක්වා වැය කළ සමස්ත අධ්‍යයන කාලයයි (Cumulative Study Time).
    නැවත නැවත විසඳීමේදී පෙර කාලය මැකී නොගොස් එකතු වේ.
    """

    __tablename__ = "user_question_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_attempt"),
        Index("idx_attempt_user_question", "user_id", "question_id"),
        Index("idx_attempt_user_date", "user_id", "completed_date"),
    )

    # UUID identifier
    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="වාර්තාවේ අනන්‍ය හැඳුනුම් අංකය (UUID)",
    )

    # Student Firebase UID
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ශිෂ්‍යයාගේ Firebase UID",
    )

    # Question Identifier
    question_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ප්‍රශ්නයේ හැඳුනුම් අංකය",
    )

    # Cumulative total study time spent on this question across all attempts (in seconds)
    time_spent_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="මෙම ප්‍රශ්නය සඳහා වැය කළ සමස්ත කාලය (තත්පර වලින් - Cumulative Seconds across all attempts)",
    )

    # Duration of the most recent attempt session (in seconds)
    last_attempt_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="අවසන් වරට විසඳීමට වැය වූ කාලය (තත්පර වලින් - Most recent session duration)",
    )

    # Recommended target duration
    target_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="ප්‍රශ්නය සඳහා නිර්දේශිත කාලය (තත්පර වලින්)",
    )

    # Whether the latest attempt exceeded the target duration
    was_overtime: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="නියමිත කාල සීමාව ඉක්මවා ගියේද යන්න",
    )

    # Number of times the student has attempted/practiced this problem
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
        comment="ප්‍රශ්නය විසඳූ වාර ගණන (Attempt Count)",
    )

    # Flag indicating if this attempt solved a Daily Challenge question
    is_daily_question: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="දිනපතා අභ්‍යාස ප්‍රශ්නයක් ලෙස විසඳුවේද යන්න",
    )

    # Calendar date of completion (Sri Lanka Colombo date)
    completed_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="විසඳූ දිනය (Asia/Colombo Calendar Date)",
    )

    # Exact UTC timestamp of completion
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
        comment="විසඳූ නිශ්චිත දිනය සහ වේලාව (UTC)",
    )

    # Quick bookmark / star flag for revision
    is_bookmarked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="නැවත බැලීම සඳහා Bookmark කර ඇත්ද යන්න",
    )

    # Student self-assessed confidence level: LOW, MEDIUM, HIGH
    confidence: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="ශිෂ්‍යයාගේ විශ්වාසය (LOW, MEDIUM, HIGH)",
    )

    # Optional personal notes written by the student
    student_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="ශිෂ්‍යයාගේ පෞද්ගලික කෙටි සටහන්",
    )

    # Audit Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", lazy="joined")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<UserQuestionAttempt(user='{self.user_id}', question='{self.question_id}', "
            f"time_spent={self.time_spent_seconds}s, attempts={self.attempt_count})>"
        )


class UserDailyActivity(Base):
    """
    ශිෂ්‍යයෙකුගේ දිනපතා ක්‍රියාකාරකම් සාරාංශය (Daily Activity Heatmap Bucket).
    දිනපතා විසඳූ ප්‍රශ්න ගණන සහ සමස්ත අධ්‍යයන කාලය මෙහි ගබඩා කර GitHub-style Heatmap පෙන්වයි.
    """

    __tablename__ = "user_daily_activities"
    __table_args__ = (
        UniqueConstraint("user_id", "date_key", name="uq_user_daily_activity"),
        Index("idx_daily_activity_user_date", "user_id", "date_key"),
    )

    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="වාර්තාවේ හැඳුනුම් අංකය (UUID)",
    )

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ශිෂ්‍යයාගේ Firebase UID",
    )

    # YYYY-MM-DD date key in Asia/Colombo timezone
    date_key: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="දිනය (YYYY-MM-DD)",
    )

    # Total questions solved on this date
    questions_solved_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="අදාළ දිනයේදී විසඳූ ප්‍රශ්න ගණන",
    )

    # Total time spent studying on this date (in seconds)
    total_time_spent_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="අදාළ දිනයේදී අධ්‍යයනය සඳහා වැය කළ මුළු කාලය (තත්පර වලින්)",
    )

    # Whether the student finished the full daily challenge on this date
    daily_challenge_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="දිනපතා අභ්‍යාසය සම්පූර්ණ කළේද යන්න",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<UserDailyActivity(user='{self.user_id}', date='{self.date_key}', "
            f"solved={self.questions_solved_count}, time={self.total_time_spent_seconds}s)>"
        )


class XpTransaction(Base):
    """
    ශිෂ්‍යයාගේ අත්දැකීම් ලකුණු (XP) විගණන ලේඛනය (Immutable XP Audit Ledger with Proof).
    ශිෂ්‍යයා ලබාගත් හෝ අඩු වූ සෑම XP අගයක්ම හේතුව සහ සාක්ෂිය (Proof) සහිතව මෙහි ස්ථිරව සටහන් වේ.
    කිසිදු XP අගයක් අත්තනෝමතිකව වෙනස් කළ නොහැකි අතර, සත්‍ය සමස්ත XP අගය යනු මෙහි එකතුවයි (Sum of XP Transactions).
    """

    __tablename__ = "xp_transactions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="XP ගනුදෙනුවේ අනන්‍ය හැඳුනුම් අංකය (UUID)",
    )

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ශිෂ්‍යයාගේ Firebase UID",
    )

    # Signed integer delta (+10, +25, +50, -10)
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="ලබාගත් හෝ අඩු වූ XP අගය (Signed delta e.g. +10, +25, +50, -10)",
    )

    # Standardized reason code
    reason: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="හේතු කේතය (QUESTION_SOLVED, QUESTION_REATTEMPTED, DAILY_CHALLENGE_BONUS, STREAK_BONUS, QUESTION_UNMARKED)",
    )

    # Optional reference to the specific attempt record
    attempt_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="අදාළ විසඳීමේ වාර්තාව (attempt_id proof)",
    )

    # Optional reference to the question
    question_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="අදාළ ප්‍රශ්නයේ හැඳුනුම් අංකය",
    )

    # Student-friendly explanation in Sinhala
    description_si: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ශිෂ්‍යයාට පෙන්වන විස්තරය (Sinhala Description e.g. 'කෙටි ප්‍රශ්නයක් විසඳීම (+10 XP)')",
    )

    # Optional English explanation
    description_en: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ඉංග්‍රීසි විස්තරය (Optional English Description)",
    )

    # Exact timestamp when the XP was awarded
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
        index=True,
        comment="XP හිමි වූ දිනය සහ වේලාව (Audit Timestamp)",
    )

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<XpTransaction(id='{self.id}', user='{self.user_id}', "
            f"amount={self.amount}, reason='{self.reason}')>"
        )
